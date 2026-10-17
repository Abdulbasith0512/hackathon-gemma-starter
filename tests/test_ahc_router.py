"""The offline question patterns, the agent's behaviour when the model is down, and the quota-aware retry."""

import json
import unittest
from types import SimpleNamespace
from unittest import mock

import gemma
from ahc import router
from ahc.agent import Agent, GemmaLLM
from tests.test_ahc_agent import ALICE, ScriptedLLM
from tests.test_ahc_core import FixtureCase
from tests.test_ahc_golden import GoldenCase


class RouterFixtureTests(FixtureCase):
    def route(self, text):
        return router.route(self.A, text)

    def test_common_question_shapes_map_to_tools(self):
        self.assertEqual(self.route("Is WELL-9001 producing oil right now?"), [("well_status", {"asset_id": "WELL-9001"})])
        self.assertEqual(self.route("Which wells in Gamma Block 9 were down the longest in the last 4 months?"),
                         [("downtime_ranking", {"scope": "Gamma Block 9", "period": "last 4 months", "top_n": 3})])
        self.assertEqual(self.route("How many days was WELL-9001 down in 2026?"), [("downtime", {"scope": "WELL-9001", "period": "2026"})])
        self.assertEqual(self.route("Show a heatmap of 2026 spills by area and month."), [("spill_heatmap", {"period": "2026"})])
        self.assertEqual(self.route("Which wells in Delta Block 4 are not producing right now?"), [("wells_not_producing", {"scope": "Delta Block 4"})])
        self.assertEqual(self.route("What have repairs cost for WELL-9001 this year?"), [("repair_costs", {"wells": ["WELL-9001"], "period": "this year"})])

    def test_areas_are_found_by_name_and_by_id(self):
        self.assertEqual(router.find_scope(self.A, "wells in gamma block 9"), "Gamma Block 9")
        self.assertEqual(router.find_scope(self.A, "anything in G-09?"), "Gamma Block 9")
        self.assertEqual(router.find_scope(self.A, "well 9001 please"), "WELL-9001")
        self.assertIsNone(router.find_scope(self.A, "nothing relevant"))

    def test_statements_and_corrections_are_never_guessed(self):
        for text in ("The 9 Mar reading for WELL-9001 is wrong, re-measured at 40", "WELL-9002 is running fine.", "FYI for everyone: WELL-9003 will be shut in from 20 Mar",
                     "Note for all T350 wells: root-cause analysis after 2 repairs, not 3."):
            self.assertIsNone(self.route(text), text)

    def test_unsure_means_no_answer(self):
        self.assertIsNone(self.route("What is the meaning of life?"))

    def test_periods_and_counts(self):
        self.assertEqual([router.find_period(t) for t in ("last 90 days", "in 2025", "this year", "past three months", "nothing here")], ["last 90 days", "2025", "this year", "last 3 months", None])
        self.assertEqual([router.find_top_n(t) for t in ("which 3 wells", "the top five wells", "5 wells", "all wells")], [3, 5, 5, None])


class RouterSampleTests(GoldenCase):
    def test_every_question_shaped_scenario_routes_to_the_expected_tool(self):
        with open("questions/sample_scenarios.json", encoding="utf-8") as f:
            qs = {q["id"]: q["text"] for q in json.load(f)}
        want = {"Q1": "well_status", "Q2": "wells_not_producing", "Q3": "inspection_series", "Q4": "spills", "Q5": "downtime", "Q6": "downtime_ranking", "Q7": "spills", "Q8": "spill_heatmap",
                "Q9": "compliance_audit", "Q10": "compliance_audit", "Q12b": "wells_not_producing", "Q14a": "rca_candidates", "Q14c": "rca_candidates", "Q15a": "well_status",
                "Q15b": "compliance_audit", "Q16b": "well_context", "Q18": "spill_evidence"}
        for qid, tool in want.items():
            routed = router.route(self.A, qs[qid])
            self.assertEqual(routed[0][0], tool, qid)
        for qid in ("Q12a", "Q13", "Q14b", "Q16a", "Q17a", "Q17b", "Q17c"):   # statements: model only
            self.assertIsNone(router.route(self.A, qs[qid]), qid)
        self.assertEqual(router.route(self.A, qs["Q6"])[0][1], {"scope": "Northeast Block 7", "period": "last 4 months", "top_n": 3})
        self.assertEqual(router.route(self.A, qs["Q18"])[0][1], {"asset_id": "WELL-0101", "date": "2026-08-20"})
        self.assertEqual(router.route(self.A, qs["Q10"])[0][1]["protocol"], "SR-02")

    def test_the_routed_tools_give_the_official_answers(self):
        from ahc import tools
        from ahc.tools import Ctx
        ctx = Ctx(self.fresh(), self.store, "U-201", "CV-x")
        name, args = router.route(self.A, "Which 3 wells in Northeast Block 7 had the most downtime in the last 4 months? Show a bar chart.")[0]
        res = tools.run_tool(ctx, name, {k: v for k, v in args.items() if v is not None})
        self.assertEqual({x["asset_id"]: x["days"] for x in res["data"]["ranking"]}, {"WELL-0121": 49, "WELL-0138": 42, "WELL-0107": 42})


class DownModelTests(FixtureCase):
    class Down:
        """A model that cannot be reached."""

        def __init__(self, fail_after=0):
            self.calls, self.fail_after = 0, fail_after

        def estimate(self, *a):
            return 10

        def wait_needed(self, need):
            return 0.0

        def generate(self, contents, tool_list, system, force_call=False):
            self.calls += 1
            if self.calls > self.fail_after:
                raise gemma.GemmaError("Gemma API error (model 'x'): 500 Internal error encountered.")
            part = __import__("google.genai.types", fromlist=["types"]).Part(function_call=__import__("google.genai.types", fromlist=["types"]).FunctionCall(name="downtime_ranking", args={"scope": "Gamma Block 9", "start": "2026-01-01", "end": "2026-03-15"}))
            return SimpleNamespace(candidates=[SimpleNamespace(content=__import__("google.genai.types", fromlist=["types"]).Content(role="model", parts=[part]))])

    def test_a_question_is_still_answered_when_the_model_is_down(self):
        out = Agent(self.A, self.store, self.Down()).respond(ALICE, None, "Which wells in Gamma Block 9 were down the longest in the last 4 months?")
        self.assertEqual(out["answer_source"], "verified facts")
        self.assertIn("built-in question patterns", out["warnings"][0])
        self.assertIn("WELL-9002", out["answer"])
        self.assertEqual(out["blocks"][0]["visual"]["kind"], "bar")
        self.assertTrue(out["citations"])

    def test_a_statement_needs_the_model_and_reports_the_error(self):
        with self.assertRaises(gemma.GemmaError):
            Agent(self.A, self.store, self.Down()).respond(ALICE, None, "WELL-9002 is running fine.")

    def test_if_only_the_wording_step_fails_the_tool_answer_is_kept(self):
        out = Agent(self.A, self.store, self.Down(fail_after=1)).respond(ALICE, None, "Which wells were down the longest?")
        self.assertEqual(out["answer_source"], "verified facts")
        self.assertIn("wording step", out["warnings"][0])
        self.assertIn("63 days", out["answer"])


class PatientRetryTests(unittest.TestCase):
    def llm(self):
        return GemmaLLM(tpm=10**9)

    def call(self, *outcomes):
        ok = SimpleNamespace(candidates=[], usage_metadata=SimpleNamespace(prompt_token_count=5))
        seq = [o if isinstance(o, Exception) else ok for o in outcomes]
        with mock.patch("gemma.generate_with_tools", side_effect=seq) as gen, mock.patch("time.sleep") as sleep:
            try:
                self.llm().generate([], [], "")
                err = None
            except gemma.GemmaError as e:
                err = e
        return gen.call_count, [c.args[0] for c in sleep.call_args_list if c.args[0] >= 1], err

    def test_sustained_server_errors_are_retried_with_longer_waits(self):
        e500 = gemma.GemmaError("Gemma API error (model 'x'): 500 Internal error encountered.")
        calls, sleeps, err = self.call(e500, e500, "ok")
        self.assertEqual((calls, sleeps, err), (3, [6.0, 15.0], None))

    def test_gives_up_after_the_bounded_retries(self):
        e503 = gemma.GemmaError("Gemma API error (model 'x'): 503 unavailable")
        calls, _sleeps, err = self.call(e503, e503, e503)
        self.assertEqual(calls, 3)
        self.assertIsNotNone(err)

    def test_quota_errors_wait_as_long_as_the_api_asks_once(self):
        e429 = gemma.GemmaError("Gemma API error (model 'x'): 429 quota. Please retry in 12.5s.")
        calls, sleeps, err = self.call(e429, "ok")
        self.assertEqual((calls, sleeps, err), (2, [13.5], None))

    def test_permanent_errors_are_not_retried(self):
        e400 = gemma.GemmaError("Gemma API error (model 'x'): 400 API key not valid")
        calls, sleeps, err = self.call(e400)
        self.assertEqual((calls, sleeps), (1, []))
        self.assertIn("400", str(err))


if __name__ == "__main__":
    unittest.main()
