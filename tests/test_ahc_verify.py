"""Answer verification and the backend audit log.

Every answer is checked against the dataset by independent recomputation (never against itself) and recorded in a separate SQLite file.
The audit rows are read back with plain sqlite3, not through the code under test.
"""

import functools
import json
import sqlite3
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from ahc import verify
from ahc.agent import Agent
from ahc.analyst import Analyst
from ahc.audit import AuditLog
from ahc.server import create_app
from tests import ahc_fixture
from tests.test_ahc_agent import ALICE, RANK, AgentCase, ScriptedLLM

RANK_Q = "Which wells in Gamma Block 9 were down the longest in 2026?"
GOOD = "WELL-9002 had the most downtime: 63 days [WELL-9002]."


class VerifyCase(AgentCase):
    def setUp(self):
        super().setUp()
        self.audit_path = Path(self._tmp.name) / f"audit-{self.id().split('.')[-1]}.sqlite3"
        self.audit = AuditLog(self.audit_path, "fixture-v1")

    def agent(self, *steps, **kw):
        self.llm = ScriptedLLM(*steps, **kw)
        return Agent(self.A, self.store, self.llm, audit=self.audit)

    def rows(self):
        c = sqlite3.connect(self.audit_path)
        c.row_factory = sqlite3.Row
        self.addCleanup(c.close)
        return [dict(r) for r in c.execute("SELECT * FROM answer_audit ORDER BY seq")]


class CorrectAnswerTests(VerifyCase):
    def test_a_correct_answer_passes_and_is_recorded_in_sqlite(self):
        out = self.agent(("call", "downtime_ranking", RANK), ("text", GOOD)).respond(ALICE, None, RANK_Q)
        self.assertEqual((out["answer_source"], out["warnings"]), ("model", []))
        self.assertEqual(out["verification"]["status"], "PASS")
        self.assertEqual(out["verification"]["reasons"], [])
        (row,) = self.rows()
        self.assertEqual((row["status"], row["question"], row["dataset_version"]), ("PASS", RANK_Q, "fixture-v1"))
        self.assertEqual(row["evaluation_id"], out["verification"]["evaluation_id"])
        self.assertEqual((row["generated_answer"], row["shown_answer"]), (GOOD, GOOD))
        self.assertIn("WELL-9002", json.loads(row["evidence_refs"]))
        self.assertEqual(json.loads(row["failure_reasons"]), [])
        self.assertEqual(json.loads(row["tools"]), ["downtime_ranking"])
        self.assertTrue(row["created_at"].endswith("+00:00") and isinstance(row["turn_id"], int) and row["conv_id"] == out["conv_id"])
        passed = [c for c in json.loads(row["checks"]) if c["outcome"] == "pass"]
        self.assertTrue(any(c["check"] == "recompute downtime_ranking" for c in passed), "a number was recomputed independently, not just cited")

    def test_the_audit_table_has_every_required_field_and_rejects_an_invalid_status(self):
        c = sqlite3.connect(self.audit_path)
        self.addCleanup(c.close)
        cols = {r[1] for r in c.execute("PRAGMA table_info(answer_audit)")}
        self.assertLessEqual({"evaluation_id", "conv_id", "turn_id", "question", "generated_answer", "evidence_refs", "status", "failure_reasons", "dataset_version", "created_at"}, cols)
        with self.assertRaises(sqlite3.IntegrityError):
            c.execute("INSERT INTO answer_audit(evaluation_id,question,status,created_at) VALUES ('x','q','MAYBE','now')")


class IncorrectCalculationTests(VerifyCase):
    def doctored(self):
        orig = Analyst.downtime_ranking

        @functools.wraps(orig)
        def wrong(self_, *a, **k):
            r = orig(self_, *a, **k)
            r["data"]["ranking"][0]["days"] += 7           # a calculation error in the tool's result
            return r
        return mock.patch.object(Analyst, "downtime_ranking", wrong)

    def test_a_wrong_downtime_figure_fails_and_the_answer_is_not_rewritten(self):
        with self.doctored():
            out = self.agent(("call", "downtime_ranking", RANK), ("text", "WELL-9002 had the most downtime: 70 days [WELL-9002].")).respond(ALICE, None, RANK_Q)
        self.assertEqual(out["verification"]["status"], "FAIL")
        self.assertIn("recomputed", " ".join(out["verification"]["reasons"]))
        self.assertIn("63 downtime days", " ".join(out["verification"]["reasons"]))
        self.assertIn("70 days", out["answer"], "the original answer is left as it was and flagged, not corrected")
        (row,) = self.rows()
        self.assertEqual(row["status"], "FAIL")
        self.assertIn("70 days", row["generated_answer"])

    def test_a_wrong_single_well_downtime_total_fails(self):
        res = self.A.downtime("WELL-9002", start="2026-01-01", end="2026-03-15")
        self.assertEqual(res["data"]["total_days"], 63)
        res["data"]["total_days"] = 70
        v = verify.verify_answer(self.A, "How many days was WELL-9002 down in 2026?", "x", [], [res], [{"name": "downtime", "args": {"scope": "WELL-9002"}}], res["citations"], "model")
        self.assertEqual(v["status"], "FAIL")
        self.assertIn("recomputed as 63 days, the answer says 70", v["reasons"][0])

    def test_wrong_spill_and_cost_figures_are_caught_the_same_way(self):
        res = self.A.spills("all", start="2026-01-01", end="2026-03-15")
        res["data"]["count"] += 1
        v = verify.verify_answer(self.A, "How many spills?", "x", [], [res], [{"name": "spills", "args": {"scope": "all"}}], res["citations"], "model")
        self.assertEqual(v["status"], "FAIL")
        self.assertIn("recounted", v["reasons"][0])
        res = self.A.repairs("Gamma Block 9", start="2026-01-01", end="2026-03-15")
        res["data"]["total_usd"] += 100
        v = verify.verify_answer(self.A, "What did repairs cost?", "x", [], [res], [{"name": "repairs", "args": {"scope": "Gamma Block 9"}}], res["citations"], "model")
        self.assertEqual(v["status"], "FAIL")
        self.assertIn("recomputed", v["reasons"][0])

    def test_a_wrong_production_status_fails_against_the_manual_threshold(self):
        res = self.A.well_status("WELL-9002")           # 18 degrees above air against a 20 degree limit: not producing
        self.assertFalse(res["data"]["producing"])
        res["data"]["producing"] = True
        v = verify.verify_answer(self.A, "Is WELL-9002 producing oil right now?", "x", [], [res], [{"name": "well_status", "args": {"asset_id": "WELL-9002"}}], res["citations"], "model")
        self.assertEqual(v["status"], "FAIL")
        self.assertIn("recomputed status is not producing", v["reasons"][0])


class UnsupportedClaimTests(VerifyCase):
    def test_a_number_the_records_do_not_contain_fails_and_the_original_wording_is_kept_in_the_log(self):
        out = self.agent(("call", "downtime_ranking", RANK), ("text", "WELL-9002 had 70 days of downtime.")).respond(ALICE, None, RANK_Q)
        self.assertEqual(out["answer_source"], "verified facts")           # the existing grounding check shows the facts, not the claim
        self.assertEqual(out["verification"]["status"], "FAIL")
        self.assertIn("70", out["verification"]["reasons"][0])
        (row,) = self.rows()
        self.assertEqual(row["status"], "FAIL")
        self.assertEqual(row["generated_answer"], "WELL-9002 had 70 days of downtime.")
        self.assertNotIn("70 days", row["shown_answer"])
        self.assertIn("63 days", row["shown_answer"])

    def test_an_answer_given_without_any_records_is_withheld_and_logged_as_unsupported(self):
        claim = "WELL-9002 produced 63 barrels, the most in 2026."
        out = self.agent(("text", claim), ("text", claim)).respond(ALICE, None, "Which well produced the most oil in 2026?")
        self.assertEqual(out["answer"], "I could not find an answer in the records.")
        self.assertEqual(out["verification"]["status"], "FAIL")
        (row,) = self.rows()
        self.assertEqual(row["generated_answer"], claim)
        self.assertIn("withheld", " ".join(json.loads(row["failure_reasons"])))


class InvalidCitationTests(VerifyCase):
    def test_a_citation_that_resolves_to_nothing_fails(self):
        orig = Analyst.downtime_ranking

        @functools.wraps(orig)
        def with_bad_citation(self_, *a, **k):
            r = orig(self_, *a, **k)
            r["citations"] = r["citations"] + [{"id": "INS-9999-0001", "type": "inspection", "label": "INS-9999-0001"}]
            return r
        with mock.patch.object(Analyst, "downtime_ranking", with_bad_citation):
            out = self.agent(("call", "downtime_ranking", RANK), ("text", GOOD)).respond(ALICE, None, RANK_Q)
        self.assertEqual(out["verification"]["status"], "FAIL")
        self.assertIn("INS-9999-0001", out["verification"]["reasons"][0])
        self.assertIn("do not resolve", out["verification"]["reasons"][0])
        self.assertEqual(self.rows()[0]["status"], "FAIL")

    def test_report_sections_and_saved_records_count_as_valid_citations(self):
        sec = self.A.c.execute("SELECT substr(doc_id, instr(doc_id, ':') + 1) d, section_id s FROM sections WHERE doc_id LIKE 'manual:%' LIMIT 1").fetchone()
        self.assertTrue(verify._citation_ok(self.A, f"{sec['d']}#{sec['s']}"))
        self.assertFalse(verify._citation_ok(self.A, f"{sec['d']}#no-such-section"))

    def test_a_pump_serial_number_is_not_mistaken_for_a_saved_note_id(self):
        v = verify.verify_answer(self.A, "Anything?", "The pump serial is SN-378851, lot LOT-2291.", [], [], [], [], "model")
        self.assertNotIn("SN-378851", " ".join(v["reasons"]))
        v = verify.verify_answer(self.A, "Anything?", "See note SN-0042.", [], [], [], [], "model")      # a real note-ID shape that does not exist
        self.assertIn("SN-0042", " ".join(v["reasons"]))

    def test_a_record_id_written_in_the_answer_must_exist(self):
        v = verify.verify_answer(self.A, "Anything?", "See INS-9999-0001 and WELL-9001.", [], [], [], [], "model")
        self.assertEqual(v["status"], "FAIL")
        self.assertIn("INS-9999-0001", v["reasons"][0])
        self.assertNotIn("WELL-9001", v["reasons"][0])


class AmbiguousQuestionTests(VerifyCase):
    def test_a_question_with_no_records_behind_it_needs_review(self):
        out = self.agent(("text", "Which well do you mean?"), ("text", "Which well do you mean?")).respond(ALICE, None, "Is it producing?")
        self.assertEqual(out["tool_calls"], [])
        self.assertEqual(out["verification"]["status"], "NEEDS_REVIEW")
        self.assertIn("No records were consulted", out["verification"]["reasons"][0])
        self.assertEqual(self.rows()[0]["status"], "NEEDS_REVIEW")

    def test_a_pronoun_the_model_resolved_by_itself_needs_review_even_if_the_numbers_are_right(self):
        out = self.agent(("call", "well_status", {"asset_id": "WELL-9002"}), ("text", "WELL-9002 is not producing oil: 18.0 °C above air against a 20.0 °C limit [INS-9002-0009].")
                         ).respond(ALICE, None, "Is it producing?")
        self.assertEqual(out["verification"]["status"], "NEEDS_REVIEW")
        self.assertTrue(any("pronoun" in r for r in out["verification"]["reasons"]))
        self.assertTrue(any(c["outcome"] == "pass" and c["check"] == "recompute well_status" for c in verify.verify_answer(
            self.A, "Is it producing?", "", [], [self.A.well_status("WELL-9002")], [{"name": "well_status", "args": {"asset_id": "WELL-9002"}}], [], "model")["checks"]))

    def test_a_tool_the_question_does_not_point_to_needs_review_not_pass(self):
        res = self.A.repairs("Gamma Block 9", start="2026-01-01", end="2026-03-15")        # numbers are right, but the question asked about spills
        v = verify.verify_answer(self.A, "How many spills did Gamma Block 9 have in 2026?", "x", [], [res], [{"name": "repairs", "args": {"scope": "Gamma Block 9"}}], res["citations"], "model")
        self.assertEqual(v["status"], "NEEDS_REVIEW")
        self.assertIn("points to spills", " ".join(v["reasons"]))

    def test_nothing_recomputed_means_needs_review_even_when_nothing_failed(self):
        res = self.A.downtime("WELL-9001", start="2026-01-01", end="2026-03-15")
        res["data"] = {"scope": "WELL-9001", "by_group": {}}              # a shape this verifier does not recompute
        v = verify.verify_answer(self.A, "How many days was WELL-9001 down in 2026?", "x", [], [res], [{"name": "downtime", "args": {"scope": "WELL-9001"}}], res["citations"], "model")
        self.assertEqual(v["status"], "NEEDS_REVIEW")
        self.assertIn("No number in this answer was recomputed", " ".join(v["reasons"]))

    def test_a_tool_with_no_independent_recomputation_is_never_a_pass(self):
        res = self.A.well_context("WELL-9001")
        v = verify.verify_answer(self.A, "What notes are there for WELL-9001?", "x", [], [res], [{"name": "well_context", "args": {"asset_id": "WELL-9001"}}], res["citations"], "model")
        self.assertEqual(v["status"], "NEEDS_REVIEW")
        self.assertIn("No independent recomputation exists", " ".join(v["reasons"]))


class ReportEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tempfile
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = ahc_fixture.build(Path(cls._tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_the_full_flow_question_answer_verification_audit_record_report(self):
        llm = ScriptedLLM(("call", "downtime_ranking", RANK), ("text", GOOD),                       # 1: correct
                          ("call", "downtime_ranking", RANK), ("text", "WELL-9002 had 70 days."),   # 2: unsupported number
                          ("text", "Which well?"), ("text", "Which well?"))                         # 3: ambiguous, no records
        app = create_app([self.root], Path(self._tmp.name) / "api.sqlite3", Path(self._tmp.name) / "mem.sqlite3", ahc_fixture.AS_OF, llm)
        c = TestClient(app)
        for q in (RANK_Q, RANK_Q, "Is it producing?"):
            r = c.post("/api/chat", json={"user_id": ALICE, "message": q})
            self.assertEqual(r.status_code, 200, r.text)
            self.assertIn(r.json()["verification"]["status"], ("PASS", "FAIL", "NEEDS_REVIEW"))
        report = c.get("/api/eval/report").json()
        self.assertEqual(report["totals"], {"PASS": 1, "FAIL": 1, "NEEDS_REVIEW": 1, "total": 3})
        (failed,) = report["failed"]
        self.assertEqual(failed["question"], RANK_Q)
        self.assertEqual(failed["generated_answer"], "WELL-9002 had 70 days.")
        self.assertIn("70", failed["reasons"][0])
        self.assertEqual(len(report["needs_review"]), 1)
        self.assertEqual(len(report["dataset_versions"]), 1)
        text = json.dumps(report)
        for private in ("conv_id", "user_id", "U-1", "turn_id"):
            self.assertNotIn(private, text, "the report must not expose users or conversations")
        # the same rows, read straight from the audit file
        db = sqlite3.connect(app.state.rt.audit.path)
        self.addCleanup(db.close)
        self.assertEqual(sorted(r[0] for r in db.execute("SELECT status FROM answer_audit")), ["FAIL", "NEEDS_REVIEW", "PASS"])
        self.assertNotEqual(Path(app.state.rt.audit.path), Path(self._tmp.name) / "mem.sqlite3")
        app.state.rt.store.close()


if __name__ == "__main__":
    unittest.main()
