"""SQLite schema for the dataset database (rebuildable from the dataset folders).

Every record keeps `raw` (the original JSON) and where it came from, so the evidence
panel can show the exact source record.
"""

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE areas (area_id TEXT PRIMARY KEY, name TEXT, team_id TEXT, lat REAL, lon REAL, raw TEXT);
CREATE TABLE teams (team_id TEXT PRIMARY KEY, name TEXT, lead_user_id TEXT);
CREATE TABLE users (user_id TEXT PRIMARY KEY, name TEXT, role TEXT, team_id TEXT);

CREATE TABLE wells (
  asset_id TEXT PRIMARY KEY, name TEXT, well_type TEXT, area_id TEXT, team_id TEXT,
  in_charge_user_id TEXT, lat REAL, lon REAL, installed_on TEXT, recorded_status TEXT,
  last_inspection_id TEXT, raw TEXT, source TEXT
);
CREATE INDEX idx_wells_area ON wells(area_id);
CREATE INDEX idx_wells_type ON wells(well_type);

CREATE TABLE inspections (
  inspection_id TEXT PRIMARY KEY, asset_id TEXT, inspected_at TEXT, inspected_date TEXT,
  inspector_user_id TEXT, method TEXT, ambient_temp_c REAL, wellhead_temp_c REAL,
  spill_detected INTEGER, spill_area_pct REAL, spill_est_volume_bbl REAL, notes TEXT,
  raw TEXT, source TEXT
);
CREATE INDEX idx_ins_asset ON inspections(asset_id, inspected_at);
CREATE INDEX idx_ins_date ON inspections(inspected_date);
CREATE INDEX idx_ins_spill ON inspections(spill_detected, inspected_date);

CREATE TABLE maintenance (
  maintenance_id TEXT PRIMARY KEY, asset_id TEXT, started_at TEXT, completed_at TEXT,
  started_date TEXT, completed_date TEXT, maintenance_type TEXT, equipment_kind TEXT,
  issue TEXT, action_taken TEXT, technician_user_id TEXT, contractor TEXT,
  downtime_hours REAL, cost_labor REAL, cost_parts REAL, cost_total REAL,
  triggered_by_inspection_id TEXT, report_file TEXT, raw TEXT, source TEXT
);
CREATE INDEX idx_mnt_asset ON maintenance(asset_id, started_date);
CREATE INDEX idx_mnt_trigger ON maintenance(triggered_by_inspection_id);

CREATE TABLE regulatory_events (
  event_id TEXT PRIMARY KEY, asset_id TEXT, date TEXT, agency TEXT, event_type TEXT,
  protocol_id TEXT, related_inspection_id TEXT, hours_to_report REAL, detail TEXT,
  fine_usd REAL, status TEXT, raw TEXT, source TEXT
);
CREATE INDEX idx_reg_asset ON regulatory_events(asset_id, date);
CREATE INDEX idx_reg_ins ON regulatory_events(related_inspection_id);

CREATE TABLE notes (
  note_id TEXT PRIMARY KEY, asset_id TEXT, created_at TEXT, author_user_id TEXT,
  note_type TEXT, inspection_id TEXT, text TEXT, valid_from TEXT, valid_to TEXT,
  raw TEXT, source TEXT
);
CREATE INDEX idx_notes_asset ON notes(asset_id, created_at);
CREATE INDEX idx_notes_ins ON notes(inspection_id);

-- Manuals, SOPs and maintenance reports, split into citable sections.
CREATE TABLE documents (
  doc_id TEXT PRIMARY KEY, kind TEXT, title TEXT, well_type TEXT, asset_id TEXT,
  maintenance_id TEXT, path TEXT, text TEXT
);
CREATE TABLE sections (
  rowid INTEGER PRIMARY KEY, doc_id TEXT, ord INTEGER, section_id TEXT, heading TEXT, text TEXT
);
CREATE INDEX idx_sections_doc ON sections(doc_id, section_id);
CREATE VIRTUAL TABLE sections_fts USING fts5(heading, text, content='sections', content_rowid='rowid');

-- Facts parsed (deterministically) from repair reports.
CREATE TABLE report_facts (
  maintenance_id TEXT PRIMARY KEY, containment_hours REAL, containment_quote TEXT,
  spill_class TEXT, action_required INTEGER
);
CREATE TABLE report_compliance (
  maintenance_id TEXT, protocol_id TEXT, result TEXT, detail TEXT
);
CREATE INDEX idx_rc_mnt ON report_compliance(maintenance_id);
"""


def connect(path: Path | str, *, readonly: bool = False) -> sqlite3.Connection:
    uri = f"file:{Path(path).as_posix()}?mode=ro" if readonly else str(path)
    conn = sqlite3.connect(uri, uri=readonly, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
