"""The agent loop and the HTTP API, driven by a scripted model (no network)."""

import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from google.genai import types

from ahc import tools, visuals
from ahc.agent import Agent, deterministic_answer, ground_check, to_llm
from ahc.analyst import Analyst
from ahc.server import create_app
from ahc.store import Store
from tests import ahc_fixture
from tests.test_ahc_core import FixtureCase

ALICE, BOB, CARA = "U-1", "U-2", "U-3"
RANK = {"scope": "Gamma Block 9", "start": "2026-01-01", "end": "2026-03-15", "top_n": 3}


class ScriptedLLM:
    """Plays a script of steps: ("call", name, args) or ("text", text). Records what it was sent."""

    def __init__(self, *steps, wait=0.0):
        self.steps, self.sent, self.wait = list(steps), [], wait

    def estimate(self, contents, tool_list, system):
        return 100

    def wait_needed(self, need):
        return self.wait

    def generate(self, contents, tool_list, system, force_call=False):
        self.sent.append(SimpleNamespace(contents=list(contents), tools=[d.name for t in tool_list for d in t.function_declarations], system=system, forced=force_call))
        kind, *rest = self.steps.pop(0)
        if kind == "call":
            part = types.Part(function_call=types.FunctionCall(name=rest[0], args=rest[1]))
        else:
            part = types.Part(text=rest[0])
        return SimpleNamespace(candidates=[SimpleNamespace(content=types.Content(role="model", parts=[part]))])


class AgentCase(FixtureCase):
    def agent(self, *steps, **kw):
        self.llm = ScriptedLLM(*steps, **kw)
        return Agent(self.A, self.store, self.llm)


class LoopTests(AgentCase):
    def test_tool_call_then_grounded_wording(self):
        out = self.agent(("call", "downtime_ranking", RANK), ("text", "WELL-9002 had the most downtime: 63 days [WELL-9002].")).respond(ALICE, None, "Which wells in Gamma Block 9 were down the longest in 2026?")
        self.assertEqual((out["answer_source"], out["warnings"]), ("model", []))
        self.assertEqual([(c["name"], c["ok"]) for c in out["tool_calls"]], [("downtime_ranking", True)])
        self.assertEqual(out["blocks"][0]["visual"]["kind"], "bar")
        self.assertIn("WELL-9002", {c["id"] for c in out["citations"]})
        self.assertEqual(len(self.llm.sent), 2)  # one to choose the tool, one to word the answer

    def test_a_number_the_tools_did_not_return_is_rejected(self):
        out = self.agent(("call", "downtime_ranking", RANK), ("text", "WELL-9002 had 70 days of downtime.")).respond(ALICE, None, "Which wells were down the longest?")
        self.assertEqual(out["answer_source"], "verified facts")
        self.assertIn("70", out["warnings"][0])
        self.assertIn("63 days", out["answer"])           # the deterministic facts replace it

    def test_an_invented_record_id_is_rejected(self):
        out = self.agent(("call", "downtime_ranking", RANK), ("text", "WELL-9002 had 63 days [INS-9999-0001].")).respond(ALICE, None, "Which wells were down the longest?")
        self.assertEqual(out["answer_source"], "verified facts")
        self.assertIn("INS-9999-0001", out["warnings"][0])

    def test_numbers_from_the_question_are_allowed(self):
        out = self.agent(("call", "spills", {"scope": "Gamma Block 9", "start": "2026-01-01", "end": "2026-03-15"}), ("text", "In the last 90 days there were 2 spills totalling 3.5 bbl.")).respond(ALICE, None, "How many spills in the last 90 days?")
        self.assertEqual((out["answer_source"], out["warnings"]), ("model", []))

    def test_a_tool_error_is_reported_not_raised(self):
        out = self.agent(("call", "well_status", {"asset_id": "WELL-0000"}), ("text", "That well does not exist.")).respond(ALICE, None, "Is WELL-0000 producing?")
        self.assertEqual(out["tool_calls"][0]["ok"], False)
        self.assertIn("Unknown well", out["errors"][0])

    def test_an_unknown_tool_is_reported(self):
        out = self.agent(("call", "launch_rockets", {}), ("text", "Sorry.")).respond(ALICE, None, "Do something odd")
        self.assertIn("Unknown tool", out["errors"][0])

    def test_wording_step_is_skipped_when_the_rate_limit_budget_is_nearly_used(self):
        out = self.agent(("call", "downtime_ranking", RANK), ("text", "never asked"), wait=30.0).respond(ALICE, None, "Which wells were down the longest?")
        self.assertEqual(len(self.llm.sent), 1)
        self.assertEqual(out["answer_source"], "verified facts")
        self.assertIn("rate limit", " ".join(out["warnings"]))
        self.assertIn("63 days", out["answer"])

    def test_the_answer_cites_without_repeating_ids_already_in_the_sentence(self):
        res = self.A.well_status("WELL-9001")
        text = deterministic_answer([res])
        self.assertNotIn("[INS-9001-0009]", text.split("\n")[0])  # the first sentence already names it

    def test_conversation_history_is_sent_for_follow_ups(self):
        a = self.agent(("text", "First answer."), ("text", "Second answer."))
        first = a.respond(ALICE, None, "Hello there")
        a.respond(ALICE, first["conv_id"], "And now?")
        texts = [p.text for c in self.llm.sent[1].contents for p in c.parts if p.text]
        self.assertEqual(texts, ["Hello there", "First answer.", "And now?"])

    def test_discussed_wells_are_remembered_privately_for_recall(self):
        out = self.agent(("call", "downtime_ranking", RANK), ("text", "ok")).respond(ALICE, None, "Which wells were down the longest?")
        self.assertEqual([r["entities"] for r in self.store.recall(ALICE, entity_type="well")], [["WELL-9002", "WELL-9001"]])
        self.assertEqual(self.store.recall(BOB, entity_type="well"), [])
        self.assertTrue(out["conv_id"].startswith("CV-"))

    def test_another_users_conversation_is_refused(self):
        a = self.agent(("text", "hi"))
        first = a.respond(ALICE, None, "Hello")
        with self.assertRaises(PermissionError):
            a.respond(BOB, first["conv_id"], "let me read that")
        with self.assertRaises(ValueError):
            a.respond("U-404", None, "who am I")


class SkippedToolTests(AgentCase):
    def test_a_data_question_answered_without_tools_is_not_accepted_the_patterns_are_used(self):
        out = self.agent(("text", "WELL-9001 had 0 spills and 42 days of downtime.")).respond(ALICE, None, "How many days was WELL-9001 down in 2026?")
        self.assertEqual(out["answer_source"], "verified facts")
        self.assertIn("without consulting the records", out["warnings"][0])
        self.assertEqual([c["name"] for c in out["tool_calls"]], ["downtime"])
        self.assertIn("35 days", out["answer"])
        self.assertNotIn("42", out["answer"])

    def test_a_statement_answered_without_tools_triggers_one_forced_retry(self):
        args = {"asset_id": "WELL-9003", "text": "WELL-9003 will be shut in", "kind": "planned_downtime", "valid_from": "2026-03-20"}
        out = self.agent(("text", "Noted, thanks!"), ("call", "add_shared_note", args), ("text", "Saved for everyone.")).respond(ALICE, None, "FYI for everyone: WELL-9003 will be shut in from 20 Mar.")
        self.assertEqual([s.forced for s in self.llm.sent], [False, True, False])
        self.assertEqual([c["name"] for c in out["tool_calls"]], ["add_shared_note"])
        self.assertEqual(len(self.store.shared_notes_for("WELL-9003")), 1)

    def test_small_talk_is_answered_normally(self):
        out = self.agent(("text", "Hello! How can I help with your wells?")).respond(ALICE, None, "Hello there")
        self.assertEqual(out["answer_source"], "model")
        self.assertEqual(out["tool_calls"], [])

    def test_numbers_inside_record_ids_do_not_make_an_invented_number_look_grounded(self):
        res = [{"facts": [{"text": "WELL-0001 is not producing", "cites": []}], "data": {}, "flags": [], "visuals": {}, "citations": []}]
        self.assertEqual(ground_check("WELL-0001 has had 0 spills.", res, "How many spills has WELL-0001 had?"), ["0"])

    def test_a_repeated_tool_call_runs_once(self):
        out = self.agent(("call", "downtime_ranking", RANK), ("call", "downtime_ranking", RANK), ("text", "WELL-9002 had 63 days.")).respond(ALICE, None, "Which wells were down the longest?")
        self.assertEqual(len(out["tool_calls"]), 1)
        self.assertEqual(len(out["blocks"]), 1)


class ReplayLessonsTests(AgentCase):
    def test_a_date_with_the_wrong_year_is_matched_to_the_nearest_real_inspection_day(self):
        self.assertEqual(self.A.match_date("WELL-9001", "2024-03-09"), "2026-03-09")
        self.assertEqual(self.A.match_date("WELL-9001", "2026-03-09"), "2026-03-09")
        self.assertEqual(self.A.match_date("WELL-9001", "2024-03-10"), "2024-03-10")   # no such inspection in any year: unchanged

    def test_a_correction_with_the_wrong_year_still_finds_the_inspection(self):
        from ahc import tools
        from ahc.tools import Ctx
        ctx = Ctx(self.A, self.store, ALICE, "CV-x")
        res = tools.run_tool(ctx, "propose_correction", {"asset_id": "WELL-9001", "date": "2024-01-19", "field": "wellhead_temp_c", "new_value": 40, "reason": "re-measured"})
        self.assertNotIn("error", res)
        self.assertIn("INS-9001-0003", res["pending"]["preview"]["rows"][0][1])

    def test_a_lookup_step_is_not_treated_as_the_final_answer_even_when_the_budget_is_tight(self):
        conv = self.store.new_conversation(ALICE, "earlier")
        mid = self.store.add_message(conv, ALICE, "assistant", "x")
        self.store.record_entities(ALICE, conv, mid, [("well", "WELL-9001"), ("well", "WELL-9002")], "Which two wells?")
        out = self.agent(("call", "recall_discussed", {"count": 2}), ("call", "repair_costs", {"wells": ["WELL-9001", "WELL-9002"], "period": "2026"}), ("text", "Done."), wait=60.0).respond(
            ALICE, None, "For the two wells we discussed, what have repairs cost this year?")
        self.assertEqual([c["name"] for c in out["tool_calls"]], ["recall_discussed", "repair_costs"])   # the second step still ran
        self.assertEqual(len(self.llm.sent), 2)   # the lookup did not end the question; the final wording step was then skipped

    def test_runaway_tool_loops_are_stopped(self):
        steps = [("call", "well_status", {"asset_id": f"WELL-900{i % 3 + 1}", "x": i}) for i in range(8)] + [("text", "ok")]
        out = self.agent(*steps).respond(ALICE, None, "Check every well")
        self.assertLessEqual(len(out["tool_calls"]), 6)
        self.assertTrue(out["answer"])

    def test_a_pattern_hint_is_sent_with_questions_but_never_with_statements(self):
        self.agent(("text", "ok")).respond(ALICE, None, "Is WELL-9001 producing oil right now?")
        parts = [p.text for p in self.llm.sent[0].contents[-1].parts]
        self.assertTrue(any("Pattern hint" in x and "well_status" in x for x in parts))
        self.agent(("text", "ok"), ("text", "ok")).respond(ALICE, None, "WELL-9002 is running fine.")
        self.assertFalse(any("Pattern hint" in (p.text or "") for p in self.llm.sent[0].contents[-1].parts))

    def test_the_data_question_pattern_matches_real_questions_and_not_small_talk(self):
        from ahc.agent import _DATA_HINT
        for m in ("How many days was WELL-9001 down in 2026?", "Which wells are down?", "show a table"):
            self.assertTrue(_DATA_HINT.search(m), m)
        for m in ("Hello there", "And now?", "thanks a lot"):
            self.assertFalse(_DATA_HINT.search(m), m)


class ToolRoutingTests(AgentCase):
    def test_write_tools_are_only_offered_for_statements_and_corrections(self):
        for msg, writes in (("Is WELL-9001 producing oil right now?", False), ("Which wells are down?", False), ("The 9 Mar reading is wrong, it was re-measured at 40", True),
                            ("WELL-9002 is running fine.", True), ("FYI for everyone: WELL-9003 will be shut in", True)):
            a = self.agent(("text", "ok"), ("text", "ok"))   # statements get one forced retry
            a.respond(ALICE, None, msg)
            offered = set(self.llm.sent[0].tools)
            self.assertEqual("propose_correction" in offered, writes, msg)
            self.assertIn("well_status", offered)

    def test_system_prompt_carries_the_as_of_date_and_the_user(self):
        self.agent(("text", "ok")).respond(ALICE, None, "Hello")
        system = self.llm.sent[0].system
        self.assertIn("2026-03-15", system)
        self.assertIn("Alice Test", system)


class VisualChoiceTests(AgentCase):
    def result(self):
        return self.A.downtime_ranking("Gamma Block 9", start="2026-01-01", end="2026-03-15")

    def test_the_natural_visual_fits_the_answer(self):
        self.assertEqual(visuals.choose("Which wells were down the longest?", self.result())["kind"], "bar")
        self.assertEqual(visuals.choose("anything", self.A.well_status("WELL-9001"))["kind"], "status_card")
        self.assertEqual(visuals.choose("anything", self.A.spills("Gamma Block 9", start="2026-01-01", end="2026-03-15"))["kind"], "table")
        self.assertEqual(visuals.choose("anything", self.A.spill_heatmap(start="2026-01-01", end="2026-03-15"))["kind"], "heatmap")
        self.assertEqual(visuals.choose("anything", self.A.inspection_series("WELL-9001", 5))["kind"], "line")

    def test_an_explicit_request_is_respected(self):
        r = self.result()
        for text, kind in (("show it as a table", "table"), ("give me a bar chart", "bar"), ("as a chart please", "bar")):
            self.assertEqual(visuals.choose(text, r)["kind"], kind, text)
        spills = self.A.spills("Gamma Block 9", start="2026-01-01", end="2026-03-15")
        self.assertEqual(visuals.choose("show them on a map", spills)["kind"], "map")
        self.assertIn("map", visuals.choose("x", spills)["available"])

    def test_an_impossible_request_falls_back_and_says_so(self):
        c = visuals.choose("show a heatmap", self.result())
        self.assertNotEqual(c["kind"], "heatmap")
        self.assertIn("cannot be shown as a heatmap", c["note"])

    def test_requested_visual_detection(self):
        self.assertEqual([visuals.requested_visual(t) for t in ("a line chart of it", "heat map", "on a map", "bar graph", "status card", "as a table", "what happened")],
                         ["line", "heatmap", "map", "bar", "status_card", "table", None])


class GroundingTests(unittest.TestCase):
    def res(self):
        return [{"facts": [{"text": "15 Oct 2026, 3.2 °C, USD 25,794 for WELL-0001", "cites": []}], "data": {}, "flags": [], "visuals": {}, "citations": [{"id": "INS-0001-0203", "kind": "inspection", "label": "x"}]}]

    def test_accepts_values_present_in_the_results(self):
        self.assertEqual(ground_check("On 15 Oct 2026 it was 3.2 °C: USD 25,794 [INS-0001-0203] for WELL-0001.", self.res()), [])

    def test_flags_unknown_numbers_and_ids(self):
        self.assertEqual(ground_check("It was 4.7 °C [INS-0001-9999].", self.res()), ["4.7", "INS-0001-9999"])

    def test_list_markers_are_not_numbers(self):
        self.assertEqual(ground_check("1. WELL-0001\n2. 3.2 °C", self.res()), [])

    def test_to_llm_is_compact_and_has_no_drawing_specs(self):
        big = {"tool": "t", "title": "x", "facts": [{"text": f"f{i}", "cites": list("abcdef")} for i in range(30)], "flags": [], "citations": [], "visuals": {"table": {"columns": ["a"], "rows": [[i] for i in range(50)]}, "map": {"points": [1] * 99}}, "data": {}}
        out = to_llm(big)
        self.assertEqual((len(out["facts"]), len(out["table"]["rows"]), out["table"]["row_count"]), (10, 8, 50))
        self.assertNotIn("map", out)


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        cls.root = ahc_fixture.build(base)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def client(self, llm):
        app = create_app([self.root], Path(self._tmp.name) / "api.sqlite3", Path(self._tmp.name) / f"mem-{id(llm)}.sqlite3", ahc_fixture.AS_OF, llm)
        self.addCleanup(app.state.rt.store.close)
        return TestClient(app), app

    def test_bootstrap_lists_users_rules_and_dataset_generated_suggestions(self):
        c, _ = self.client(ScriptedLLM())
        b = c.get("/api/bootstrap").json()
        self.assertEqual((b["as_of"], b["well_count"], len(b["users"])), ("2026-03-15", 3, 3))
        self.assertTrue(any(r["key"] == "production_delta_c" for r in b["rules"]))
        self.assertTrue(all("WELL-0001" not in s and "Northeast" not in s for s in b["suggestions"]))
        self.assertTrue(any("WELL-90" in s for s in b["suggestions"]))
        self.assertEqual(c.get("/").status_code, 200)

    def test_chat_returns_answer_visuals_and_citations(self):
        c, _ = self.client(ScriptedLLM(("call", "downtime_ranking", RANK), ("text", "WELL-9002 is first with 63 days [WELL-9002].")))
        out = c.post("/api/chat", json={"user_id": ALICE, "message": "Which wells were down the longest? Show a bar chart."}).json()
        self.assertEqual(out["blocks"][0]["visual"]["kind"], "bar")
        self.assertIn("63 days", out["answer"])
        self.assertTrue(out["conv_id"])

    def test_private_conversations_over_http(self):
        c, _ = self.client(ScriptedLLM(("text", "hi"), ("text", "hi again")))
        conv = c.post("/api/chat", json={"user_id": ALICE, "message": "private hello"}).json()["conv_id"]
        self.assertEqual(c.get(f"/api/conversations/{conv}", params={"user_id": ALICE}).status_code, 200)
        self.assertEqual(c.get(f"/api/conversations/{conv}", params={"user_id": BOB}).status_code, 403)
        self.assertEqual(c.get("/api/conversations", params={"user_id": BOB}).json(), [])
        self.assertEqual(c.post("/api/chat", json={"user_id": BOB, "message": "x", "conv_id": conv}).status_code, 403)
        self.assertEqual(c.post("/api/chat", json={"user_id": "U-404", "message": "x"}).status_code, 400)
        self.assertEqual(c.post("/api/chat", json={"user_id": ALICE, "message": "   "}).status_code, 400)

    def test_evidence_endpoint(self):
        c, _ = self.client(ScriptedLLM())
        self.assertEqual(c.get("/api/evidence", params={"ref": "INS-9001-0003"}).json()["kind"], "inspection")
        doc = c.get("/api/evidence", params={"ref": "T200#9.3"}).json()
        self.assertTrue(any(s["highlight"] and "15 °C above" in s["text"] for s in doc["sections"]))
        self.assertEqual(c.get("/api/evidence", params={"ref": "SR-02"}).status_code, 200)
        self.assertEqual(c.get("/api/evidence", params={"ref": "INS-0000-0000"}).status_code, 404)

    def test_correction_flow_over_http_preview_confirm_and_audit(self):
        args = {"asset_id": "WELL-9001", "date": "2026-01-19", "field": "wellhead_temp_c", "new_value": 40.0, "reason": "Faulty thermal gun, re-measured"}
        c, app = self.client(ScriptedLLM(("call", "propose_correction", args), ("text", "I prepared the correction; please confirm it.")))
        out = c.post("/api/chat", json={"user_id": ALICE, "message": "The 19 Jan reading for WELL-9001 is wrong; the crew re-measured 40.0 C."}).json()
        (pending,) = out["pending"]
        self.assertEqual(c.get("/api/audit").json()["corrections"], [])                               # nothing saved yet
        self.assertEqual(c.post(f"/api/actions/{pending['action_id']}/confirm", json={"user_id": BOB}).status_code, 403)
        done = c.post(f"/api/actions/{pending['action_id']}/confirm", json={"user_id": ALICE}).json()
        self.assertIn("Saved correction", done["answer"])
        (cor,) = c.get("/api/audit").json()["corrections"]
        self.assertEqual((cor["original_value"], cor["new_value"], cor["author_user_id"]), (25.0, 40.0, ALICE))
        self.assertEqual(c.post(f"/api/actions/{pending['action_id']}/confirm", json={"user_id": ALICE}).status_code, 400)  # not twice
        self.assertEqual(c.get("/api/evidence", params={"ref": cor["correction_id"]}).json()["kind"], "correction")
        later = app.state.rt
        with later.session() as A:
            self.assertEqual(A.downtime("WELL-9001", start="2026-01-01", end="2026-03-15")["data"]["total_days"], 28)

    def test_changing_the_as_of_date(self):
        c, app = self.client(ScriptedLLM())
        self.assertEqual(c.post("/api/settings", json={"as_of": "2026-02-01"}).json()["as_of"], "2026-02-01")
        self.assertEqual(c.post("/api/settings", json={"as_of": "nonsense"}).status_code, 400)
        with app.state.rt.session() as A:
            self.assertEqual(A.as_of, date(2026, 2, 1))


if __name__ == "__main__":
    unittest.main()
