"""Ingestion, rules, calculations, corrections: on a synthetic dataset with IDs that are not in the sample."""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from ahc import db, ingest, periods, rules
from ahc.analyst import Analyst, ToolError
from ahc.store import Store
from tests import ahc_fixture


class FixtureCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        cls.root = ahc_fixture.build(base)
        cls.db_path = base / "ahc.sqlite3"
        cls.stats = ingest.ingest([cls.root], cls.db_path)
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


class IngestTests(FixtureCase):
    def test_counts(self):
        s = self.stats
        self.assertEqual((s["wells"], s["inspections"], s["maintenance"], s["notes"], s["reports"]), (3, 27, 8, 2, 1))
        self.assertEqual(s["issue_count"], 0)

    def test_report_is_found_through_report_file_not_by_guessing_the_name(self):
        row = self.conn.execute("SELECT containment_hours, spill_class FROM report_facts WHERE maintenance_id='MNT-9003-001'").fetchone()
        self.assertEqual((row["containment_hours"], row["spill_class"]), (6.5, "moderate"))

    def test_reuses_database_when_nothing_changed(self):
        self.assertTrue(ingest.ingest([self.root], self.db_path)["reused"])

    def test_manual_sections_are_citable(self):
        row = self.conn.execute("SELECT heading FROM sections WHERE doc_id='manual:T200' AND section_id='9.3'").fetchone()
        self.assertIn("Production temperature rule", row["heading"])
        self.assertTrue(self.conn.execute("SELECT 1 FROM sections WHERE section_id='SR-02'").fetchone())

    def test_missing_folder_gives_a_clear_error(self):
        with self.assertRaisesRegex(FileNotFoundError, "AHC_DATA_DIRS"):
            ingest.ingest([Path(self._tmp.name) / "nope"], Path(self._tmp.name) / "x.sqlite3")

    def test_a_second_root_extends_the_first(self):
        extra = Path(tempfile.mkdtemp(dir=self._tmp.name))
        d = extra / "assets/WELL-9100"
        d.mkdir(parents=True)
        (d / "metadata.json").write_text('{"asset_id":"WELL-9100","name":"X","well_type":"T200","area_id":"D-04","location":{"lat":1,"lon":2},"recorded_status":"down"}')
        (d / "inspections.jsonl").write_text('{"inspection_id":"INS-9100-0001","asset_id":"WELL-9100","inspected_at":"2026-03-09T10:00:00Z","ambient_temp_c":10,"wellhead_temp_c":40,"spill_detected":false}\n')
        out = Path(self._tmp.name) / "two-roots.sqlite3"
        ingest.ingest([self.root, extra], out)
        c = db.connect(out)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM wells").fetchone()[0], 4)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM inspections").fetchone()[0], 28)
        c.close()


class RulesTests(FixtureCase):
    def test_thresholds_come_from_the_manuals(self):
        self.assertEqual(self.rules.value("production_delta_c", "T200"), 15.0)
        self.assertEqual(self.rules.value("production_delta_c", "T350"), 20.0)
        self.assertEqual(self.rules.get("production_delta_c", "T200").ref, "T200#9.3")
        self.assertIn("15 °C above", self.rules.get("production_delta_c", "T200").quote)

    def test_inherited_and_sop_rules(self):
        inherited = self.rules.get("downtime_report_days", "T350")
        self.assertEqual((inherited.value, inherited.inherited_from), (14.0, "T200"))
        self.assertEqual(self.rules.value("rca_corrective_count", "T350"), 3.0)
        self.assertEqual([self.rules.value(k) for k in ("sr01.hours", "sr02.hours", "sr03.days", "rc04.days", "spill.reportable_min_bbl")], [24.0, 4.0, 60.0, 30.0, 5.0])
        self.assertFalse(any(r.fallback for r in self.rules.all()))

    def test_unknown_well_type_has_no_rule_instead_of_a_guess(self):
        self.assertIsNone(self.rules.get("production_delta_c", "T999"))


class StatusAndDowntimeTests(FixtureCase):
    def test_threshold_is_per_well_type(self):
        i = self.A.latest("WELL-9002")  # delta 18: producing for T200's 15, not for T350's 20
        self.assertEqual((i["delta"], i["threshold"], i["producing"]), (18.0, 20.0, False))
        self.assertTrue(self.A.latest("WELL-9003")["producing"])

    def test_hot_day_is_judged_by_the_difference_not_the_absolute_temperature(self):
        hot = self.A.get_inspection("INS-9001-0006")
        self.assertEqual(hot["wellhead_temp_c"], 60.0)
        self.assertEqual((hot["delta"], hot["producing"]), (14.9, False))

    def test_exactly_at_the_threshold_counts_as_producing(self):
        self.assertTrue(self.A.get_inspection("INS-9001-0007")["producing"])

    def test_downtime_counts_non_producing_inspections_times_seven_and_ignores_repair_hours(self):
        r = self.A.downtime("WELL-9001", start="2026-01-01", end="2026-03-15")
        self.assertEqual(r["data"]["total_days"], 35)  # 5 non-producing weeks; the missed week and downtime_hours=999 add nothing

    def test_period_bounds_are_inclusive(self):
        self.assertEqual(self.A.downtime("WELL-9001", start="2026-03-09", end="2026-03-09")["data"]["total_days"], 7)
        self.assertEqual(self.A.downtime("WELL-9001", start="2026-03-10", end="2026-03-15")["data"]["total_days"], 0)

    def test_ranking_orders_by_days_and_resolves_area_names_and_ids(self):
        for scope in ("Gamma Block 9", "G-09", "gamma 9", "block 9"):
            r = self.A.downtime_ranking(scope, start="2026-01-01", end="2026-03-15", top_n=3)
            self.assertEqual([(x["asset_id"], x["days"]) for x in r["data"]["ranking"]], [("WELL-9002", 63), ("WELL-9001", 35)], scope)

    def test_well_type_filter(self):
        r = self.A.downtime_ranking("the whole field", start="2026-01-01", end="2026-03-15", well_type="T200")
        self.assertEqual({x["asset_id"] for x in r["data"]["ranking"]}, {"WELL-9001", "WELL-9003"})

    def test_status_cites_the_rule_and_explains_the_stop_with_a_note(self):
        r = self.A.well_status("WELL-9001")
        self.assertIs(r["data"]["producing"], False)
        ids = {c["id"] for c in r["citations"]}
        self.assertTrue({"INS-9001-0009", "T200#9.3", "CTX-9001-002"} <= ids)
        self.assertTrue(r["data"]["recorded_status_stale"])
        self.assertTrue(any("planned workover" in f["text"] for f in r["facts"]))

    def test_unknown_things_raise_clear_errors(self):
        for call in (lambda: self.A.well_status("WELL-0000"), lambda: self.A.downtime("No Such Block", "2026"), lambda: self.A.downtime("WELL-9001", "whenever")):
            with self.assertRaises(ToolError):
                call()

    def test_nothing_explains_a_stop_is_said_not_invented(self):
        r = self.A.wells_not_producing("Gamma Block 9")
        by = {row[0]: row[3] for row in r["visuals"]["table"]["rows"]}
        self.assertIn("planned workover", by["WELL-9001"])
        self.assertTrue(by["WELL-9002"].startswith("No recorded reason"))
        self.assertTrue(any(f["type"] == "missing_evidence" for f in r["flags"]))


class SpillTests(FixtureCase):
    def test_corrected_detection_is_not_counted_but_is_reported(self):
        r = self.A.spills("WELL-9001", start="2026-01-01", end="2026-03-15")
        self.assertEqual((r["data"]["count"], r["data"]["total_bbl"], r["data"]["excluded"]), (2, 3.5, ["INS-9001-0005"]))
        self.assertTrue(any("CTX-9001-001" in f["text"] for f in r["facts"]))
        self.assertIn("CTX-9001-001", {c["id"] for c in r["citations"]})

    def test_heatmap_by_area_and_month(self):
        r = self.A.spill_heatmap(start="2026-01-01", end="2026-03-15")
        self.assertEqual(r["data"]["matrix"]["Gamma Block 9"], [1, 0, 1])
        self.assertEqual(r["data"]["totals"]["Delta Block 4"], 0)


class RepairAndRuleTests(FixtureCase):
    def test_costs_belong_to_the_period_of_their_start_date(self):
        r = self.A.repair_costs(["WELL-9001"], "2026")
        self.assertEqual(r["data"]["per_well"], {"WELL-9001": 5100})

    def test_rca_uses_the_manual_threshold(self):
        self.assertEqual(self.A.rca_candidates("the whole field")["data"]["wells"], ["WELL-9001"])

    def test_type_scoped_rule_applies_only_to_its_type_and_is_attributed(self):
        self.store.add_scoped_rule(scope_type="well_type", scope_value="T350", key="rca_corrective_count", value=2, unit="repairs", reason="team policy",
                                   author_user_id="U-1", equipment_kind="pump_jack")
        r = Analyst(self.conn, self.rules, self.store, ahc_fixture.AS_OF).rca_candidates("the whole field")
        self.assertEqual(r["data"]["wells"], ["WELL-9001", "WELL-9002"])
        text = " ".join(f["text"] for f in r["facts"])
        self.assertIn("Alice Test", text)
        self.assertIn("not the manual", text)
        # A T200 well with 2 repairs would not be added: the rule is scoped to T350 only.
        self.assertEqual(self.A.rca_rule(self.A.wells["WELL-9003"], "pump_jack")["kind"], "manual")


class CorrectionTests(FixtureCase):
    def correct(self, new=40.0, author="U-1", reason="Faulty thermal gun, re-measured"):
        i = self.A.get_inspection("INS-9001-0003")
        return self.store.add_correction(target_id="INS-9001-0003", asset_id="WELL-9001", field="wellhead_temp_c", original=i["orig"]["wellhead_temp_c"],
                                         previous=i["wellhead_temp_c"], new=new, reason=reason, author_user_id=author)

    def test_correction_keeps_the_original_and_records_who_why_when_scope(self):
        c = self.correct()
        self.assertEqual((c["original_value"], c["new_value"], c["author_user_id"], c["reason"], c["scope_type"], c["status"]), (25.0, 40.0, "U-1", "Faulty thermal gun, re-measured", "record", "active"))
        self.assertTrue(c["created_at"] and c["correction_id"].startswith("COR-"))
        i = Analyst(self.conn, self.rules, self.store, ahc_fixture.AS_OF).get_inspection("INS-9001-0003")
        self.assertEqual((i["wellhead_temp_c"], i["orig"]["wellhead_temp_c"], i["producing"]), (40.0, 25.0, True))

    def test_correction_changes_later_calculations_for_everyone(self):
        before = self.A.downtime("WELL-9001", start="2026-01-01", end="2026-03-15")["data"]["total_days"]
        self.correct()
        later = Analyst(self.conn, self.rules, self.store, ahc_fixture.AS_OF)  # a new request, possibly a different user
        r = later.downtime("WELL-9001", start="2026-01-01", end="2026-03-15")
        self.assertEqual((before, r["data"]["total_days"]), (35, 28))
        self.assertIn("COR-0001", {c["id"] for c in later.downtime_ranking("Gamma Block 9", start="2026-01-01", end="2026-03-15")["citations"]} | {c["id"] for c in r["citations"]})

    def test_correction_applies_only_to_its_record(self):
        self.correct()
        later = Analyst(self.conn, self.rules, self.store, ahc_fixture.AS_OF)
        self.assertEqual(later.get_inspection("INS-9001-0004")["wellhead_temp_c"], 25.0)
        self.assertEqual(later.get_inspection("INS-9002-0003")["wellhead_temp_c"], 38.0)

    def test_a_second_correction_supersedes_but_history_and_original_are_kept(self):
        self.correct(new=40.0)
        c2 = self.correct(new=41.0, author="U-3")
        self.assertEqual((c2["original_value"], c2["supersedes_id"]), (25.0, "COR-0001"))
        history = self.store.corrections_for("INS-9001-0003")
        self.assertEqual([h["status"] for h in history], ["superseded", "active"])
        self.assertEqual(Analyst(self.conn, self.rules, self.store, ahc_fixture.AS_OF).get_inspection("INS-9001-0003")["wellhead_temp_c"], 41.0)

    def test_corrected_values_are_flagged_in_answers(self):
        self.correct()
        r = Analyst(self.conn, self.rules, self.store, ahc_fixture.AS_OF).spills("WELL-9001", start="2026-01-01", end="2026-03-15")
        r2 = Analyst(self.conn, self.rules, self.store, ahc_fixture.AS_OF).inspection_series("WELL-9001", 9)
        self.assertTrue(any(f["type"] == "corrected" and "Alice Test" in f["text"] for f in r2["flags"]))
        self.assertTrue(r["data"]["count"] == 2)


class BroaderQuestionTests(FixtureCase):
    def test_repairs_total_and_ranking_by_cost(self):
        r = self.A.repairs("Gamma Block 9", start="2026-01-01", end="2026-03-15", top_n=2)
        self.assertEqual((r["data"]["count"], r["data"]["total_usd"]), (4, 5100 + 800))
        self.assertEqual([row[0] for row in r["visuals"]["table"]["rows"]], ["MNT-9001-003", "MNT-9001-002"])
        self.assertEqual(r["data"]["by_equipment"], {"pump_jack": 5900.0})

    def test_repairs_filter_by_type_and_equipment(self):
        r = self.A.repairs("the whole field", start="2026-01-01", end="2026-03-15", equipment_kind="flowline", maintenance_type="corrective")
        self.assertEqual((r["data"]["count"], r["data"]["total_usd"]), (1, 400))

    def test_inspection_gaps_use_the_sop_limit_and_can_be_tightened(self):
        self.assertEqual(self.A.inspection_gaps("the whole field", start="2026-01-01", end="2026-03-15")["data"]["wells"], [])
        tight = self.A.inspection_gaps("the whole field", start="2026-01-01", end="2026-03-15", max_days=10)
        self.assertEqual(tight["data"]["wells"], ["WELL-9001", "WELL-9002", "WELL-9003"])  # the missed week left a 14-day gap on every well

    def test_long_downtime_runs_longer_than_the_reporting_limit(self):
        r = self.A.long_downtime("the whole field", start="2026-01-01", end="2026-03-15")
        self.assertEqual(r["data"]["wells"], ["WELL-9002"])          # 9 weekly inspections in a row = 63 days
        self.assertEqual(r["visuals"]["table"]["rows"][0][1], 63)
        self.assertEqual(self.A.long_downtime("the whole field", start="2026-01-01", end="2026-03-15", min_days=13)["data"]["wells"], ["WELL-9001", "WELL-9002"])

    def test_downtime_and_repair_cost_can_be_compared_by_area_and_by_well_type(self):
        r = self.A.downtime("the whole field", start="2026-01-01", end="2026-03-15", group_by="area")
        self.assertEqual(r["data"]["by_group"], {"Gamma Block 9": 98, "Delta Block 4": 0})
        self.assertEqual(r["natural"], "bar")
        self.assertEqual(r["visuals"]["table"]["rows"][0], ["Gamma Block 9", 98, 2, 49.0])
        t = self.A.downtime("the whole field", start="2026-01-01", end="2026-03-15", group_by="well_type")
        self.assertEqual(t["data"]["by_group"], {"T350": 63, "T200": 35})
        c = self.A.repair_costs(scope="the whole field", period="2026", group_by="area")
        self.assertEqual(c["data"]["by_group"], {"Gamma Block 9": 5900, "Delta Block 4": 400})
        self.assertEqual(c["data"]["total_usd"], 6300)

    def test_regulatory_events_empty_case(self):
        r = self.A.regulatory_events("the whole field", "2026")
        self.assertEqual((r["data"]["count"], r["data"]["fines_usd"]), (0, 0))

    def test_an_area_missing_from_areas_json_still_works(self):
        a = Analyst(self.conn, self.rules, self.store, ahc_fixture.AS_OF)
        a.wells["WELL-9003"]["area_id"] = "X-99"
        a.areas.pop("X-99", None)
        for w in a.wells.values():
            if w["area_id"] and w["area_id"] not in a.areas:
                a.areas[w["area_id"]] = {"area_id": w["area_id"], "name": w["area_id"], "team_id": None, "lat": None, "lon": None}
        self.assertEqual(a.spill_heatmap(start="2026-01-01", end="2026-03-15")["data"]["totals"].get("X-99"), 0)

    def test_later_dataset_roots_report_the_records_they_replace(self):
        out = Path(self._tmp.name) / "overlap.sqlite3"
        stats = ingest.ingest([self.root, self.root], out)
        self.assertEqual(stats["overwritten"]["inspections"], 27)
        self.assertTrue(any("replaced" in i for i in stats["issues"]))


class PeriodTests(unittest.TestCase):
    def test_relative_windows_end_on_the_as_of_date(self):
        a = date(2026, 10, 16)
        cases = {"last 4 months": ("2026-06-16", "2026-10-16"), "last 90 days": ("2026-07-18", "2026-10-16"), "2025": ("2025-01-01", "2025-12-31"),
                 "this year": ("2026-01-01", "2026-10-16"), "last 12 months": ("2025-10-16", "2026-10-16")}
        for text, (s, e) in cases.items():
            p = periods.resolve_period(text, a)
            self.assertEqual((p.start.isoformat(), p.end.isoformat()), (s, e), text)

    def test_more_phrases_and_their_stated_conventions(self):
        a = date(2026, 10, 16)
        cases = {"the past year": ("2025-10-16", "2026-10-16"), "past quarter": ("2026-07-16", "2026-10-16"), "last quarter": ("2026-07-01", "2026-09-30"), "this quarter": ("2026-10-01", "2026-10-16"),
                 "Q2": ("2026-04-01", "2026-06-30"), "q3 2025": ("2025-07-01", "2025-09-30"), "since March": ("2026-03-01", "2026-10-16"), "last year": ("2025-01-01", "2025-12-31"),
                 "last month": ("2026-09-01", "2026-09-30"), "yesterday": ("2026-10-15", "2026-10-15"), "last 2 weeks": ("2026-10-02", "2026-10-16")}
        for text, (s, e) in cases.items():
            p = periods.resolve_period(text, a)
            self.assertEqual((p.start.isoformat(), p.end.isoformat()), (s, e), text)
        self.assertIn("calendar", periods.resolve_period("last year", a).assumption)

    def test_month_end_is_clamped(self):
        self.assertEqual(periods.add_months(date(2026, 3, 31), -1), date(2026, 2, 28))

    def test_explicit_dates_win(self):
        p = periods.resolve_period("last 4 months", date(2026, 10, 16), start="2026-01-01", end="2026-01-31")
        self.assertEqual((p.start, p.end), (date(2026, 1, 1), date(2026, 1, 31)))


if __name__ == "__main__":
    unittest.main()
