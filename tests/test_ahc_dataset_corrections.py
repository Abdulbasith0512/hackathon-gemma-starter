"""Corrections written into the dataset itself (context.jsonl note_type 'data_correction'): inspection, field, original and corrected value.

They act like saved corrections: every tool reads the corrected value, the dataset's original stays visible, and a correction a user saves in
the app still wins over the dataset's.
"""

import json
import tempfile
import unittest
from pathlib import Path

from ahc import db, ingest, rules
from ahc.analyst import Analyst
from ahc.store import Store
from tests import ahc_fixture

INS = "INS-9002-0001"        # WELL-9002 (T350, limit 20): 18 degrees above air, so not producing as recorded


class DatasetCorrectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        base = Path(cls._tmp.name)
        root = cls.root = ahc_fixture.build(base)
        rec = next(json.loads(l) for l in (root / "assets/WELL-9002/inspections.jsonl").read_text(encoding="utf-8").splitlines() if json.loads(l)["inspection_id"] == INS)
        cls.original, cls.ambient = rec["wellhead_temp_c"], rec["ambient_temp_c"]
        cls.corrected = round(cls.ambient + 25.0, 1)
        note = {"note_id": "CTX-9002-001", "asset_id": "WELL-9002", "created_at": "2026-03-01T09:00:00Z", "author_user_id": "U-1", "note_type": "data_correction",
                "inspection_id": INS, "field": "wellhead_temp_c", "original_value": cls.original, "corrected_value": cls.corrected,
                "text": f"Inspection {INS}: wellhead_temp_c corrected from {cls.original} to {cls.corrected}. Thermal camera pointed at the shaded side.",
                "valid_from": "2026-03-01", "valid_to": None}
        with open(root / "assets/WELL-9002/context.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(note) + "\n")
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

    def test_the_corrected_value_is_the_effective_value_and_the_original_is_kept(self):
        i = self.A.get_inspection(INS)
        self.assertEqual(i["wellhead_temp_c"], self.corrected)
        self.assertEqual(i["orig"]["wellhead_temp_c"], self.original)
        self.assertTrue(i["producing"])                       # 25 above air against a 20 limit; recorded it was 18
        self.assertEqual(i["orig_delta"], 18.0)
        self.assertEqual([(c["correction_id"], c["field"], c["new_value"]) for c in i["corrections"]], [("CTX-9002-001", "wellhead_temp_c", self.corrected)])

    def test_it_changes_what_the_tools_report(self):
        """Downtime is 7 days per weekly inspection found not producing; a raw recount of the file, with the one corrected reading swapped in, must agree."""
        rows = [json.loads(l) for l in (self.root / "assets/WELL-9002/inspections.jsonl").read_text(encoding="utf-8").splitlines()]
        down = [r["inspection_id"] for r in rows if r["inspected_at"][:10] <= ahc_fixture.AS_OF.isoformat() and r["wellhead_temp_c"] - r["ambient_temp_c"] < 20 - 1e-9]
        self.assertIn(INS, down, "recorded, the inspection was below the limit")
        r = self.A.downtime("WELL-9002", start="2025-01-01", end=ahc_fixture.AS_OF.isoformat())
        self.assertEqual(r["data"]["total_days"], 7 * (len(down) - 1))
        self.assertNotIn(INS, {c["id"] for c in r["citations"]})

    def test_the_lineage_shows_the_dataset_correction(self):
        row = self.A.lineage_rows([INS])[0]
        self.assertEqual([(c["id"], c["original"], c["new"]) for c in row["corrections"]], [("CTX-9002-001", self.original, self.corrected)])

    def test_a_correction_saved_in_the_app_wins_over_the_datasets(self):
        self.store.add_correction(target_id=INS, asset_id="WELL-9002", field="wellhead_temp_c", original=self.original, previous=self.corrected, new=self.ambient + 5,
                                  reason="re-measured", author_user_id="U-2")
        i = Analyst(self.conn, self.rules, self.store, ahc_fixture.AS_OF).get_inspection(INS)
        self.assertEqual(i["wellhead_temp_c"], self.ambient + 5)
        self.assertEqual(i["orig"]["wellhead_temp_c"], self.original)
        self.assertEqual(len(i["corrections"]), 1)


if __name__ == "__main__":
    unittest.main()
