"""A tiny synthetic dataset in the official format, with IDs and names that appear nowhere in the
sample. If the code only worked on sample IDs these tests would fail.

AS_OF is 2026-03-15. Wells:
  WELL-9001  T200  Gamma Block 9   weekly Mondays; 5 non-producing weeks; one missed week; one corrected spill
  WELL-9002  T350  Gamma Block 9   deltas 18 (below its 20 limit, but above T200's 15)
  WELL-9003  T200  Delta Block 4   always producing
"""

import json
from datetime import date, timedelta
from pathlib import Path

AS_OF = date(2026, 3, 15)

MANUAL_T200 = """# T200 test manual

## 9. Engineering limits

### 9.3 Production temperature rule
A T200 well is considered **producing (active)** when its wellhead temperature is
at least **15 °C above** ambient air temperature at the time of the reading.

## 10. Maintenance escalation

- Three or more **corrective** maintenance events on the same equipment kind in the
  12 months before the current date require a root-cause analysis (RCA).
- Downtime of more than 14 consecutive days must be reported to the area production supervisor.
"""

MANUAL_T350 = """# T350 test manual

Procedures not listed here follow the T200 manual.

## 3. Production temperature rule
A T350 well is considered **producing (active)** only when its wellhead temperature is at least **20 °C above
ambient** air temperature at the time of the reading.

## 6. Maintenance escalation
Same as T200 section 10 (RCA after three corrective events on the same equipment kind within 12 months).
"""

SPILL_SOP = """# Spill Response SOP

## 3. Spill classes

| Class | Estimated crude volume | Notes |
|---|---|---|
| Minor | below 1 bbl | Record |
| Moderate | 1 bbl to below 5 bbl | Notify |
| Reportable | 5 bbl to below 25 bbl | Report |
| Major | 25 bbl or more | Report in 2 h |

## 4. Protocols

| Protocol ID | Requirement |
|---|---|
| **SR-01** | File the written notice within **24 hours** of discovery, or within **2 hours** for a major spill. |
| **SR-02** | Contain the spill within **4 hours** of discovery. |
| **SR-03** | Clean soil to **1.0% TPH or less**. Take **at least 4 soil samples**. Verify within 60 days of discovery. |
"""

COMPLIANCE_SOP = """# Regulatory Compliance SOP

## 2. Protocols

| Protocol ID | Requirement | Evidence in the data |
|---|---|---|
| **RC-01** | Inspect at least once every **14 days**. | inspections |
| **RC-02** | Flowline integrity test once per calendar year. | maintenance |
| **RC-03** | Any well down for more than **14 consecutive days** must be reported. | inspections |
| **RC-04** | Notices of violation must be answered within **30 days**. | regulatory events |
"""

# (date, wellhead delta above air, spill volume or None)
W9001 = [("2026-01-05", 20, None), ("2026-01-12", 20, 2.0), ("2026-01-19", 5, None), ("2026-01-26", 5, None),
         # 2026-02-02 inspection missed
         ("2026-02-09", 20, 6.0), ("2026-02-16", 14.9, None), ("2026-02-23", 15.0, None), ("2026-03-02", 3, 1.5), ("2026-03-09", 3, None)]


def _w(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")


def _jsonl(path: Path, rows: list[dict]) -> None:
    _w(path, "\n".join(json.dumps(r) for r in rows) + ("\n" if rows else ""))


def _inspections(well: str, series: list[tuple]) -> list[dict]:
    rows = []
    for n, (d, delta, spill) in enumerate(series, 1):
        amb = 45.1 if d == "2026-02-16" else 20.0  # a hot day: 60 degrees absolute but only 14.9 above air
        rows.append({"inspection_id": f"INS-{well[-4:]}-{n:04d}", "asset_id": well, "inspected_at": f"{d}T10:00:00Z", "inspector_user_id": "U-2",
                     "method": "drone", "ambient_temp_c": amb, "wellhead_temp_c": round(amb + delta, 1), "spill_detected": spill is not None,
                     "spill_area_pct": 2.0 if spill else None, "spill_est_volume_bbl": spill, "evidence_images": [], "notes": ""})
    return rows


def build(root: Path) -> Path:
    root = Path(root) / "sample-data"
    _w(root / "fleet/users.json", {"users": [
        {"user_id": "U-1", "name": "Alice Test", "role": "production_supervisor", "team_id": "TEAM-G"},
        {"user_id": "U-2", "name": "Bob Test", "role": "field_inspector", "team_id": "TEAM-G"},
        {"user_id": "U-3", "name": "Cara Test", "role": "field_operator", "team_id": "TEAM-D"}]})
    _w(root / "fleet/areas.json", {"areas": [
        {"area_id": "G-09", "name": "Gamma Block 9", "team_id": "TEAM-G", "center": {"lat": 30.0, "lon": -100.0}, "asset_ids": ["WELL-9001", "WELL-9002"]},
        {"area_id": "D-04", "name": "Delta Block 4", "team_id": "TEAM-D", "center": {"lat": 31.0, "lon": -101.0}, "asset_ids": ["WELL-9003"]}],
        "teams": [{"team_id": "TEAM-G", "name": "Gamma Production", "lead_user_id": "U-1"}, {"team_id": "TEAM-D", "name": "Delta Production", "lead_user_id": "U-3"}]})
    _w(root / "fleet/well-types/T200.md", MANUAL_T200)
    _w(root / "fleet/well-types/T350.md", MANUAL_T350)
    _w(root / "fleet/sops/spill-response-sop.md", SPILL_SOP)
    _w(root / "fleet/sops/regulatory-compliance-sop.md", COMPLIANCE_SOP)
    _w(root / "fleet/sops/field-work-sop.md", "# Field SOP\n\n## 1. Purpose\nCrew safety.\n")

    wells = {"WELL-9001": ("T200", "G-09", 30.01, -100.01), "WELL-9002": ("T350", "G-09", 30.02, -100.02), "WELL-9003": ("T200", "D-04", 31.01, -101.01)}
    for well, (wt, area, lat, lon) in wells.items():
        d = root / "assets" / well
        _w(d / "metadata.json", {"asset_id": well, "name": f"{area} {well[-3:]}", "asset_category": "oil_well", "well_type": wt, "area_id": area, "team_id": "TEAM-G",
                                 "in_charge_user_id": "U-1", "location": {"lat": lat, "lon": lon}, "installed_on": "2015-01-01", "equipment": [],
                                 "last_inspection": {}, "recorded_status": "active"})
    series = {"WELL-9001": W9001,
              "WELL-9002": [(d, 18, None) for d, _, _ in W9001],
              "WELL-9003": [(d, 30, None) for d, _, _ in W9001]}
    for well, s in series.items():
        _jsonl(root / "assets" / well / "inspections.jsonl", _inspections(well, s))

    def mnt(well, n, kind, equip, issue, started, cost, trig=None, report=None):
        return {"maintenance_id": f"MNT-{well[-4:]}-{n:03d}", "asset_id": well, "started_at": f"{started}T08:00:00Z", "completed_at": f"{started}T18:00:00Z",
                "maintenance_type": kind, "equipment_kind": equip, "issue": issue, "action_taken": "fixed", "technician_user_id": "U-2", "contractor": None,
                "downtime_hours": 999, "cost_usd": {"labor": cost // 2, "parts": cost - cost // 2, "total": cost}, "triggered_by_inspection_id": trig, "report_file": report}
    _jsonl(root / "assets/WELL-9001/maintenance.jsonl", [
        mnt("WELL-9001", 1, "corrective", "pump_jack", "Bearing wear", "2025-11-03", 1000),
        mnt("WELL-9001", 2, "corrective", "pump_jack", "Belt failure", "2026-01-20", 2000, trig="INS-9001-0003"),
        mnt("WELL-9001", 3, "corrective", "pump_jack", "Gearbox leak", "2026-02-24", 3000, trig="INS-9001-0008"),
        mnt("WELL-9001", 4, "scheduled", "pump_jack", "Lubrication", "2026-03-01", 100),
        mnt("WELL-9001", 5, "corrective", "pump_jack", "Old repair, out of the 12-month window", "2025-01-10", 500)])
    _jsonl(root / "assets/WELL-9002/maintenance.jsonl", [
        mnt("WELL-9002", 1, "corrective", "pump_jack", "Bearing wear", "2025-12-03", 700),
        mnt("WELL-9002", 2, "corrective", "pump_jack", "Belt failure", "2026-02-03", 800)])
    spill_report = "# Maintenance Report — MNT-9003-001\n\n## What happened\nThe release was contained about 6.5 hours after the inspection.\n\n## Compliance check\n\n| Protocol | Result | Detail |\n|---|---|---|\n| SR-02 | **Not met** | Contained about 6.5 hours after discovery (limit 4 hours) |\n| SR-04 | Met | Recorded (moderate class) |\n"
    _w(root / "assets/WELL-9003/maintenance-reports/odd-name-for-report.md", spill_report)
    _jsonl(root / "assets/WELL-9003/maintenance.jsonl", [mnt("WELL-9003", 1, "corrective", "flowline", "Leak", "2026-03-02", 400, trig="INS-9003-0008", report="maintenance-reports/odd-name-for-report.md")])
    _jsonl(root / "assets/WELL-9001/context.jsonl", [
        {"asset_id": "WELL-9001", "created_at": "2026-02-10T09:00:00Z", "author_user_id": "U-2", "note_type": "correction", "inspection_id": "INS-9001-0005",
         "text": "Inspection INS-9001-0005: wet soil after rain. Not a crude spill.", "valid_from": "2026-02-09", "valid_to": None, "note_id": "CTX-9001-001"},
        {"asset_id": "WELL-9001", "created_at": "2026-03-05T09:00:00Z", "author_user_id": "U-1", "note_type": "operator_feedback",
         "text": "Well shut in for planned workover. Expected back around 20 Mar.", "valid_from": "2026-03-03", "valid_to": "2026-03-20", "note_id": "CTX-9001-002"}])
    _jsonl(root / "assets/WELL-9001/regulatory-events.jsonl", [])
    for well in ("WELL-9002", "WELL-9003"):
        _jsonl(root / "assets" / well / "context.jsonl", [])
        _jsonl(root / "assets" / well / "regulatory-events.jsonl", [])
    _jsonl(root / "assets/WELL-9002/maintenance-reports/.keep", []) if False else None
    return root
