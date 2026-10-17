"""Writes to shared knowledge: corrections, type-scoped rules, shared notes, status claims.

A correction or rule is first PROPOSED: the preview shows the original value, the current value
and the replacement, who is making the change, why, and at what scope. Nothing is saved until the
user confirms (or the caller is a batch run with auto_confirm). Originals are never overwritten.
"""

import json
import re
from datetime import date, timedelta

from .analyst import Analyst, Cites, ToolError, fmt_date, fmt_num

FIELD_LABEL = {"wellhead_temp_c": "Wellhead temperature (°C)", "ambient_temp_c": "Air temperature (°C)",
               "spill_est_volume_bbl": "Spill volume estimate (bbl)", "spill_area_pct": "Spill area (% of pad)"}
FIELD_ALIASES = {"wellhead": "wellhead_temp_c", "wellhead_temp": "wellhead_temp_c", "wellhead_temperature": "wellhead_temp_c", "temperature": "wellhead_temp_c", "temp": "wellhead_temp_c",
                 "ambient": "ambient_temp_c", "air": "ambient_temp_c", "ambient_temp": "ambient_temp_c", "volume": "spill_est_volume_bbl", "spill_volume": "spill_est_volume_bbl",
                 "spill_volume_bbl": "spill_est_volume_bbl", "spill_area": "spill_area_pct", "area": "spill_area_pct"}
RULE_KEYS = {"rca_corrective_count": ("corrective repairs", "number of corrective repairs on the same equipment in 12 months that triggers a root-cause analysis")}


def _author(A: Analyst, user_id: str) -> str:
    u = A.users.get(user_id, {})
    return f"{u.get('name', user_id)} ({(u.get('role') or 'user').replace('_', ' ')})"


def _find_inspection(A: Analyst, asset_id: str, date_s: str | None, inspection_id: str | None) -> dict:
    if inspection_id:
        ins = A.get_inspection(inspection_id.strip())
        if not ins:
            raise ToolError(f"Unknown inspection '{inspection_id}'.")
        return ins
    aid = A.well(asset_id)["asset_id"]
    if date_s:
        date_s = A.match_date(aid, date_s)
        rows = A.inspections([aid], date_s[:10], date_s[:10])
        if not rows:
            near = [r["inspected_date"] for r in A.inspections([aid], (date.fromisoformat(date_s[:10]) - timedelta(days=10)).isoformat(), (date.fromisoformat(date_s[:10]) + timedelta(days=10)).isoformat())]
            raise ToolError(f"{aid} has no inspection on {date_s[:10]}." + (f" Nearby inspections: {', '.join(near)}." if near else ""))
        return rows[0]
    ins = A.latest(aid)
    if not ins:
        raise ToolError(f"{aid} has no inspections.")
    return ins


def _simulate(A: Analyst, ins: dict, field: str, new) -> dict:
    """The inspection as it would look with the correction applied (nothing saved)."""
    sim = dict(ins)
    sim[field] = new
    wh, amb = sim.get("wellhead_temp_c"), sim.get("ambient_temp_c")
    sim["delta"] = round(wh - amb, 6) if wh is not None and amb is not None else None
    sim["producing"] = None if sim["delta"] is None or sim["threshold"] is None else sim["delta"] >= sim["threshold"] - 1e-9
    return sim


def propose_correction(ctx, args: dict) -> dict:
    A, store = ctx.analyst, ctx.store
    field = FIELD_ALIASES.get(str(args.get("field", "")).strip().lower(), str(args.get("field", "")).strip())
    if field not in FIELD_LABEL:
        raise ToolError(f"I can correct: {', '.join(FIELD_LABEL)}. Which one do you mean?")
    try:
        new = float(args["new_value"])
    except (KeyError, TypeError, ValueError):
        raise ToolError("Give the corrected value as a number.")
    reason = str(args.get("reason") or "").strip()
    if not reason:
        raise ToolError("A correction needs a reason (for example, what the crew re-measured).")
    ins = _find_inspection(A, args.get("asset_id", ""), args.get("date"), args.get("inspection_id"))
    cites = Cites()
    A.c_ins(cites, ins)
    A.c_well(cites, ins["asset_id"])
    orig, current = ins["orig"][field], ins[field]
    warnings, impact = [], []
    if field.endswith("temp_c") and not -60 <= new <= 200:
        warnings.append(f"{fmt_num(new)} °C looks implausible for a well-site reading.")
    if field.startswith("spill") and new < 0:
        raise ToolError("A spill volume or area cannot be negative.")
    if field == "spill_area_pct" and new > 100:
        raise ToolError("Spill area is a percentage of the pad (0-100).")
    old_cor = [c for c in ins["corrections"] if c["field"] == field]
    if old_cor:
        warnings.append(f"This replaces {old_cor[0]['correction_id']} ({A.user_name(old_cor[0]['author_user_id'])}); that correction stays in the history.")
        A.c_cor(cites, old_cor[0])
    sim = _simulate(A, ins, field, new)
    if field in ("wellhead_temp_c", "ambient_temp_c") and sim["producing"] is not None and ins["producing"] is not None:
        word = lambda p: "producing" if p else "not producing"
        impact.append(f"Status at this inspection changes from {word(ins['producing'])} ({fmt_num(ins['delta'])} °C above air) to {word(sim['producing'])} ({fmt_num(sim['delta'])} °C above air; the {ins['well_type']} limit is {fmt_num(ins['threshold'])} °C)."
                      if sim["producing"] != ins["producing"] else f"Status at this inspection stays {word(ins['producing'])} ({fmt_num(ins['delta'])} → {fmt_num(sim['delta'])} °C above air).")
        latest = A.latest(ins["asset_id"])
        if latest and latest["inspection_id"] == ins["inspection_id"] and sim["producing"] != ins["producing"]:
            impact.append(f"This is the latest inspection, so {ins['asset_id']}'s current status changes.")
        if sim["producing"] != ins["producing"]:
            A.c_rule(cites, A.threshold_for(ins["well_type"]))
    if field == "spill_est_volume_bbl":
        c_old, c_new = A.spill_class(current), A.spill_class(new)
        impact.append(f"Spill class changes from {c_old} to {c_new}." if c_old != c_new else f"Spill class stays {c_new}.")
        if c_new in ("reportable", "major") and c_old not in ("reportable", "major"):
            impact.append(f"At {fmt_num(new)} bbl the spill becomes reportable (≥ {fmt_num(A.rules.value('spill.reportable_min_bbl', default=5.0))} bbl), so a written notice, a 24-hour deadline and agency verification now apply.")
    conflicts = []
    if sim.get("producing") != ins["producing"] or field.startswith("spill"):
        if ins.get("notes"):
            who = A.user_name(ins["inspector_user_id"])
            conflicts.append(f"The same inspection has the note \"{ins['notes']}\" ({who}), which may disagree with this correction. {A.user_name(ctx.user_id)} should confirm.")
        for n in A.notes_about(ins["inspection_id"]):
            if n["note_type"] != "correction":
                A.c_note(cites, n) if n["source"] == "dataset" else None
                conflicts.append(f"Note {n['note_id']} by {A.user_name(n['author_user_id'])}: \"{n['text']}\"")
    rows = [["Record", f"{ins['inspection_id']} · {ins['asset_id']} · {fmt_date(ins['inspected_at'])}"], ["Field", FIELD_LABEL[field]], ["Original value (dataset)", fmt_num(orig), "orig"]]
    if current != orig:
        rows.append(["Current value (already corrected)", fmt_num(current), "orig"])
    rows += [["Proposed value", fmt_num(new), "new"], ["Scope", f"This inspection only ({ins['inspection_id']}); every other record is unchanged, and it applies to all users' later answers"],
             ["Corrected by", _author(A, ctx.user_id)], ["Reason", reason]]
    payload = {"inspection_id": ins["inspection_id"], "asset_id": ins["asset_id"], "field": field, "original": orig, "previous": current, "new": new, "reason": reason}
    preview = {"title": f"Proposed correction to {ins['inspection_id']}", "rows": rows, "impact": impact, "warnings": conflicts + warnings}
    res = A.result("propose_correction", f"Proposed correction to {ins['inspection_id']}", cites, entities={"wells": [ins["asset_id"]]})
    facts = [{"text": f"Proposed: change {FIELD_LABEL[field]} on {ins['inspection_id']} ({ins['asset_id']}, {fmt_date(ins['inspected_at'])}) from {fmt_num(orig)}" + (f" (currently {fmt_num(current)})" if current != orig else "") + f" to {fmt_num(new)}, by {A.user_name(ctx.user_id)}. Reason: {reason}. The original value is kept.", "cites": [ins["inspection_id"]]}]
    facts += [{"text": t, "cites": [ins["inspection_id"]]} for t in impact]
    res["facts"] = facts
    res["flags"] = [{"type": "needs_confirmation", "text": t, "refs": [ins["inspection_id"]]} for t in conflicts]
    res["visuals"] = {}
    res["natural"] = "table"
    if ctx.auto_confirm:
        return apply_action(A, store, ctx.user_id, "correction", payload, preview)
    res["pending"] = {"action_id": store.create_pending(ctx.user_id, ctx.conv_id, "correction", {"payload": payload, "preview": preview}), "kind": "correction", "preview": preview}
    res["citations"] = cites.list()
    return res


def propose_rule(ctx, args: dict) -> dict:
    A, store = ctx.analyst, ctx.store
    scope_type = str(args.get("scope_type") or "well_type").lower()
    scope_value = str(args.get("scope_value") or "").strip()
    key = str(args.get("key") or "rca_corrective_count").strip()
    if key not in RULE_KEYS:
        raise ToolError("I can set the root-cause-analysis threshold (rca_corrective_count) for a well type or a single well.")
    if scope_type == "well_type":
        scope_value = scope_value.upper()
        if scope_value not in A.rules.well_types:
            raise ToolError(f"Unknown well type '{scope_value}'. Known types: {', '.join(A.rules.well_types)}.")
    elif scope_type == "well":
        scope_value = A.well(scope_value)["asset_id"]
    else:
        raise ToolError("A rule is scoped to a well_type or a single well.")
    try:
        value = float(args["value"])
    except (KeyError, TypeError, ValueError):
        raise ToolError("Give the new threshold as a number.")
    equipment = (str(args.get("equipment_kind") or "").strip().lower().replace(" ", "_")) or None
    reason = str(args.get("reason") or "").strip() or "Team policy (no reason given)"
    wt = scope_value if scope_type == "well_type" else A.wells[scope_value]["well_type"]
    manual = A.rules.get(key, wt)
    cites = Cites()
    if manual:
        A.c_rule(cites, manual)
    eq_txt = equipment.replace("_", " ") if equipment else "any equipment"
    rows = [["Scope", f"{'All ' + scope_value + ' wells' if scope_type == 'well_type' else 'Well ' + scope_value} only"], ["Setting", "Root-cause analysis after this many corrective repairs in 12 months"],
            ["Equipment", eq_txt], ["Manual value", f"{fmt_num(manual.value, 0) if manual else 'none'} ({manual.ref if manual else 'no manual rule'})", "orig"], ["Proposed value", fmt_num(value, 0), "new"],
            ["Set by", _author(A, ctx.user_id)], ["Reason", reason], ["Original wording", ctx.message or ""]]
    others = sorted({t for t in A.rules.well_types if t != wt}) if scope_type == "well_type" else []
    impact = [f"Other well types ({', '.join(others)}) keep the manual's value." if others else "Other wells keep the manual's value."]
    payload = {"scope_type": scope_type, "scope_value": scope_value, "key": key, "equipment_kind": equipment, "value": value, "reason": reason, "source_text": ctx.message or ""}
    preview = {"title": f"New rule for {scope_value}", "rows": rows, "impact": impact, "warnings": []}
    res = A.result("propose_rule", f"New rule for {scope_value}", cites)
    res["facts"] = [{"text": f"Proposed: for {scope_value} {'wells' if scope_type == 'well_type' else ''}, a root-cause analysis on {eq_txt} after {fmt_num(value, 0)} corrective repairs in 12 months (the manual says {fmt_num(manual.value, 0) if manual else 'nothing'}), set by {A.user_name(ctx.user_id)}.", "cites": [manual.ref] if manual else []}] + [{"text": t, "cites": []} for t in impact]
    res["visuals"] = {}
    if ctx.auto_confirm:
        return apply_action(A, store, ctx.user_id, "rule", payload, preview)
    res["pending"] = {"action_id": store.create_pending(ctx.user_id, ctx.conv_id, "rule", {"payload": payload, "preview": preview}), "kind": "rule", "preview": preview}
    return res


def apply_action(A: Analyst, store, user_id: str, kind: str, payload: dict, preview: dict) -> dict:
    """Save a confirmed proposal and return the result to show (a normal tool result)."""
    cites = Cites()
    if kind == "correction":
        cor = store.add_correction(target_id=payload["inspection_id"], asset_id=payload["asset_id"], field=payload["field"], original=payload["original"], previous=payload["previous"],
                                   new=payload["new"], reason=payload["reason"], author_user_id=user_id)
        A2 = Analyst(A.c, A.rules, store, A.as_of)
        ins = A2.get_inspection(payload["inspection_id"])
        A2.c_cor(cites, cor)
        head = {"text": f"Saved correction {cor['correction_id']}: {FIELD_LABEL[payload['field']]} on {payload['inspection_id']} changed from {fmt_num(payload['original'])} to {fmt_num(payload['new'])} by {A2.user_name(user_id)} ({payload['reason']}). The original value is kept and the correction applies to everyone's later answers.", "cites": [cor["correction_id"], payload["inspection_id"]]}
        if payload["field"] in ("wellhead_temp_c", "ambient_temp_c"):
            res = A2.well_status(payload["asset_id"])
            res["facts"] = [head] + [{"text": t, "cites": [payload["inspection_id"]]} for t in preview.get("impact", [])] + res["facts"]
        else:
            res = A2.compliance_audit(payload["asset_id"], start=ins["inspected_date"], end=ins["inspected_date"], extras=False)
            res["facts"] = [head] + [{"text": t, "cites": [payload["inspection_id"]]} for t in preview.get("impact", [])] + res["facts"]
        for t in preview.get("warnings", []):
            if "disagree" in t or t.startswith("Note "):
                res["flags"].append({"type": "needs_confirmation", "text": t, "refs": [payload["inspection_id"]]})
        res["flags"].append({"type": "corrected", "text": f"{payload['inspection_id']}: {payload['field']} {fmt_num(payload['original'])} → {fmt_num(payload['new'])} ({cor['correction_id']}).", "refs": [cor["correction_id"]]})
        merged = {c["id"]: c for c in res["citations"]}
        merged.update({c["id"]: c for c in cites.list()})
        res["citations"] = list(merged.values())
        res["tool"], res["title"] = "apply_correction", f"Correction {cor['correction_id']} saved"
        res["saved"] = cor["correction_id"]
        return res
    if kind == "rule":
        sr = store.add_scoped_rule(scope_type=payload["scope_type"], scope_value=payload["scope_value"], key=payload["key"], value=payload["value"], unit="corrective repairs",
                                   reason=payload["reason"], author_user_id=user_id, equipment_kind=payload["equipment_kind"], source_text=payload["source_text"])
        cites.add(sr["rule_id"], "rule", f"{sr['rule_id']} · {sr['scope_type']} {sr['scope_value']} · {A.user_name(user_id)}")
        res = A.result("apply_rule", f"Rule {sr['rule_id']} saved", cites)
        res["facts"] = [{"text": f"Saved rule {sr['rule_id']}: for {payload['scope_value']}, a root-cause analysis after {fmt_num(payload['value'], 0)} corrective {(payload['equipment_kind'] or 'equipment').replace('_', ' ')} repairs in 12 months, set by {A.user_name(user_id)}. It applies only to {payload['scope_value']}; other well types keep the manual's value.", "cites": [sr["rule_id"]]}]
        res["saved"] = sr["rule_id"]
        res["flags"] = [{"type": "rule", "text": f"{sr['rule_id']} is a user rule for {payload['scope_value']}, not a manual rule.", "refs": [sr["rule_id"]]}]
        return res
    raise ValueError(f"Unknown action kind '{kind}'.")


def add_shared_note(ctx, args: dict) -> dict:
    A, store = ctx.analyst, ctx.store
    w = A.well(args.get("asset_id", ""))
    text = str(args.get("text") or "").strip()
    if not text:
        raise ToolError("Give the note text.")
    kind = str(args.get("kind") or "info").strip().lower()
    vf = (args.get("valid_from") or "").strip() or None
    vt = (args.get("valid_to") or "").strip() or None
    try:
        if vf:
            date.fromisoformat(vf)
        if vt:
            date.fromisoformat(vt)
        if vf and not vt and args.get("duration_days"):
            vt = (date.fromisoformat(vf) + timedelta(days=int(float(args["duration_days"])))).isoformat()
    except ValueError:
        raise ToolError("Dates must look like 2026-10-17.")
    n = store.add_shared_note(asset_id=w["asset_id"], kind=kind, text=text, author_user_id=ctx.user_id, valid_from=vf, valid_to=vt)
    cites = Cites()
    A.c_well(cites, w["asset_id"])
    cites.add(n["note_id"], "shared_note", f"{n['note_id']} · {kind} · {A.user_name(ctx.user_id)}")
    res = A.result("add_shared_note", f"Shared note saved for {w['asset_id']}", cites, entities={"wells": [w["asset_id"]]})
    span = f" from {fmt_date(vf)}" + (f" to {fmt_date(vt)}" if vt else "") if vf else ""
    res["facts"] = [{"text": f"Saved {n['note_id']} for {w['asset_id']}{span}: \"{text}\" (by {A.user_name(ctx.user_id)}). It is shared knowledge: other users asking about {w['asset_id']} will see it.", "cites": [n["note_id"]]}]
    res["visuals"] = {}
    return res


def check_claim(ctx, args: dict) -> dict:
    """A user says something about a well's state. Compare with the records and with what others said; keep every statement."""
    A, store = ctx.analyst, ctx.store
    data = A.claim_check(args.get("asset_id", ""), args.get("asserted_state", ""), args.get("since"))
    w, ins, verdict, cites, others = data["well"], data["ins"], data["verdict"], data["cites"], data["others"]
    aid = w["asset_id"]
    text = str(args.get("claim_text") or "").strip() or f"{aid} is {verdict['asserted'].replace('_', ' ')}"
    since = (args.get("since") or "").strip() or None
    status = "consistent_with_records" if verdict["matches"] else "unconfirmed"
    note = store.add_shared_note(asset_id=aid, kind="status_claim", text=text, author_user_id=ctx.user_id, valid_from=since, status=status, verdict=verdict)
    cites.add(note["note_id"], "shared_note", f"{note['note_id']} · status claim · {A.user_name(ctx.user_id)}")
    facts, flags = list(data["facts"]), list(data["flags"])
    me = A.user_name(ctx.user_id)
    conflicts = []
    for n in others:
        v = (store.get_shared_note(n["note_id"]) or {}).get("verdict") if n["source"] == "shared" else None
        if v and v.get("asserted") and v["asserted"] != verdict["asserted"]:
            conflicts.append(n)
    if verdict["matches"] is False:
        facts.append({"text": f"This does not match the records: {me}'s statement (\"{text}\") is recorded as {note['note_id']} and marked unconfirmed. Please confirm it, for example with a fresh reading or a note from someone on site.", "cites": [note["note_id"]]})
        flags.append({"type": "unconfirmed", "text": f"{note['note_id']} ({me}): \"{text}\" is unconfirmed; the latest inspection says otherwise.", "refs": [note["note_id"], verdict.get("inspection_id", aid)]})
    elif verdict["matches"]:
        facts.append({"text": f"This matches the latest inspection. {me}'s statement is recorded as {note['note_id']} for everyone.", "cites": [note["note_id"]]})
    else:
        facts.append({"text": f"{me}'s statement is recorded as {note['note_id']} but could not be checked.", "cites": [note["note_id"]]})
    for n in conflicts:
        cites.add(n["note_id"], "shared_note", f"{n['note_id']} · status claim · {A.user_name(n['author_user_id'])}")
        vv = store.get_shared_note(n["note_id"])["verdict"]
        side = "matches" if vv.get("matches") else "does not match"
        facts.append({"text": f"This conflicts with {n['note_id']} by {A.user_name(n['author_user_id'])} (\"{n['text']}\"), which {side} the latest inspection. Both statements are kept on record; neither was silently chosen.", "cites": [n["note_id"], note["note_id"]]})
        flags.append({"type": "conflict", "text": f"{note['note_id']} ({me}) and {n['note_id']} ({A.user_name(n['author_user_id'])}) disagree about {aid}.", "refs": [note["note_id"], n["note_id"]]})
    res = A.result("check_claim", f"Claim about {aid}", cites, entities={"wells": [aid]})
    res["facts"], res["flags"], res["visuals"] = facts, flags, {}
    res["data"] = {"asset_id": aid, "verdict": verdict, "claim_note": note["note_id"], "status": status}
    return res


def decide(A: Analyst, store, agent, user_id: str, action_id: str, confirm: bool) -> dict:
    """Confirm or cancel a pending proposal. Returns the assistant message to append to the chat."""
    act = store.get_pending(action_id)
    if not act:
        raise LookupError("That proposal no longer exists.")
    if act["user_id"] != user_id:
        raise PermissionError("Only the person who proposed this can confirm it.")
    if act["status"] != "pending":
        raise ValueError(f"This proposal was already {act['status']}.")
    if not confirm:
        store.resolve_pending(action_id, "cancelled")
        return {"cancelled": True}
    body = act["payload"]
    res = apply_action(A, store, user_id, act["kind"], body["payload"], body["preview"])
    store.resolve_pending(action_id, "confirmed")
    from .tools import Ctx
    ctx = Ctx(A, store, user_id, act["conv_id"])
    return agent._finish(ctx, "", 0, [res], [], None)
