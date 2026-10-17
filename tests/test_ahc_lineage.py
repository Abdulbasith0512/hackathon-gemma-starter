"""Data lineage for the heatmap, and verification of what the model is allowed to say about it.

The displayed numbers are checked against evidence that does not come from the code that produced
them: a recount straight from the raw table and the source files at the cited lines.
"""

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from ahc import config
from ahc.agent import Agent, ground_check
from ahc.server import create_app
from tests import ahc_fixture
from tests.test_ahc_agent import ALICE, AgentCase, ScriptedLLM
from tests.test_ahc_core import FixtureCase
from tests.test_ahc_golden import GoldenCase

WINDOW = {"start": "2026-01-01", "end": "2026-03-15"}


def source_line(root: Path, source: str) -> dict:
    """Read the record at 'assets/<well>/inspections.jsonl:<line>' from the dataset folder itself."""
    path, line = source.rsplit(":", 1)
    return json.loads((root / path).read_text(encoding="utf-8").splitlines()[int(line) - 1])


class HeatmapLineageTests(FixtureCase):
    def heat(self, **kw):
        return self.A.spill_heatmap(**{**WINDOW, **kw})

    def test_totals_reconcile_with_the_cells_and_with_a_raw_recount(self):
        r = self.heat()
        L = r["visuals"]["heatmap"]["lineage"]
        cells = r["visuals"]["heatmap"]["cells"]
        values = r["visuals"]["heatmap"]["values"]
        flat_ids = [i for row in cells for cell in row for i in cell]
        self.assertEqual(L["grand_total"], sum(L["row_totals"]), "grand total is the sum of the area totals")
        self.assertEqual(L["grand_total"], sum(L["col_totals"]), "...and of the month totals")
        self.assertEqual(L["grand_total"], len(flat_ids))
        self.assertEqual(len(flat_ids), len(set(flat_ids)), "no record is counted twice")
        self.assertEqual([[len(c) for c in row] for row in cells], values, "every number is exactly the records listed under it")
        raw = self.conn.execute("SELECT COUNT(*) FROM inspections WHERE spill_detected=1 AND inspected_date>=? AND inspected_date<=?", (WINDOW["start"], WINDOW["end"])).fetchone()[0]
        self.assertEqual(raw, L["grand_total"] + L["excluded_total"], "counted + excluded = every detection in the raw table for the window")
        self.assertEqual(r["data"]["grand_total"], L["grand_total"])
        self.assertIn(f"Total across all areas: {L['grand_total']} spills", " ".join(f["text"] for f in r["facts"]))

    def test_each_listed_record_is_in_the_right_cell_and_exists_in_its_source_file(self):
        r = self.heat()
        h = r["visuals"]["heatmap"]
        for i, area in enumerate(h["rows"]):
            for j, col in enumerate(h["cols"]):
                rows = self.A.lineage_rows(h["cells"][i][j])
                self.assertEqual(len(rows), len(h["cells"][i][j]))
                for row in rows:
                    self.assertEqual(row["area"], area)
                    self.assertEqual(int(row["inspected_at"][5:7]), j + 1)            # Jan, Feb, Mar
                    self.assertTrue(row["counted_as_spill"] and row["dataset_flag"])
                    self.assertRegex(row["source"], r"^assets/WELL-\d+/inspections\.jsonl:\d+$")
                    raw = source_line(self.root, row["source"])                    # the cited file and line really hold this record
                    self.assertEqual((raw["inspection_id"], raw["spill_est_volume_bbl"], raw["inspected_at"]), (row["inspection_id"], row["volume_bbl"], row["inspected_at"]))

    def test_excluded_detections_are_listed_in_their_cell_with_the_reason_and_the_note_that_corrected_them(self):
        h = self.heat()["visuals"]["heatmap"]
        L = h["lineage"]
        gi = h["rows"].index("Gamma Block 9")
        feb = [e for e in L["excluded_cells"][gi][1]]
        self.assertEqual([e["inspection_id"] for e in feb], ["INS-9001-0005"])
        self.assertIn("CTX-9001-001", feb[0]["refs"])
        self.assertIn("Not a crude spill", feb[0]["reason"])
        self.assertEqual(h["values"][gi][1], 0)                                   # not counted...
        row = self.A.lineage_rows(["INS-9001-0005"])[0]
        self.assertEqual((row["dataset_flag"], row["counted_as_spill"]), (True, False))   # ...though the dataset flagged it
        self.assertEqual(row["dataset_correction_note"]["note_id"], "CTX-9001-001")
        self.assertEqual(row["dataset_correction_note"]["source"], "assets/WELL-9001/context.jsonl:1")
        note_file = (self.root / "assets/WELL-9001/context.jsonl").read_text(encoding="utf-8").splitlines()[0]
        self.assertEqual(json.loads(note_file)["note_id"], "CTX-9001-001")

    def test_filters_and_the_calculation_are_stated(self):
        r = self.heat()
        L = r["visuals"]["heatmap"]["lineage"]
        filters = dict(L["filters"])
        self.assertIn("1 Jan 2026 to 15 Mar 2026", filters["Period"])
        self.assertEqual(filters["Scope"], "the whole field")
        self.assertEqual(filters["As-of date"], "2026-03-15")
        self.assertIn("correction", filters["Counted as a spill"])
        self.assertIn("sum of the area totals", L["calculation"])
        self.assertIn("inspections", L["source_table"])

    def test_a_correction_that_removes_a_spill_changes_the_cell_the_totals_and_the_exclusions(self):
        before = self.heat()["visuals"]["heatmap"]["lineage"]["grand_total"]
        self.store.add_correction(target_id="INS-9001-0002", asset_id="WELL-9001", field="spill_detected", original=True, previous=True, new=False,
                                  reason="Crew confirmed it was rainwater", author_user_id="U-1")
        later = Analyst_for(self)
        r = later.spill_heatmap(**WINDOW)
        h = r["visuals"]["heatmap"]
        self.assertEqual(h["lineage"]["grand_total"], before - 1)
        self.assertNotIn("INS-9001-0002", [i for row in h["cells"] for c in row for i in c])
        gi = h["rows"].index("Gamma Block 9")
        jan = h["lineage"]["excluded_cells"][gi][0]
        self.assertEqual([e["inspection_id"] for e in jan], ["INS-9001-0002"])
        self.assertTrue(any(ref.startswith("COR-") for ref in jan[0]["refs"]))
        self.assertIn("Alice Test", jan[0]["reason"])
        raw = self.conn.execute("SELECT COUNT(*) FROM inspections WHERE spill_detected=1 AND inspected_date>=? AND inspected_date<=?", (WINDOW["start"], WINDOW["end"])).fetchone()[0]
        self.assertEqual(raw, h["lineage"]["grand_total"] + h["lineage"]["excluded_total"])

    def test_a_volume_correction_is_shown_beside_the_original_in_the_lineage_rows(self):
        self.store.add_correction(target_id="INS-9001-0008", asset_id="WELL-9001", field="spill_est_volume_bbl", original=1.5, previous=1.5, new=5.4, reason="measured", author_user_id="U-1")
        row = Analyst_for(self).lineage_rows(["INS-9001-0008"])[0]
        self.assertEqual((row["volume_bbl"], row["original_volume_bbl"], row["counted_as_spill"]), (5.4, 1.5, True))
        self.assertEqual([(c["id"], c["field"], c["original"], c["new"], c["by"]) for c in row["corrections"]], [("COR-0001", "spill_est_volume_bbl", 1.5, 5.4, "Alice Test")])

    def test_unknown_ids_are_not_invented(self):
        self.assertEqual(self.A.lineage_rows(["INS-0000-0000", ""]), [])
        self.assertEqual(self.A.lineage_rows([]), [])


def Analyst_for(case):
    from ahc.analyst import Analyst
    return Analyst(case.conn, case.rules, case.store, ahc_fixture.AS_OF)


class HeatmapLineageSampleTests(GoldenCase):
    def test_the_141_total_is_computed_and_reconciles_with_the_raw_table_and_the_source_files(self):
        r = self.A.spill_heatmap("2026")
        h = r["visuals"]["heatmap"]
        L = h["lineage"]
        self.assertEqual((L["grand_total"], L["excluded_total"]), (141, 17))
        self.assertEqual(sum(L["row_totals"]), 141)
        self.assertEqual(dict(zip(h["rows"], L["row_totals"])), {"Northeast Block 7": 37, "Northeast Block 8": 26, "Southwest Block 23": 35, "Southwest Block 24": 43})
        raw = self.conn.execute("SELECT COUNT(*) FROM inspections WHERE spill_detected=1 AND inspected_date>='2026-01-01' AND inspected_date<='2026-10-16'").fetchone()[0]
        self.assertEqual(raw, 141 + 17)
        rows = self.A.lineage_rows([i for row in h["cells"] for c in row for i in c])
        self.assertEqual(len(rows), 141)
        for row in rows:
            raw_rec = source_line(config.DATA_DIR / "sample-data", row["source"])
            self.assertEqual(raw_rec["inspection_id"], row["inspection_id"])
            self.assertTrue(row["counted_as_spill"])
        ex = [e for row in L["excluded_cells"] for cell in row for e in cell]
        self.assertEqual(len(ex), 17)
        self.assertTrue(all(e["refs"] and e["refs"][0].startswith("CTX-") for e in ex))   # every exclusion cites the note that corrected it

    def test_the_total_the_model_used_to_add_up_itself_is_now_part_of_the_evidence(self):
        r = self.A.spill_heatmap("2026")
        q = "Show a heatmap of 2026 spills by geographic area and month."
        self.assertEqual(ground_check("There were 141 spills in 2026 across the four areas.", [r], q), [])
        self.assertEqual(ground_check("There were one hundred forty-one spills.", [r], q), [])
        self.assertEqual(ground_check("There were 142 spills.", [r], q), ["142"])
        self.assertEqual(ground_check("There were one hundred forty-two spills.", [r], q), ["one hundred forty-two"])
        self.assertEqual(ground_check("141 spills [INS-9999-0001]", [r], q), ["INS-9999-0001"])


class UnsupportedClaimsCannotBypassVerificationTests(AgentCase):
    ARGS = dict(WINDOW)

    def ask(self, wording):
        out = self.agent(("call", "spill_heatmap", self.ARGS), ("text", wording)).respond(ALICE, None, "Show a heatmap of spills by area and month.")
        return out

    def test_a_correct_total_stated_by_the_model_is_accepted(self):
        out = self.ask("There were 2 spills in total.")
        self.assertEqual((out["answer_source"], out["warnings"]), ("model", []))

    def test_wrong_totals_in_digits_or_words_are_replaced_by_the_verified_facts(self):
        for claim, shown in (("There were 150 spills in total.", "150"), ("There were one hundred fifty spills.", "one hundred fifty"), ("There were forty-one spills.", "forty-one")):
            out = self.ask(claim)
            self.assertEqual(out["answer_source"], "verified facts", claim)
            self.assertIn(shown, out["warnings"][0], claim)
            self.assertNotIn(shown, out["answer"], "the rejected claim is never displayed")
            self.assertIn("Total across all areas: 2 spills", out["answer"])

    def test_an_invented_record_is_replaced_by_the_verified_facts(self):
        out = self.ask("The 2 spills include INS-9999-0001.")
        self.assertEqual(out["answer_source"], "verified facts")
        self.assertIn("INS-9999-0001", out["warnings"][0])
        self.assertNotIn("INS-9999-0001", out["answer"])

    def test_what_the_page_draws_matches_the_evidence_whatever_the_model_says(self):
        out = self.ask("There were 999 spills.")                                   # a rejected wording must not change the drawing
        spec = out["blocks"][0]["visual"]["spec"]
        self.assertEqual(spec["lineage"]["grand_total"], sum(sum(row) for row in spec["values"]))
        self.assertEqual(spec["lineage"]["grand_total"], 2)
        self.assertEqual([[len(c) for c in row] for row in spec["cells"]], spec["values"])


class LineageApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = ahc_fixture.build(Path(cls._tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def client(self):
        app = create_app([self.root], Path(self._tmp.name) / "api.sqlite3", Path(self._tmp.name) / f"mem-{id(self)}.sqlite3", ahc_fixture.AS_OF, ScriptedLLM())
        self.addCleanup(app.state.rt.store.close)
        return TestClient(app), app

    def test_lineage_endpoint_returns_source_records_and_reports_unknown_ids(self):
        c, _ = self.client()
        out = c.get("/api/lineage/inspections", params={"ids": "INS-9001-0002,INS-9001-0005,INS-0000-0000"}).json()
        by = {r["inspection_id"]: r for r in out["rows"]}
        self.assertEqual(sorted(by), ["INS-9001-0002", "INS-9001-0005"])
        self.assertEqual(out["missing"], ["INS-0000-0000"])
        self.assertTrue(by["INS-9001-0002"]["counted_as_spill"])
        self.assertFalse(by["INS-9001-0005"]["counted_as_spill"])
        self.assertEqual(by["INS-9001-0005"]["dataset_correction_note"]["note_id"], "CTX-9001-001")
        self.assertEqual(source_line(self.root, by["INS-9001-0002"]["source"])["inspection_id"], "INS-9001-0002")

    def test_bad_requests_are_refused(self):
        c, _ = self.client()
        self.assertEqual(c.get("/api/lineage/inspections", params={"ids": " , "}).status_code, 400)
        self.assertEqual(c.get("/api/lineage/inspections", params={"ids": ",".join(f"INS-{n}" for n in range(501))}).status_code, 400)
        self.assertEqual(c.get("/api/lineage/inspections").status_code, 422)


if __name__ == "__main__":
    unittest.main()
