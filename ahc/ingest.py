"""Load the documented dataset folders into SQLite.

Nothing here knows any well ID, area name or answer: it only follows the documented
layout (fleet/ and assets/<ASSET_ID>/) and the `report_file` field of each repair.
Several roots can be loaded; later roots extend or override earlier ones by record ID.
"""

import hashlib
import json
import os
import re
from pathlib import Path

from . import db as dbmod

SCHEMA_VERSION = "2"
_HEAD = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_PROTOCOL_ROW = re.compile(r"^\|\s*\*\*([A-Z]{2,3}-\d{2})\*\*\s*\|(.+)\|\s*$")
_CONTAINED = re.compile(r"[Cc]ontained about\s+\*{0,2}([0-9]+(?:\.[0-9]+)?)\s+hours")
_CLASS = re.compile(r"\((minor|moderate|reportable|major) class\)", re.I)


def fingerprint(roots: list[Path]) -> str:
    h = hashlib.sha256(SCHEMA_VERSION.encode())
    for root in roots:
        for dirpath, _dirs, files in os.walk(root):
            for name in sorted(files):
                p = Path(dirpath) / name
                st = p.stat()
                h.update(f"{p.relative_to(root).as_posix()}|{st.st_size}|{st.st_mtime_ns}".encode())
    return h.hexdigest()


def _jsonl(path: Path, issues: list[str]) -> list[tuple[int, dict]]:
    out = []
    if not path.exists():
        return out
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            out.append((n, json.loads(line)))
        except json.JSONDecodeError as e:
            issues.append(f"{path.name}:{n}: bad JSON ({e.msg})")
    return out


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def split_sections(text: str) -> list[dict]:
    """Markdown -> [{section_id, heading, text}]. '## 9.3 Title' gets section_id '9.3'."""
    sections, cur = [], None
    for line in text.splitlines():
        m = _HEAD.match(line)
        if m:
            if cur:
                sections.append(cur)
            heading = m.group(2).strip()
            num = re.match(r"^(\d+(?:\.\d+)*)\.?\s+(.*)$", heading)
            cur = {"section_id": num.group(1) if num else _slug(heading), "heading": heading, "lines": []}
        else:
            if cur is None:
                cur = {"section_id": "intro", "heading": "(intro)", "lines": []}
            cur["lines"].append(line)
    if cur:
        sections.append(cur)
    return [{"section_id": s["section_id"], "heading": s["heading"], "text": "\n".join(s["lines"]).strip()} for s in sections]


def protocol_sections(text: str) -> list[dict]:
    """SOP protocol table rows (| **SR-01** | requirement | ...) become sections of their own."""
    out = []
    for line in text.splitlines():
        m = _PROTOCOL_ROW.match(line.strip())
        if m:
            out.append({"section_id": m.group(1), "heading": m.group(1), "text": m.group(2).strip().strip("|").strip()})
    return out


def parse_report(text: str) -> tuple[dict, list[tuple[str, str, str]]]:
    """Deterministic facts from a maintenance report: containment time, spill class, compliance rows."""
    rows, in_table = [], False
    for line in text.splitlines():
        if line.startswith("#"):
            in_table = line.lower().lstrip("# ").startswith("compliance check")
        elif in_table and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 3 and re.match(r"^[A-Z]{2,3}-\d{2}$", cells[0]):
                rows.append((cells[0], cells[1].strip("* ").strip(), cells[2]))
    hours = quote = None
    for _pid, _res, detail in rows:
        m = _CONTAINED.search(detail)
        if m:
            hours, quote = float(m.group(1)), detail
            break
    if hours is None:
        m = _CONTAINED.search(text)
        if m:
            hours = float(m.group(1))
            start = max(text.rfind(".", 0, m.start()) + 1, 0)
            end = text.find(".", m.end())
            quote = text[start : end + 1 if end != -1 else None].strip().replace("\n", " ")
    cls = None
    for _pid, _res, detail in rows:
        m = _CLASS.search(detail)
        if m:
            cls = m.group(1).lower()
            break
    return {
        "containment_hours": hours,
        "containment_quote": quote,
        "spill_class": cls,
        "action_required": 1 if re.search(r"action required", text, re.I) else 0,
    }, rows


def _num(v):
    return None if v is None else float(v)


def _load_root(conn, root: Path, issues: list[str], stats: dict, seen: dict | None = None) -> None:
    seen = {} if seen is None else seen
    over = stats.setdefault("overwritten", {})

    def mark(table: str, key) -> None:
        ids = seen.setdefault(table, set())
        if key in ids:
            over[table] = over.get(table, 0) + 1
        ids.add(key)

    fleet = root / "fleet"
    areas_file = fleet / "areas.json"
    if areas_file.exists():
        data = json.loads(areas_file.read_text(encoding="utf-8"))
        for a in data.get("areas", []):
            c = a.get("center") or {}
            conn.execute("INSERT OR REPLACE INTO areas VALUES (?,?,?,?,?,?)",
                         (a["area_id"], a.get("name"), a.get("team_id"), c.get("lat"), c.get("lon"), json.dumps(a)))
        for t in data.get("teams", []):
            conn.execute("INSERT OR REPLACE INTO teams VALUES (?,?,?)", (t["team_id"], t.get("name"), t.get("lead_user_id")))
        area_of = {w: a["area_id"] for a in data.get("areas", []) for w in a.get("asset_ids", [])}
    else:
        area_of = {}
    users_file = fleet / "users.json"
    if users_file.exists():
        for u in json.loads(users_file.read_text(encoding="utf-8")).get("users", []):
            conn.execute("INSERT OR REPLACE INTO users VALUES (?,?,?,?)", (u["user_id"], u.get("name"), u.get("role"), u.get("team_id")))

    for sub, kind in (("well-types", "manual"), ("sops", "sop")):
        for path in sorted((fleet / sub).glob("*.md")) if (fleet / sub).is_dir() else []:
            text = path.read_text(encoding="utf-8")
            title = next((m.group(2) for m in map(_HEAD.match, text.splitlines()) if m), path.stem)
            doc_id = f"{kind}:{path.stem}"
            conn.execute("INSERT OR REPLACE INTO documents VALUES (?,?,?,?,?,?,?,?)",
                         (doc_id, kind, title, path.stem if kind == "manual" else None, None, None, path.relative_to(root).as_posix(), text))
            _add_sections(conn, doc_id, split_sections(text) + (protocol_sections(text) if kind == "sop" else []))
            stats["documents"] += 1

    assets = root / "assets"
    for wdir in sorted(assets.glob("*")) if assets.is_dir() else []:
        if not wdir.is_dir():
            continue
        meta_file = wdir / "metadata.json"
        if not meta_file.exists():
            issues.append(f"{wdir.name}: no metadata.json")
            continue
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        aid = meta["asset_id"]
        mark("wells", aid)
        loc = meta.get("location") or {}
        conn.execute("INSERT OR REPLACE INTO wells VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (aid, meta.get("name"), meta.get("well_type"), meta.get("area_id") or area_of.get(aid), meta.get("team_id"),
                      meta.get("in_charge_user_id"), loc.get("lat"), loc.get("lon"), meta.get("installed_on"),
                      meta.get("recorded_status"), (meta.get("last_inspection") or {}).get("inspection_id"),
                      json.dumps(meta), meta_file.relative_to(root).as_posix()))
        stats["wells"] += 1

        for n, r in _jsonl(wdir / "inspections.jsonl", issues):
            at = r.get("inspected_at") or ""
            mark("inspections", r["inspection_id"])
            conn.execute("INSERT OR REPLACE INTO inspections VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         (r["inspection_id"], r.get("asset_id", aid), at, at[:10], r.get("inspector_user_id"), r.get("method"),
                          _num(r.get("ambient_temp_c")), _num(r.get("wellhead_temp_c")), 1 if r.get("spill_detected") else 0,
                          _num(r.get("spill_area_pct")), _num(r.get("spill_est_volume_bbl")), r.get("notes") or "",
                          json.dumps(r), f"{wdir.name}/inspections.jsonl:{n}"))
            stats["inspections"] += 1

        for n, r in _jsonl(wdir / "maintenance.jsonl", issues):
            cost = r.get("cost_usd") or {}
            s, c = r.get("started_at") or "", r.get("completed_at") or ""
            mark("maintenance", r["maintenance_id"])
            conn.execute("INSERT OR REPLACE INTO maintenance VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         (r["maintenance_id"], r.get("asset_id", aid), s, c, s[:10], c[:10], r.get("maintenance_type"),
                          r.get("equipment_kind"), r.get("issue"), r.get("action_taken"), r.get("technician_user_id"),
                          r.get("contractor"), _num(r.get("downtime_hours")), _num(cost.get("labor")), _num(cost.get("parts")),
                          _num(cost.get("total")), r.get("triggered_by_inspection_id"), r.get("report_file"),
                          json.dumps(r), f"{wdir.name}/maintenance.jsonl:{n}"))
            stats["maintenance"] += 1
            rf = r.get("report_file")  # always follow the field; never guess file names
            if rf:
                rpath = wdir / rf
                if rpath.exists():
                    text = rpath.read_text(encoding="utf-8")
                    mid = r["maintenance_id"]
                    conn.execute("INSERT OR REPLACE INTO documents VALUES (?,?,?,?,?,?,?,?)",
                                 (f"report:{mid}", "report", f"Maintenance report {mid}", None, aid, mid, rpath.relative_to(root).as_posix(), text))
                    _add_sections(conn, f"report:{mid}", split_sections(text))
                    facts, rows = parse_report(text)
                    conn.execute("INSERT OR REPLACE INTO report_facts VALUES (?,?,?,?,?)",
                                 (mid, facts["containment_hours"], facts["containment_quote"], facts["spill_class"], facts["action_required"]))
                    conn.execute("DELETE FROM report_compliance WHERE maintenance_id=?", (mid,))
                    conn.executemany("INSERT INTO report_compliance VALUES (?,?,?,?)", [(mid, *row) for row in rows])
                    stats["reports"] += 1
                else:
                    issues.append(f"{r['maintenance_id']}: report_file missing on disk: {rf}")

        for n, r in _jsonl(wdir / "regulatory-events.jsonl", issues):
            conn.execute("INSERT OR REPLACE INTO regulatory_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         (r["event_id"], r.get("asset_id", aid), r.get("date"), r.get("agency"), r.get("event_type"), r.get("protocol_id"),
                          r.get("related_inspection_id"), _num(r.get("hours_to_report")), r.get("detail"), _num(r.get("fine_usd")),
                          r.get("status"), json.dumps(r), f"{wdir.name}/regulatory-events.jsonl:{n}"))
            stats["regulatory_events"] += 1

        for n, r in _jsonl(wdir / "context.jsonl", issues):
            conn.execute("INSERT OR REPLACE INTO notes VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (r["note_id"], r.get("asset_id", aid), r.get("created_at"), r.get("author_user_id"), r.get("note_type"),
                          r.get("inspection_id"), r.get("text"), r.get("valid_from"), r.get("valid_to"), json.dumps(r),
                          f"{wdir.name}/context.jsonl:{n}"))
            stats["notes"] += 1


def _add_sections(conn, doc_id: str, sections: list[dict]) -> None:
    conn.execute("DELETE FROM sections WHERE doc_id=?", (doc_id,))
    for i, s in enumerate(sections):
        conn.execute("INSERT INTO sections(doc_id, ord, section_id, heading, text) VALUES (?,?,?,?,?)",
                     (doc_id, i, s["section_id"], s["heading"], s["text"]))


def ingest(roots: list[Path], db_path: Path, force: bool = False) -> dict:
    """Build (or reuse) the dataset database. Returns counts, issues and the fingerprint."""
    roots = [Path(r) for r in roots]
    missing = [str(r) for r in roots if not r.is_dir()]
    if missing:
        raise FileNotFoundError(
            f"Dataset folder not found: {', '.join(missing)}. Put the official sample-data folder at "
            "data/sample-data/ or set AHC_DATA_DIRS."
        )
    fp = fingerprint(roots)
    db_path = Path(db_path)
    if db_path.exists() and not force:
        conn = dbmod.connect(db_path)
        try:
            row = conn.execute("SELECT value FROM meta WHERE key='fingerprint'").fetchone()
            if row and row["value"] == fp:
                stats = json.loads(conn.execute("SELECT value FROM meta WHERE key='stats'").fetchone()["value"])
                stats["reused"] = True
                return stats
        except Exception:
            pass
        finally:
            conn.close()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = db_path.with_suffix(".building")
    if tmp.exists():
        tmp.unlink()
    conn = dbmod.connect(tmp)
    stats = {k: 0 for k in ("wells", "inspections", "maintenance", "regulatory_events", "notes", "reports", "documents")}
    issues: list[str] = []
    try:
        dbmod.create_schema(conn)
        seen: dict = {}
        for root in roots:
            _load_root(conn, root, issues, stats, seen)
        for table, n in (stats.get("overwritten") or {}).items():
            issues.append(f"{n} {table} record(s) from an earlier dataset root were replaced by the same ID in a later root.")
        conn.execute("INSERT INTO sections_fts(rowid, heading, text) SELECT rowid, heading, text FROM sections")
        stats["roots"] = [str(r) for r in roots]
        stats["issues"] = issues[:50]
        stats["issue_count"] = len(issues)
        stats["reused"] = False
        conn.execute("INSERT INTO meta VALUES ('fingerprint', ?)", (fp,))
        conn.execute("INSERT INTO meta VALUES ('stats', ?)", (json.dumps(stats),))
        conn.commit()
    finally:
        conn.close()
    os.replace(tmp, db_path)
    return stats
