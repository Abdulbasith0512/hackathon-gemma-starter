"""Golden tests: the official sample dataset against the expected answers in the Example Scenarios.

The expected values live ONLY here, never in runtime code. Skipped when data/sample-data is absent.
"""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from ahc import config, db, ingest, rules
from ahc.analyst import Analyst
from ahc.store import Store

SAMPLE = config.DATA_DIR / "sample-data"
AS_OF = date(2026, 10, 16)


@unittest.skipUnless((SAMPLE / "fleet").is_dir(), "official sample dataset not present in data/sample-data")
class GoldenCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls._tmp.name) / "ahc.sqlite3"
        ingest.ingest([SAMPLE], cls.db_path)
        cls.conn = db.connect(cls.db_path)
        cls.rules = rules.load_rules(cls.conn)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls._tmp.cleanup()

    def setUp(self):
        self.store = Store(Path(self._tmp.name) / f"{self.id().split('.')[-1]}.sqlite3")
        self.addCleanup(self.store.close)
        self.A = Analyst(self.conn, self.rules, self.store, AS_OF)

    def fresh(self):
        return Analyst(self.conn, self.rules, self.store, AS_OF)

    @staticmethod
    def cited(r):
        return {c["id"] for c in r["citations"]}


class A1Tests(GoldenCase):
    def test_q1_status_of_well_0001(self):
        r = self.A.well_status("WELL-0001")
        d = r["data"]
        self.assertEqual((d["producing"], d["delta_c"], d["inspection_id"], d["inspector"], d["method"]), (False, 3.2, "INS-0001-0203", "Ryan Brooks", "drone"))
        self.assertEqual(d["inspected_at"][:10], "2026-10-15")
        self.assertTrue(d["recorded_status_stale"])
        self.assertEqual(d["recorded_status"], "active")
        self.assertTrue({"INS-0001-0203", "CTX-0001-003", "T200#9.3"} <= self.cited(r))
        text = " ".join(f["text"] for f in r["facts"])
        self.assertIn("Jake Morales", text)
        self.assertIn("7 Oct", text)
        self.assertIn("not yet in the maintenance system", text)
        self.assertEqual(r["natural"], "status_card")

    def test_q2_wells_not_producing_in_northeast_block_8(self):
        r = self.A.wells_not_producing("Northeast Block 8")
        rows = {row[0]: row for row in r["visuals"]["table"]["rows"]}
        self.assertEqual(sorted(rows), ["WELL-0164", "WELL-0170", "WELL-0172", "WELL-0175"])
        self.assertEqual([rows[w][1] for w in sorted(rows)], ["4.1 °C", "2.9 °C", "5.7 °C", "0.4 °C"])
        self.assertEqual(rows["WELL-0164"][2], "active (out of date)")
        self.assertEqual(rows["WELL-0170"][2], "down")
        self.assertTrue(rows["WELL-0164"][3].startswith("No recorded reason") and "Pump jack not moving." in rows["WELL-0164"][3])
        self.assertIn("MNT-0170-031", rows["WELL-0170"][3])
        self.assertIn("still open", rows["WELL-0170"][3])
        self.assertIn("MNT-0172-028", rows["WELL-0172"][3])
        self.assertEqual(rows["WELL-0175"][3], "No recorded reason")
        self.assertEqual(r["natural"], "table")

    def test_q3_thirteen_week_series(self):
        r = self.A.inspection_series("WELL-0001", 13)
        self.assertEqual(r["data"]["points"], 13)
        line = r["visuals"]["line"]
        self.assertEqual((line["x"][0], line["x"][-1]), ("2026-07-23", "2026-10-15"))
        self.assertEqual(r["data"]["not_producing_dates"], ["2026-10-08", "2026-10-15"])
        self.assertEqual(r["natural"], "line")

    def test_q4_spills_for_well_0001(self):
        r = self.A.spills("WELL-0001", "last 4 years")
        self.assertEqual((r["data"]["count"], r["data"]["total_bbl"]), (6, 15.1))
        self.assertEqual(r["data"]["excluded"], ["INS-0001-0070"])
        rows = r["visuals"]["table"]["rows"]
        self.assertEqual([(row[0], row[2]) for row in rows], [("2023-03-16", 0.5), ("2023-04-27", 2.6), ("2023-09-28", 3.3), ("2023-10-19", 0.3), ("2026-06-11", 6.8), ("2026-10-01", 1.6)])
        self.assertIn("CTX-0001-001", self.cited(r))

    def test_q5_downtime_2025(self):
        r = self.A.downtime("WELL-0001", "2025")
        self.assertEqual(r["data"]["total_days"], 21)
        text = " ".join(f["text"] for f in r["facts"])
        self.assertIn("24 Jul 2025", text)
        self.assertIn("51.6", text)
        self.assertIn("43.1", text)
        self.assertIn("8.5", text)
        self.assertTrue({"MNT-0001-021", "MNT-0001-023"} <= self.cited(r))

    def test_q6_top_three_downtime_northeast_block_7(self):
        r = self.A.downtime_ranking("Northeast Block 7", "last 4 months", 3)
        self.assertEqual(r["window"]["start"], "2026-06-16")
        self.assertEqual(r["window"]["end"], "2026-10-16")
        self.assertEqual({x["asset_id"]: x["days"] for x in r["data"]["ranking"]}, {"WELL-0121": 49, "WELL-0138": 42, "WELL-0107": 42})
        self.assertEqual({x["asset_id"]: x["well_type"] for x in r["data"]["ranking"]}, {"WELL-0121": "T200", "WELL-0138": "T350", "WELL-0107": "T350"})
        self.assertEqual(r["data"]["next"], {"asset_id": "WELL-0119", "days": 28})
        self.assertEqual(r["natural"], "bar")

    def test_q7_map_of_real_spills_in_northeast_block_8(self):
        r = self.A.spills("Northeast Block 8", "last 90 days")
        pins = {p["asset_id"]: p for p in r["visuals"]["map"]["points"]}
        self.assertEqual({a: (p["date"], p["value"]) for a, p in pins.items()},
                         {"WELL-0151": ("2026-09-24", 4.5), "WELL-0165": ("2026-07-30", 1.2), "WELL-0175": ("2026-07-30", 3.9), "WELL-0186": ("2026-07-23", 0.6)})
        self.assertEqual((pins["WELL-0151"]["lat"], pins["WELL-0151"]["lon"]), (32.12246, -102.18445))
        self.assertEqual((pins["WELL-0186"]["lat"], pins["WELL-0186"]["lon"]), (32.17552, -102.17775))

    def test_q8_heatmap_of_2026_spills(self):
        r = self.A.spill_heatmap("2026")
        expected = {"Southwest Block 23": [4, 3, 3, 6, 3, 4, 4, 3, 3, 2, 35], "Southwest Block 24": [7, 4, 5, 6, 5, 5, 3, 1, 5, 2, 43],
                    "Northeast Block 7": [5, 3, 2, 4, 6, 6, 2, 4, 4, 1, 37], "Northeast Block 8": [4, 4, 4, 3, 2, 4, 4, 0, 1, 0, 26]}
        for area, row in expected.items():
            self.assertEqual(r["data"]["matrix"][area] + [r["data"]["totals"][area]], row, area)
        self.assertEqual(r["visuals"]["heatmap"]["cols"], ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct"])

    def test_q11_repair_costs_this_year(self):
        r = self.A.repair_costs(["WELL-0121", "WELL-0138", "WELL-0107"], "this year")
        self.assertEqual(r["data"]["per_well"], {"WELL-0121": 25794, "WELL-0138": 46942, "WELL-0107": 5176})

    def test_q14_pump_jack_rca_candidates_before_and_after_the_type_rule(self):
        self.assertEqual(self.A.rca_candidates("Northeast Block 7")["data"]["wells"], ["WELL-0108", "WELL-0121", "WELL-0138"])
        rule = self.store.add_scoped_rule(scope_type="well_type", scope_value="T350", key="rca_corrective_count", value=2, unit="repairs", reason="team policy",
                                          author_user_id="U-201", equipment_kind="pump_jack")
        r = self.fresh().rca_candidates("Northeast Block 7")
        self.assertEqual(r["data"]["wells"], ["WELL-0108", "WELL-0120", "WELL-0121", "WELL-0138"])
        self.assertNotIn("WELL-0102", r["data"]["wells"])  # 2 repairs, but a T200 well: the rule is scoped to T350
        self.assertEqual(self.fresh().wells["WELL-0102"]["well_type"], "T200")
        text = " ".join(f["text"] for f in r["facts"])
        self.assertIn("Michael Turner", text)
        self.assertIn("not the manual", text)
        self.assertIn(rule["rule_id"], self.cited(r))


class CorrectionScenarioTests(GoldenCase):
    def test_q12_raw_data_correction_flips_status_and_reaches_every_user(self):
        ins = self.A.get_inspection("INS-0164-0205")
        self.assertEqual((ins["orig"]["wellhead_temp_c"], ins["ambient_temp_c"], ins["notes"]), (24.0, 19.9, "Pump jack not moving."))
        self.store.add_correction(target_id="INS-0164-0205", asset_id="WELL-0164", field="wellhead_temp_c", original=24.0, previous=24.0, new=41.0,
                                  reason="The handheld thermal gun was faulty; the crew re-measured 41.0 C", author_user_id="U-201")
        after = self.fresh()
        i = after.get_inspection("INS-0164-0205")
        self.assertEqual((i["wellhead_temp_c"], i["orig"]["wellhead_temp_c"], i["delta"], i["producing"]), (41.0, 24.0, 21.1, True))
        rows = {row[0] for row in after.wells_not_producing("Northeast Block 8")["visuals"]["table"]["rows"]}
        self.assertEqual(rows, {"WELL-0170", "WELL-0172", "WELL-0175"})
        status = after.well_status("WELL-0164")
        self.assertIs(status["data"]["producing"], True)
        self.assertTrue(any(f["type"] == "corrected" and "Michael Turner" in f["text"] for f in status["flags"]))

    def test_q13_ai_volume_correction_changes_the_spill(self):
        self.store.add_correction(target_id="INS-0151-0201", asset_id="WELL-0151", field="spill_est_volume_bbl", original=4.5, previous=4.5, new=5.4,
                                  reason="Field crew measured 5.4 bbl", author_user_id="U-201")
        r = self.fresh().spills("Northeast Block 8", "last 90 days")
        vols = {row[1]: row[2] for row in r["visuals"]["table"]["rows"]}
        self.assertEqual(vols["WELL-0151"], 5.4)
        self.assertEqual(self.fresh().get_inspection("INS-0151-0201")["orig"]["spill_est_volume_bbl"], 4.5)


class ReportFactTests(GoldenCase):
    def test_containment_times_come_from_repair_reports_found_through_report_file(self):
        q = "SELECT containment_hours h FROM report_facts WHERE maintenance_id=?"
        got = {m: self.conn.execute(q, (m,)).fetchone()["h"] for m in ("MNT-0082-028", "MNT-0100-034", "MNT-0151-025", "MNT-0001-029")}
        self.assertEqual(got, {"MNT-0082-028": 7.1, "MNT-0100-034": 8.1, "MNT-0151-025": 6.4, "MNT-0001-029": 7.0})
        self.assertEqual(self.conn.execute("SELECT spill_class FROM report_facts WHERE maintenance_id='MNT-0151-025'").fetchone()[0], "moderate")
        self.assertEqual(self.conn.execute("SELECT action_required FROM report_facts WHERE maintenance_id='MNT-0001-032'").fetchone()[0], 1)

    def test_every_spill_report_has_a_containment_time(self):
        n = self.conn.execute("SELECT COUNT(*) FROM maintenance m JOIN inspections i ON i.inspection_id=m.triggered_by_inspection_id LEFT JOIN report_facts f ON f.maintenance_id=m.maintenance_id "
                              "WHERE m.report_file IS NOT NULL AND i.spill_detected=1 AND f.containment_hours IS NULL").fetchone()[0]
        self.assertEqual(n, 0)


if __name__ == "__main__":
    unittest.main()
