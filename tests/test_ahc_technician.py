"""Who carried out a maintenance job: a matched technician, a missing technician ID, and an ID with no matching user.

The expected names come from the fixture's users.json and from a join written independently in the test,
so the code under test is not checking itself.
"""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from ahc import db, ingest, rules
from ahc.agent import Agent, ground_check
from ahc.analyst import Analyst
from ahc.evidence import resolve
from ahc.router import route
from ahc.server import create_app
from ahc.store import Store
from tests import ahc_fixture
from tests.test_ahc_agent import ALICE, ScriptedLLM
from tests.test_ahc_golden import AS_OF as SAMPLE_AS_OF
from tests.test_ahc_golden import SAMPLE

MATCHED = "MNT-9001-001"       # technician U-2 (Bob Test)
MISSING = "MNT-9002-001"       # technician_user_id set to null in this test
UNMATCHED = "MNT-9002-002"     # technician_user_id "U-999": no such user
UNNAMED = "MNT-9001-004"       # technician U-3, whose user record has an empty name


def rewrite(root: Path, well: str, edits: dict) -> None:
    path = root / "assets" / well / "maintenance.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    for r in rows:
        if r["maintenance_id"] in edits:
            r["technician_user_id"] = edits[r["maintenance_id"]]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


class TechnicianCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        cls.root = ahc_fixture.build(base)
        rewrite(cls.root, "WELL-9002", {MISSING: None, UNMATCHED: "U-999"})
        rewrite(cls.root, "WELL-9001", {UNNAMED: "U-3"})
        users = cls.root / "fleet/users.json"
        data = json.loads(users.read_text(encoding="utf-8"))
        for u in data["users"]:
            if u["user_id"] == "U-3":
                u["name"] = ""
        users.write_text(json.dumps(data), encoding="utf-8")
        cls.db_path = base / "ahc.sqlite3"
        ingest.ingest([cls.root], cls.db_path)
        cls.conn = db.connect(cls.db_path)
        cls.rules = rules.load_rules(cls.conn)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls._tmp.cleanup()

    def setUp(self):
        self.store = Store(Path(self._tmp.name) / f"mem-{self.id().split('.')[-1]}.sqlite3")
        self.addCleanup(self.store.close)
        self.A = Analyst(self.conn, self.rules, self.store, ahc_fixture.AS_OF)

    def agent(self, *steps):
        self.llm = ScriptedLLM(*steps)
        return Agent(self.A, self.store, self.llm)

    def joined(self, mid):
        """The technician as an independent SQL join of the two tables."""
        return self.conn.execute("SELECT m.technician_user_id, u.name FROM maintenance m LEFT JOIN users u ON m.technician_user_id = u.user_id WHERE m.maintenance_id=?", (mid,)).fetchone()


class MatchedTechnicianTests(TechnicianCase):
    def test_the_join_returns_the_id_and_the_name(self):
        self.assertEqual(tuple(self.joined(MATCHED)), ("U-2", "Bob Test"))
        m = next(x for x in self.A.maintenance(["WELL-9001"]) if x["maintenance_id"] == MATCHED)
        self.assertEqual((m["technician_user_id"], m["technician_name"]), ("U-2", "Bob Test"))

    def test_the_answer_names_the_technician_and_cites_the_maintenance_record(self):
        r = self.A.maintenance_record(MATCHED)
        self.assertEqual(r["data"]["technician_status"], "recorded")
        self.assertIn("carried out by Bob Test (U-2)", r["facts"][0]["text"])
        self.assertEqual(r["facts"][0]["cites"], [MATCHED])
        self.assertIn(MATCHED, {c["id"] for c in r["citations"]})
        self.assertEqual(r["flags"], [])
        self.assertEqual(r["visuals"]["table"]["columns"][4:6], ["Technician ID", "Technician"])
        self.assertEqual(r["visuals"]["table"]["rows"][0][4:6], ["U-2", "Bob Test"])

    def test_the_report_file_citation_is_kept(self):
        r = self.A.maintenance_record("MNT-9003-001")
        self.assertIn("report:MNT-9003-001", {c["id"] for c in r["citations"]})

    def test_lookup_by_the_inspection_that_triggered_the_repair(self):
        r = self.A.maintenance_record(inspection_id="INS-9003-0008")
        self.assertEqual(r["data"]["maintenance_id"], "MNT-9003-001")

    def test_the_agent_answers_with_the_name_and_the_citation(self):
        out = self.agent(("call", "maintenance_record", {"maintenance_id": MATCHED}),
                         ("text", f"{MATCHED} was carried out by Bob Test (U-2) [{MATCHED}].")).respond(ALICE, None, f"Who carried out {MATCHED}?")
        self.assertEqual((out["answer_source"], out["warnings"]), ("model", []))
        self.assertIn(MATCHED, {c["id"] for c in out["citations"]})
        self.assertEqual(out["blocks"][0]["visual"]["spec"]["rows"][0][5], "Bob Test")

    def test_a_follow_up_without_an_id_is_never_answered_from_memory(self):
        """'Who carried out this maintenance task?' must trigger a lookup; the ID is only in the history."""
        agent = self.agent(("call", "maintenance_record", {"maintenance_id": MATCHED}), ("text", f"Bob Test (U-2) did {MATCHED} [{MATCHED}]."),
                           ("text", f"Bob Test did it [{MATCHED}]."),                                           # tool-less: must be discarded
                           ("call", "maintenance_record", {"maintenance_id": MATCHED}), ("text", f"{MATCHED} was carried out by Bob Test (U-2) [{MATCHED}]."))
        first = agent.respond(ALICE, None, f"Show maintenance record {MATCHED}")
        out = agent.respond(ALICE, first["conv_id"], "Who carried out this maintenance task?")
        self.assertTrue(self.llm.sent[2].forced is False and self.llm.sent[3].forced is True, "the tool-less answer triggers one forced retry")
        self.assertEqual([(c["name"], c["args"]["maintenance_id"], c["ok"]) for c in out["tool_calls"]], [("maintenance_record", MATCHED, True)])
        self.assertEqual((out["answer_source"], out["warnings"]), ("model", []))
        self.assertIn("Bob Test (U-2)", out["answer"])
        self.assertIn(MATCHED, {c["id"] for c in out["citations"]})

    def test_a_tool_less_follow_up_that_never_calls_a_tool_is_not_shown(self):
        agent = self.agent(("call", "maintenance_record", {"maintenance_id": MATCHED}), ("text", f"Bob Test (U-2) did {MATCHED} [{MATCHED}]."),
                           ("text", f"Bob Test did it [{MATCHED}]."), ("text", f"Bob Test did it [{MATCHED}]."))
        first = agent.respond(ALICE, None, f"Show maintenance record {MATCHED}")
        out = agent.respond(ALICE, first["conv_id"], "Who carried out this maintenance task?")
        self.assertEqual(out["tool_calls"], [])
        self.assertNotIn("Bob Test", out["answer"])

    def test_the_offline_router_sends_a_who_question_to_the_tool(self):
        self.assertEqual(route(self.A, f"Who carried out {MATCHED}?"), [("maintenance_record", {"maintenance_id": MATCHED})])

    def test_the_repairs_table_has_a_technician_column(self):
        r = self.A.repairs("WELL-9001", start="2025-10-01", end="2026-03-15")
        cols = r["visuals"]["table"]["columns"]
        self.assertEqual(cols[-1], "Technician")
        by_id = {row[0]: row[cols.index("Technician")] for row in r["visuals"]["table"]["rows"]}
        self.assertEqual(by_id[MATCHED], "Bob Test (U-2)")

    def test_the_evidence_drawer_shows_the_technician(self):
        fields = dict(map(tuple, resolve(self.A, MATCHED)["fields"]))
        self.assertEqual(fields["Technician"], "Bob Test (U-2)")


class MissingTechnicianTests(TechnicianCase):
    def test_a_null_technician_id_is_reported_as_not_recorded(self):
        self.assertEqual(tuple(self.joined(MISSING)), (None, None))
        r = self.A.maintenance_record(MISSING)
        self.assertEqual(r["data"]["technician_status"], "not_recorded")
        self.assertIsNone(r["data"]["technician_name"])
        self.assertIn("not recorded", r["facts"][0]["text"])
        self.assertEqual(r["facts"][0]["cites"], [MISSING])
        self.assertEqual([f["type"] for f in r["flags"]], ["missing_evidence"])
        self.assertEqual(r["visuals"]["table"]["rows"][0][4:6], ["—", "Not recorded"])

    def test_no_user_name_leaks_into_a_not_recorded_answer(self):
        text = json.dumps(self.A.maintenance_record(MISSING)["facts"])
        for u in self.A.users.values():
            self.assertNotIn(u["name"] or "\0", text)

    def test_the_table_and_the_drawer_say_not_recorded(self):
        r = self.A.repairs("WELL-9002", start="2025-12-01", end="2026-03-15")
        cols = r["visuals"]["table"]["columns"]
        by_id = {row[0]: row[cols.index("Technician")] for row in r["visuals"]["table"]["rows"]}
        self.assertEqual(by_id[MISSING], "Not recorded")
        self.assertEqual(dict(map(tuple, resolve(self.A, MISSING)["fields"]))["Technician"], "Not recorded")

    def test_a_guessed_name_is_rejected_and_replaced_by_the_verified_facts(self):
        out = self.agent(("call", "maintenance_record", {"maintenance_id": MISSING}),
                         ("text", f"{MISSING} was carried out by Bob Test [{MISSING}].")).respond(ALICE, None, f"Who carried out {MISSING}?")
        self.assertEqual(out["answer_source"], "verified facts")
        self.assertIn("Bob Test", out["warnings"][0])
        self.assertNotIn("Bob Test", out["answer"])
        self.assertIn("not recorded", out["answer"])

    def test_an_honest_not_recorded_wording_is_accepted(self):
        out = self.agent(("call", "maintenance_record", {"maintenance_id": MISSING}),
                         ("text", f"The technician is not recorded for {MISSING} [{MISSING}].")).respond(ALICE, None, f"Who carried out {MISSING}?")
        self.assertEqual((out["answer_source"], out["warnings"]), ("model", []))


class UnmatchedTechnicianTests(TechnicianCase):
    def test_an_id_with_no_user_is_not_turned_into_a_name(self):
        self.assertEqual(tuple(self.joined(UNMATCHED)), ("U-999", None))
        r = self.A.maintenance_record(UNMATCHED)
        self.assertEqual((r["data"]["technician_status"], r["data"]["technician_user_id"], r["data"]["technician_name"]), ("unmatched", "U-999", None))
        self.assertIn("U-999", r["facts"][0]["text"])
        self.assertIn("cannot be said", r["facts"][0]["text"])
        self.assertEqual(r["facts"][0]["cites"], [UNMATCHED])
        self.assertEqual([f["type"] for f in r["flags"]], ["missing_evidence"])
        self.assertEqual(r["visuals"]["table"]["rows"][0][4:6], ["U-999", "Name not available"])

    def test_the_table_and_the_drawer_show_the_id_with_no_name(self):
        r = self.A.repairs("WELL-9002", start="2025-12-01", end="2026-03-15")
        cols = r["visuals"]["table"]["columns"]
        by_id = {row[0]: row[cols.index("Technician")] for row in r["visuals"]["table"]["rows"]}
        self.assertEqual(by_id[UNMATCHED], "U-999 (name not available)")
        self.assertEqual(dict(map(tuple, resolve(self.A, UNMATCHED)["fields"]))["Technician"], "U-999 (name not available)")

    def test_a_user_record_with_an_empty_name_counts_as_name_not_available(self):
        r = self.A.maintenance_record(UNNAMED)
        self.assertEqual((r["data"]["technician_status"], r["data"]["technician_name"]), ("unmatched", None))
        self.assertIn("U-3", r["facts"][0]["text"])

    def test_an_invented_user_id_or_name_is_rejected(self):
        res = [self.A.maintenance_record(UNMATCHED)]
        q = f"Who carried out {UNMATCHED}?"
        self.assertEqual(ground_check(f"{UNMATCHED} lists technician U-999.", res, q, ["Bob Test"]), [])
        self.assertEqual(ground_check(f"{UNMATCHED} was done by U-2.", res, q, ["Bob Test"]), ["U-2"])
        self.assertEqual(ground_check(f"{UNMATCHED} was done by Bob Test.", res, q, ["Bob Test"]), ["Bob Test"])

    def test_the_agent_rejects_a_guessed_name(self):
        out = self.agent(("call", "maintenance_record", {"maintenance_id": UNMATCHED}),
                         ("text", f"{UNMATCHED} was carried out by Alice Test [{UNMATCHED}].")).respond(ALICE, None, f"Who carried out {UNMATCHED}?")
        self.assertEqual(out["answer_source"], "verified facts")
        self.assertNotIn("Alice Test", out["answer"])
        self.assertIn("U-999", out["answer"])


class ErrorTests(TechnicianCase):
    def test_an_unknown_record_is_an_error_not_a_guess(self):
        from ahc.analyst import ToolError
        with self.assertRaises(ToolError):
            self.A.maintenance_record("MNT-0000-000")
        with self.assertRaises(ToolError):
            self.A.maintenance_record()


class ToollessNameClaimTests(TechnicianCase):
    def test_a_person_named_without_any_records_is_never_shown(self):
        """A data question answered twice without a tool, naming a person but with no digit or record ID, used to be displayed as the model's answer."""
        out = self.agent(("text", "Bob Test carried out that job."), ("text", "Bob Test carried out that job.")).respond(ALICE, None, "Who carried out this maintenance task?")
        self.assertEqual(out["tool_calls"], [])
        self.assertNotIn("Bob Test", out["answer"])
        self.assertEqual(out["answer"], "I could not find an answer in the records.")


@unittest.skipUnless((SAMPLE / "fleet").is_dir(), "official sample dataset not present in data/sample-data")
class FollowUpSequenceOnTheSampleDataTests(unittest.TestCase):
    """The two-turn sequence a user types in the app, through the HTTP API, conversation history, the agent loop, the tool, the evidence
    and the grounding check, on the official sample data. Only the model is scripted, and it behaves as the real one did: on the
    follow-up it first answers from memory (naming a contractor the records do not contain), then calls the tool when a call is required."""

    TURN1, TURN2 = "show maintenance record MNT-0155-009", "Who carried out this maintenance task?"
    CALL = ("call", "maintenance_record", {"maintenance_id": "MNT-0155-009"})
    FROM_MEMORY = ("text", 'The maintenance task was carried out by the contractor "Alpine Services" [MNT-0155-009].')

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls._tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def app(self, *steps):
        self.llm = ScriptedLLM(*steps)
        n = self.id().split(".")[-1]
        app = create_app([SAMPLE], self.base / "api.sqlite3", self.base / f"mem-{n}.sqlite3", SAMPLE_AS_OF, self.llm)
        self.addCleanup(app.state.rt.store.close)
        return TestClient(app), app

    def chat(self, client, message, conv=None):
        r = client.post("/api/chat", json={"user_id": "U-201", "conv_id": conv, "message": message})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_the_follow_up_calls_the_tool_with_the_id_from_the_conversation_and_is_grounded(self):
        client, app = self.app(self.CALL, ("text", "Maintenance record MNT-0155-009 was carried out by Brian Coleman (U-304) [MNT-0155-009]."),
                               self.FROM_MEMORY, self.CALL, ("text", "Brian Coleman (U-304) carried out maintenance task MNT-0155-009 [MNT-0155-009]."))
        first = self.chat(client, self.TURN1)
        self.assertEqual([(c["name"], c["args"], c["ok"]) for c in first["tool_calls"]], [("maintenance_record", {"maintenance_id": "MNT-0155-009"}, True)])
        out = self.chat(client, self.TURN2, first["conv_id"])

        # the ID reached the model only through the stored conversation, and the answer from memory forced exactly one required call
        history = " ".join(p.text for c in self.llm.sent[2].contents for p in c.parts if getattr(p, "text", None))
        self.assertIn("MNT-0155-009", history)
        self.assertEqual([s.forced for s in self.llm.sent[2:]], [False, True, False])

        # the tool ran with that ID, and the answer is the model's wording, accepted by the grounding check
        self.assertEqual([(c["name"], c["args"], c["ok"]) for c in out["tool_calls"]], [("maintenance_record", {"maintenance_id": "MNT-0155-009"}, True)])
        self.assertEqual((out["answer_source"], out["warnings"]), ("model", []))
        self.assertIn("Brian Coleman (U-304)", out["answer"])
        self.assertNotIn("Alpine Services", out["answer"], "the claim made from memory is discarded")

        # the technician is what an independent join of the two tables says
        sql = sqlite3.connect(self.base / "api.sqlite3")
        self.addCleanup(sql.close)
        joined = sql.execute("SELECT m.technician_user_id, u.name FROM maintenance m LEFT JOIN users u ON m.technician_user_id = u.user_id WHERE m.maintenance_id = 'MNT-0155-009'").fetchone()
        self.assertEqual(joined, ("U-304", "Brian Coleman"))

        # citations: the maintenance record and its repair report
        self.assertLessEqual({"MNT-0155-009", "report:MNT-0155-009"}, {c["id"] for c in out["citations"]})

        # the grounding check, run again on the tool's own result: this answer passes, and the answer from memory is what it rejects
        with app.state.rt.session() as A:
            res = A.maintenance_record("MNT-0155-009")
            people = [u["name"] for u in A.users.values()]
        self.assertEqual(ground_check(out["answer"], [res], self.TURN2, people), [])
        self.assertEqual(ground_check(self.FROM_MEMORY[1], [], self.TURN2, people), ["MNT-0155-009"])

        # the evidence drawer and the source line agree
        ev = client.get("/api/evidence", params={"ref": "MNT-0155-009"}).json()
        self.assertEqual(dict(map(tuple, ev["fields"]))["Technician"], "Brian Coleman (U-304)")
        path, line = ("assets/" + ev["source"].split(":")[0], int(ev["source"].split(":")[1]))
        record = json.loads((SAMPLE / path).read_text(encoding="utf-8").splitlines()[line - 1])
        self.assertEqual((record["maintenance_id"], record["technician_user_id"]), ("MNT-0155-009", "U-304"))

        # both turns are in the one stored conversation
        stored = client.get(f"/api/conversations/{first['conv_id']}", params={"user_id": "U-201"}).json()
        self.assertEqual([m["role"] for m in stored], ["user", "assistant", "user", "assistant"])

    def test_if_the_model_never_calls_the_tool_nothing_unsupported_is_shown(self):
        """The failure the app showed before the fix, now the deliberate fail-safe: no records consulted means no answer, not a guess."""
        client, _ = self.app(self.CALL, ("text", "Maintenance record MNT-0155-009 was carried out by Brian Coleman (U-304) [MNT-0155-009]."), self.FROM_MEMORY, self.FROM_MEMORY)
        first = self.chat(client, self.TURN1)
        out = self.chat(client, self.TURN2, first["conv_id"])
        self.assertEqual(out["tool_calls"], [])
        self.assertEqual(out["answer"], "I could not find an answer in the records.")
        self.assertNotIn("Alpine Services", out["answer"])
        self.assertEqual(out["citations"], [])


if __name__ == "__main__":
    unittest.main()
