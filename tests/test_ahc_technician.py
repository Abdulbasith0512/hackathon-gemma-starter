"""Who carried out a maintenance job: a matched technician, a missing technician ID, and an ID with no matching user.

The expected names come from the fixture's users.json and from a join written independently in the test,
so the code under test is not checking itself.
"""

import json
import tempfile
import unittest
from pathlib import Path

from ahc import db, ingest, rules
from ahc.agent import Agent, ground_check
from ahc.analyst import Analyst
from ahc.evidence import resolve
from ahc.router import route
from ahc.store import Store
from tests import ahc_fixture
from tests.test_ahc_agent import ALICE, ScriptedLLM

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


if __name__ == "__main__":
    unittest.main()
