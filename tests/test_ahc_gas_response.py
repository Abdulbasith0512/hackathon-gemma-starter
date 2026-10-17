"""Gas-odor reports and whether a field response started in time (Operations SOP OPS-1).

The test dataset carries its own copy of the SOP with a different cutoff date (1 Feb 2026) than the real one, so the deadlines can only
come from reading the SOP. Expected results are worked out by hand in the comments, not by the code under test.
"""

import json
import tempfile
import unittest
from pathlib import Path

from ahc import db, ingest, rules
from ahc.analyst import Analyst, ToolError
from ahc.router import route
from ahc.store import Store
from tests import ahc_fixture

SOP = """# Operations SOP

## OPS-1 Gas odor response

An operator note reporting a gas smell needs a field response on that well.

A field response is either:
- a maintenance job on that well (its `started_at` in `maintenance.jsonl`), or
- an inspection of that well with `method` = `manual`. Drone inspections do not count.

The response must start after the note's `created_at` and within:
- **24 hours** for reports noted before 1 Feb 2026;
- **12 hours** for reports noted from 1 Feb 2026.

Otherwise the response is missed.
"""
W = "WELL-9003"


def note(n, at, text, kind="operator_note"):
    return {"note_id": f"CTX-9003-9{n:02d}", "asset_id": W, "created_at": at, "author_user_id": "U-3", "note_type": kind, "inspection_id": None, "text": text,
            "valid_from": at[:10], "valid_to": None}


def inspection(n, at, method):
    return {"inspection_id": f"INS-9003-9{n:02d}", "asset_id": W, "inspected_at": at, "inspector_user_id": "U-2", "method": method, "ambient_temp_c": 20.0, "wellhead_temp_c": 50.0,
            "spill_detected": False, "spill_area_pct": None, "spill_est_volume_bbl": None, "evidence_images": [], "notes": ""}


def job(n, at):
    return {"maintenance_id": f"MNT-9003-9{n:02d}", "asset_id": W, "started_at": at, "completed_at": at, "maintenance_type": "scheduled", "equipment_kind": "pump_jack", "issue": "Check",
            "action_taken": "done", "technician_user_id": "U-2", "contractor": None, "downtime_hours": 0, "cost_usd": {"labor": 1, "parts": 1, "total": 2}, "triggered_by_inspection_id": None, "report_file": None}


def append(path: Path, rows: list) -> None:
    with open(path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


class GasResponseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        root = ahc_fixture.build(base)
        (root / "fleet/sops/operations-sop.md").write_text(SOP, encoding="utf-8")
        a = root / "assets" / W
        append(a / "context.jsonl", [
            note(1, "2026-01-10T08:00:00Z", "Strong gas odor around the WELL-9003 cellar, called it in."),          # limit 24 h
            note(2, "2026-01-12T08:00:00Z", "H2S monitor alarmed at WELL-9003, crew moved upwind."),                # limit 24 h
            note(3, "2026-02-10T08:00:00Z", "Rotten-egg smell at the WELL-9003 pad on arrival."),                  # limit 12 h
            note(4, "2026-02-11T08:00:00Z", "Smelled gas downwind of WELL-9003 wellhead."),                        # limit 12 h
            note(5, "2026-02-20T08:00:00Z", "Gas odor reported by the pumper near WELL-9003 wellhead."),           # limit 12 h; the next job is 10 days later (MNT-9003-001)
            note(6, "2026-02-21T08:00:00Z", "WELL-9003 pumping normally."),                                         # not a gas report
            note(7, "2026-02-22T08:00:00Z", "Smelled gas near WELL-9003.", kind="operator_feedback"),               # not an operator note
            note(8, "2026-01-05T08:00:00Z", "Gas odor reported by the pumper near WELL-9003 wellhead."),           # before the window asked for below
            note(10, "2026-02-12T08:00:00Z", "Strong gas odor around the WELL-9003 cellar, called it in."),          # limit 12 h; the response comes after exactly 12 h
            note(9, "2026-03-14T12:00:00Z", "Gas odor reported by the pumper near WELL-9003 wellhead."),           # limit 12 h, nothing recorded after it at all
        ])
        append(a / "inspections.jsonl", [
            inspection(1, "2026-01-10T20:00:00Z", "manual"),     # note 1: 12 h later, a manual inspection -> Met
            inspection(2, "2026-01-12T10:00:00Z", "drone"),      # note 2: a drone inspection does not count
            inspection(3, "2026-02-11T21:00:00Z", "manual"),     # note 4: 13 h later, over the 12 h limit -> Missed
            inspection(4, "2026-02-10T07:00:00Z", "manual"),     # an hour BEFORE note 3: does not count as a response
            inspection(5, "2026-02-12T20:00:00Z", "manual"),     # note 10: exactly 12 h later -> "within 12 hours" is met
        ])
        append(a / "maintenance.jsonl", [
            job(1, "2026-01-13T09:00:00Z"),                      # note 2: 25 h later, over the 24 h limit -> Missed
            job(2, "2026-02-10T18:00:00Z"),                      # note 3: 10 h later, within 12 h -> Met
        ])
        cls.db_path = base / "ahc.sqlite3"
        ingest.ingest([root], cls.db_path)
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

    def run_tool(self, **kw):
        return self.A.gas_response(**{"start": "2026-01-09", "end": "2026-03-15", **kw})

    def test_every_gas_report_is_listed_with_its_response_and_verdict(self):
        r = self.run_tool()
        rows = {row[2][:10] + row[2][10:16]: row for row in r["visuals"]["table"]["rows"]}
        self.assertEqual(r["visuals"]["table"]["columns"], ["Well", "Area", "Reported at", "Response", "Hours to response", "Deadline", "Met / Missed"])
        verdicts = [(row[2], row[3].split(" ")[0], row[4], row[6]) for row in r["visuals"]["table"]["rows"]]
        self.assertEqual(verdicts, [
            ("2026-01-10 08:00 UTC", "INS-9003-901", 12.0, "Met"),
            ("2026-01-12 08:00 UTC", "MNT-9003-901", 25.0, "Missed"),     # the drone inspection two hours after the note is not a response
            ("2026-02-10 08:00 UTC", "MNT-9003-902", 10.0, "Met"),        # the manual inspection an hour earlier is not a response
            ("2026-02-11 08:00 UTC", "INS-9003-903", 13.0, "Missed"),
            ("2026-02-12 08:00 UTC", "INS-9003-905", 12.0, "Met"),        # exactly at the limit
            ("2026-02-20 08:00 UTC", "MNT-9003-001", 240.0, "Missed"),    # a response, but ten days late
            ("2026-03-14 12:00 UTC", "none", "—", "Missed"),
        ])
        self.assertEqual({k: r["data"][k] for k in ("reports", "met", "missed")}, {"reports": 7, "met": 3, "missed": 4})
        self.assertEqual(rows["2026-01-10 08:00"][5], "2026-01-11 08:00 UTC (24 h)")
        self.assertEqual(rows["2026-02-10 08:00"][5], "2026-02-10 20:00 UTC (12 h)")

    def test_the_deadline_and_the_cutoff_date_come_from_the_sop(self):
        r = self.run_tool()
        self.assertEqual((r["data"]["limits_hours"], r["data"]["cutoff"]), ({"before": 24, "from": 12}, "1 Feb 2026"))
        self.assertIn("within 24 hours of a report noted before 1 Feb 2026", r["facts"][0]["text"])

    def test_only_gas_reports_by_operators_are_included(self):
        ids = {c["id"] for c in self.run_tool()["citations"]}
        self.assertNotIn("CTX-9003-906", ids)       # "pumping normally"
        self.assertNotIn("CTX-9003-907", ids)       # an operator_feedback note, not an operator note

    def test_the_window_filters_reports(self):
        self.assertEqual(self.run_tool(start="2026-02-01")["data"]["reports"], 5)
        self.assertEqual(self.run_tool(start="2026-01-01")["data"]["reports"], 8)      # now includes the 5 Jan report

    def test_missed_reports_are_stated_in_the_facts_and_cited(self):
        r = self.run_tool()
        missed = [f for f in r["facts"][1:]]
        self.assertEqual(len(missed), 4)
        self.assertTrue(any("no response is recorded" in f["text"] and "CTX-9003-909" in f["cites"] for f in missed))
        self.assertTrue(any("after 240.0 h" in f["text"] and "MNT-9003-001" in f["cites"] for f in missed))
        self.assertTrue(all(any(c.endswith("#ops-1-gas-odor-response") for c in f["cites"]) for f in missed))

    def test_a_missing_rule_is_an_error_not_a_guess(self):
        (Path(self._tmp.name) / "empty").mkdir(exist_ok=True)
        root = ahc_fixture.build(Path(self._tmp.name) / "empty")      # a dataset without the Operations SOP
        db_path = Path(self._tmp.name) / "norule.sqlite3"
        ingest.ingest([root], db_path)
        conn = db.connect(db_path)
        self.addCleanup(conn.close)
        with self.assertRaises(ToolError):
            Analyst(conn, rules.load_rules(conn), self.store, ahc_fixture.AS_OF).gas_response(start="2026-01-01", end="2026-03-15")

    def test_the_answer_is_verified_by_recomputation_and_passes_when_right_and_fails_when_a_verdict_is_wrong(self):
        from ahc import verify
        q = "Since 9 Jan, every time an operator note reports gas at a well, did we get someone out to that well in time? List every report."
        res = self.run_tool()
        call = [{"name": "gas_response", "args": {"scope": "all", "start": "2026-01-09", "end": "2026-03-15"}}]
        ok = verify.verify_answer(self.A, q, "x", [], [res], call, res["citations"], "model")
        self.assertEqual((ok["status"], ok["reasons"]), ("PASS", []))
        self.assertTrue(any(c["check"] == "recompute gas_response" and c["outcome"] == "pass" for c in ok["checks"]))
        res["visuals"]["table"]["rows"][0][6] = "Missed"            # flip a verdict: the first report was answered within 12 h of a 24 h limit
        bad = verify.verify_answer(self.A, q, "x", [], [res], call, res["citations"], "model")
        self.assertEqual(bad["status"], "FAIL")
        self.assertIn("the table says 12.0 h and Missed", bad["reasons"][0])

    def test_the_offline_router_sends_the_question_to_the_tool(self):
        q = "Since 1 Feb, every time an operator note reports gas at a well, did we get someone out in time?"
        self.assertEqual(route(self.A, q)[0][0], "gas_response")


if __name__ == "__main__":
    unittest.main()
