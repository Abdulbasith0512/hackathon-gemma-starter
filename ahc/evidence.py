"""Resolve a citation ID to the actual record or document passage, for the evidence panel."""

import json
import re

from .analyst import Analyst, fmt_date

_SOP_PROTOCOL = re.compile(r"^[A-Z]{2,3}-\d{2}$")


def _rel(ref: str, label: str) -> dict:
    return {"ref": ref, "label": label}


def _fields(d: dict, skip=("raw",)) -> list[list]:
    return [[k, "" if v is None else v] for k, v in d.items() if k not in skip]


def resolve(A: Analyst, ref: str) -> dict | None:
    c, store = A.c, A.store
    ref = ref.strip()
    out = {"ref": ref, "kind": None, "title": ref, "subtitle": "", "fields": [], "sections": [], "related": [], "corrections": [], "source": None, "raw": None}

    if ref.startswith("INS-"):
        row = c.execute("SELECT * FROM inspections WHERE inspection_id=?", (ref,)).fetchone()
        if not row:
            return None
        i = A.get_inspection(ref)
        out.update(kind="inspection", title=f"Inspection {ref}", subtitle=f"{i['asset_id']} · {fmt_date(i['inspected_at'])}", source=row["source"], raw=json.loads(row["raw"]))
        flds = [["Well", i["asset_id"]], ["Inspected at", i["inspected_at"]], ["Inspector", A.user_name(i["inspector_user_id"])], ["Method", i["method"]],
                ["Ambient temp (°C)", i["ambient_temp_c"]], ["Wellhead temp (°C)", i["wellhead_temp_c"]], ["Wellhead above air (°C)", i["delta"]],
                ["Threshold (°C)", i["threshold"]], ["Producing oil", {True: "yes", False: "no", None: "unknown"}[i["producing"]]],
                ["Spill (effective)", "yes" if i["spill"] else "no"], ["Spill volume (bbl)", i["spill_est_volume_bbl"]], ["Pad area (%)", i["spill_area_pct"]], ["Inspector notes", i["notes"]]]
        out["fields"] = flds
        if i["spill_override"]:
            out["fields"].append(["Detection corrected by", f"{i['spill_override']['note_id']}: {i['spill_override']['text']}"])
            out["related"].append(_rel(i["spill_override"]["note_id"], "Correction note"))
        out["corrections"] = [dict(cor) for cor in i["corrections"]]
        for cor in store.corrections_for(ref) if store else []:
            out["related"].append(_rel(cor["correction_id"], f"{cor['correction_id']} ({cor['status']})"))
        for m in c.execute("SELECT maintenance_id, issue FROM maintenance WHERE triggered_by_inspection_id=?", (ref,)):
            out["related"].append(_rel(m["maintenance_id"], f"Repair {m['maintenance_id']}: {m['issue']}"))
        for r in c.execute("SELECT event_id, event_type FROM regulatory_events WHERE related_inspection_id=?", (ref,)):
            out["related"].append(_rel(r["event_id"], f"{r['event_id']} {r['event_type']}"))
        return out

    if ref.startswith("MNT-"):
        row = c.execute("SELECT * FROM maintenance WHERE maintenance_id=?", (ref,)).fetchone()
        if not row:
            return None
        out.update(kind="maintenance", title=f"Repair {ref}", subtitle=f"{row['asset_id']} · {row['equipment_kind']} · {row['maintenance_type']}", source=row["source"], raw=json.loads(row["raw"]))
        out["fields"] = [["Well", row["asset_id"]], ["Started", row["started_at"]], ["Completed / planned end", row["completed_at"]], ["Issue", row["issue"]], ["Action taken", row["action_taken"]],
                         ["Technician", A.user_name(row["technician_user_id"])], ["Contractor", row["contractor"]], ["Downtime of this job (hours)", row["downtime_hours"]],
                         ["Cost labor / parts / total (USD)", f"{row['cost_labor']} / {row['cost_parts']} / {row['cost_total']}"], ["Triggered by", row["triggered_by_inspection_id"]], ["Report file", row["report_file"]]]
        if row["triggered_by_inspection_id"]:
            out["related"].append(_rel(row["triggered_by_inspection_id"], "Triggering inspection"))
        if c.execute("SELECT 1 FROM documents WHERE doc_id=?", (f"report:{ref}",)).fetchone():
            out["related"].append(_rel(f"report:{ref}", "Full repair report"))
            f = c.execute("SELECT * FROM report_facts WHERE maintenance_id=?", (ref,)).fetchone()
            if f and f["containment_hours"] is not None:
                out["fields"].append(["Containment time from report (hours)", f["containment_hours"]])
        return out

    if ref.startswith("REG-"):
        row = c.execute("SELECT * FROM regulatory_events WHERE event_id=?", (ref,)).fetchone()
        if not row:
            return None
        out.update(kind="regulatory", title=f"Regulatory event {ref}", subtitle=f"{row['asset_id']} · {row['event_type']}", source=row["source"], raw=json.loads(row["raw"]))
        out["fields"] = _fields(dict(row), skip=("raw", "source"))
        if row["related_inspection_id"]:
            out["related"].append(_rel(row["related_inspection_id"], "Related inspection"))
        return out

    if ref.startswith("CTX-"):
        row = c.execute("SELECT * FROM notes WHERE note_id=?", (ref,)).fetchone()
        if not row:
            return None
        out.update(kind="note", title=f"Note {ref}", subtitle=f"{row['asset_id']} · {row['note_type']} · {A.user_name(row['author_user_id'])}", source=row["source"], raw=json.loads(row["raw"]))
        out["fields"] = [["Text", row["text"]], ["Type", row["note_type"]], ["Author", A.user_name(row["author_user_id"])], ["Created", row["created_at"]], ["Valid from", row["valid_from"]], ["Valid to", row["valid_to"]], ["Inspection corrected", row["inspection_id"]]]
        if row["inspection_id"]:
            out["related"].append(_rel(row["inspection_id"], "Inspection this note corrects"))
        return out

    if ref.startswith("COR-") and store:
        cor = store.get_correction(ref)
        if not cor:
            return None
        out.update(kind="correction", title=f"Correction {ref}", subtitle=f"{cor['field']} on {cor['target_id']} · {cor['status']}")
        out["fields"] = [["Record corrected", cor["target_id"]], ["Field", cor["field"]], ["Original value (dataset)", cor["original_value"]], ["Value before this correction", cor["previous_value"]], ["New value", cor["new_value"]],
                         ["Reason", cor["reason"]], ["Corrected by", A.user_name(cor["author_user_id"])], ["When", cor["created_at"]], ["Scope", f"{cor['scope_type']}: {cor['scope_value']}"], ["Status", cor["status"]], ["Supersedes", cor["supersedes_id"]]]
        out["related"].append(_rel(cor["target_id"], "Corrected record"))
        return out

    if ref.startswith("SN-") and store:
        n = store.get_shared_note(ref)
        if not n:
            return None
        out.update(kind="shared_note", title=f"Shared note {ref}", subtitle=f"{n['asset_id']} · {n['kind']} · {n['status']}")
        out["fields"] = [["Text", n["text"]], ["Author", A.user_name(n["author_user_id"])], ["Saved", n["created_at"]], ["Valid from", n["valid_from"]], ["Valid to", n["valid_to"]], ["Status", n["status"]],
                         ["Check against records", json.dumps(n["verdict"]) if n["verdict"] else ""]]
        out["related"].append(_rel(n["asset_id"], "Well"))
        return out

    if ref.startswith("RULE-") and store:
        r = next((x for x in store.all_scoped_rules() if x["rule_id"] == ref), None)
        if not r:
            return None
        out.update(kind="rule", title=f"Rule {ref}", subtitle=f"{r['scope_type']} {r['scope_value']} · {r['key']}")
        out["fields"] = [["Scope", f"{r['scope_type']}: {r['scope_value']}"], ["Setting", r["key"]], ["Equipment", r["equipment_kind"]], ["Value", r["value"]], ["Reason", r["reason"]], ["Set by", A.user_name(r["author_user_id"])], ["When", r["created_at"]], ["Status", r["status"]], ["Original wording", r["source_text"]]]
        return out

    if ref.startswith("WELL-"):
        w = A.wells.get(ref)
        if not w:
            return None
        row = c.execute("SELECT raw, source FROM wells WHERE asset_id=?", (ref,)).fetchone()
        meta = json.loads(row["raw"])
        out.update(kind="well", title=ref, subtitle=f"{w['name']} · {w['well_type']}", source=row["source"], raw=meta)
        out["fields"] = [["Name", w["name"]], ["Type", w["well_type"]], ["Area", A.areas.get(w["area_id"], {}).get("name", w["area_id"])], ["In charge", A.user_name(w["in_charge_user_id"])], ["Location", f"{w['lat']}, {w['lon']}"],
                         ["Installed", meta.get("installed_on")], ["Recorded status", w["recorded_status"]], ["Equipment", ", ".join(f"{e['kind']} ({e['model']})" for e in meta.get("equipment", []))]]
        return out

    if ref.startswith("report:"):
        doc = c.execute("SELECT * FROM documents WHERE doc_id=?", (ref,)).fetchone()
        if not doc:
            return None
        out.update(kind="report", title=doc["title"], subtitle=f"{doc['asset_id']} · {doc['maintenance_id']}", source=doc["path"])
        out["sections"] = [{"heading": s["heading"], "text": s["text"], "highlight": False} for s in c.execute("SELECT heading, text FROM sections WHERE doc_id=? ORDER BY ord", (ref,))]
        out["related"].append(_rel(doc["maintenance_id"], "Repair record"))
        return out

    doc_id = section_id = None
    if _SOP_PROTOCOL.match(ref):
        s = c.execute("SELECT doc_id, section_id FROM sections WHERE section_id=? AND doc_id LIKE 'sop:%' LIMIT 1", (ref,)).fetchone()
        doc_id, section_id = (s["doc_id"], s["section_id"]) if s else (None, None)
    elif "#" in ref:
        name, section_id = ref.split("#", 1)
        for prefix in ("manual", "sop"):
            if c.execute("SELECT 1 FROM documents WHERE doc_id=?", (f"{prefix}:{name}",)).fetchone():
                doc_id = f"{prefix}:{name}"
                break
    if doc_id:
        doc = c.execute("SELECT * FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
        out.update(kind="document", title=doc["title"], subtitle=f"{doc['kind']} · section {section_id}", source=doc["path"])
        out["sections"] = [{"heading": s["heading"], "text": s["text"], "highlight": s["section_id"] == section_id}
                           for s in c.execute("SELECT section_id, heading, text FROM sections WHERE doc_id=? AND NOT (section_id GLOB '[A-Z][A-Z]-[0-9][0-9]' OR section_id GLOB '[A-Z][A-Z][A-Z]-[0-9][0-9]') ORDER BY ord", (doc_id,))]
        if _SOP_PROTOCOL.match(ref):
            row = c.execute("SELECT heading, text FROM sections WHERE doc_id=? AND section_id=?", (doc_id, ref)).fetchone()
            out["sections"].insert(0, {"heading": f"Protocol {ref}", "text": row["text"], "highlight": True})
        return out
    return None
