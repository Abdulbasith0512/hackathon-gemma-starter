"""Answer verification: checks an answer against the dataset by independent recomputation, never against itself.

For every answer the copilot returns, `verify_answer` runs a set of deterministic checks:

  * the model's wording was grounded (no number, record ID or person that the tools did not return)
  * every citation resolves to a real record or document
  * every record ID written in the answer exists
  * the tool's headline numbers are recomputed from the raw tables (counts, totals, downtime days, production status against the
    manual's threshold, technician by joining users, gas-report deadlines against the SOP limits)
  * the question's own wording (pattern rules, not the model) points to the tool that was used

Status:  FAIL          a check contradicts the answer or its evidence;
         PASS          nothing failed, at least one numeric claim was recomputed independently, and the question pattern agrees with the tool used;
         NEEDS_REVIEW  nothing failed but correctness could not be established independently (no recomputation exists for the tool, the question is
                       ambiguous or unclassified, no records were consulted, or a change is awaiting confirmation).
PASS therefore means "the records and numbers shown are right", never "every possible claim was checked". Answers are never rewritten here.
"""

import re
from datetime import datetime

from . import evidence, router

_REC = re.compile(r"\b(?:WELL|INS|MNT|REG|CTX)-\d[\d-]*\b|\b(?:COR|SN)-\d{4}(?!\d)")      # saved corrections/notes are COR-0001 / SN-0001; a pump serial like SN-378851 is not one
_AMBIGUOUS = re.compile(r"\b(it|this|those|these|they|them)\b", re.I)      # not "that"/"there": "at that well" usually points back inside the same question
_REFUSAL = re.compile(r"^\s*I could not find an answer in the records\.?\s*$")


def _chunks(items, n=400):
    items = list(items)
    for k in range(0, len(items), n):
        yield items[k:k + n]


def _end(A, res):
    w = res.get("window") or {}
    return w.get("start"), min(w.get("end") or A.as_of_s, A.as_of_s)


def _scope_ids(A, args):
    return A.resolve_scope(args.get("scope"), args.get("well_type"))[0]


def _effective_rows(A, ids, start, end):
    """Inspections of the wells in a window with their effective readings: straight from SQL, and re-read through the correction layer
    only for the few inspections a correction touches."""
    corrected = set(A._dataset_corr) | set(A._corr) | set(A._override)
    rows = []
    for chunk in _chunks(ids):
        q = ("SELECT inspection_id, asset_id, inspected_date, wellhead_temp_c, ambient_temp_c, spill_detected, spill_est_volume_bbl FROM inspections "
             f"WHERE asset_id IN ({','.join('?' * len(chunk))}) AND inspected_date>=? AND inspected_date<=?")
        for r in A.c.execute(q, [*chunk, start, end]):
            d = dict(r)
            d["spill"] = bool(d["spill_detected"])
            if d["inspection_id"] in corrected:
                e = A.get_inspection(d["inspection_id"])
                d.update(wellhead_temp_c=e["wellhead_temp_c"], ambient_temp_c=e["ambient_temp_c"], spill=e["spill"], spill_est_volume_bbl=e["spill_est_volume_bbl"])
            rows.append(d)
    return rows


def _producing(A, row):
    """Production status from the manual's threshold for the well's type; None when a reading or the rule is missing."""
    wh, amb = row["wellhead_temp_c"], row["ambient_temp_c"]
    rule = A.threshold_for(A.wells[row["asset_id"]]["well_type"])
    if wh is None or amb is None or rule is None:
        return None
    return round(wh - amb, 6) >= rule.value - 1e-9


def _manual_threshold(A, well_type):
    """The temperature limit as written in the well-type manual (an independent read of the document text), or None."""
    r = A.c.execute("SELECT text FROM documents WHERE kind='manual' AND well_type=?", (well_type,)).fetchone()
    m = re.search(r"at least\s+(\d+(?:\.\d+)?)\s*°?\s*C\s+(?:above|warmer)", r["text"] if r else "", re.I)
    return float(m.group(1)) if m else None


# ---- recomputations: each returns a list of (outcome, detail) ------------------------------------------------------------------------------
def _re_well_status(A, res, args):
    d = res["data"]
    latest = A.c.execute("SELECT inspection_id FROM inspections WHERE asset_id=? AND inspected_date<=? ORDER BY inspected_at DESC LIMIT 1", (d["asset_id"], A.as_of_s)).fetchone()
    if not latest or latest["inspection_id"] != d["inspection_id"]:
        return [("fail", f"{d['asset_id']}: the latest inspection is {latest['inspection_id'] if latest else 'none'}, not {d['inspection_id']}")]
    row = _effective_rows(A, [d["asset_id"]], A.c.execute("SELECT inspected_date FROM inspections WHERE inspection_id=?", (d["inspection_id"],)).fetchone()[0], A.as_of_s)
    row = next(r for r in row if r["inspection_id"] == d["inspection_id"])
    out, wt = [], A.wells[d["asset_id"]]["well_type"]
    prod, delta = _producing(A, row), round(row["wellhead_temp_c"] - row["ambient_temp_c"], 6)
    if prod != d["producing"]:
        out.append(("fail", f"{d['asset_id']}: recomputed status is {'producing' if prod else 'not producing'} ({delta} °C above air), the answer says {'producing' if d['producing'] else 'not producing'}"))
    if abs(delta - (d["delta_c"] or 0)) > 0.051:
        out.append(("fail", f"{d['asset_id']}: recomputed {delta} °C above air, the answer says {d['delta_c']}"))
    man = _manual_threshold(A, wt)
    if man is not None and abs(man - d["threshold_c"]) > 1e-9:
        out.append(("fail", f"{wt}: the manual says {man} °C, the answer used {d['threshold_c']}"))
    return out or [("pass", f"{d['asset_id']}: {delta} °C above air against {d['threshold_c']} °C gives {'producing' if prod else 'not producing'}, as stated")]


def _down_days(A, ids, start, end):
    days = {a: 0 for a in ids}
    for r in _effective_rows(A, ids, start, end):
        if _producing(A, r) is False:
            days[r["asset_id"]] += 7
    return days


def _re_downtime(A, res, args):
    if "total_days" not in res["data"] or "by_group" in res["data"]:
        return []
    start, end = _end(A, res)
    days = _down_days(A, _scope_ids(A, args), start, end)
    got, want = res["data"]["total_days"], sum(days.values())
    return [("pass", f"downtime recomputed as {want} days (7 per weekly inspection found not producing)")] if got == want else \
           [("fail", f"downtime recomputed as {want} days, the answer says {got}")]


def _re_ranking(A, res, args):
    rank = res["data"].get("ranking")
    if not rank:
        return []
    start, end = _end(A, res)
    days = _down_days(A, _scope_ids(A, args), start, end)
    out = [("fail", f"{r['asset_id']}: recomputed {days.get(r['asset_id'])} downtime days, the answer says {r['days']}") for r in rank if days.get(r["asset_id"]) != r["days"]]
    others = [d for a, d in days.items() if a not in {r["asset_id"] for r in rank}]
    if others and rank and max(others) > min(r["days"] for r in rank):
        out.append(("fail", f"a well outside the ranking has {max(others)} downtime days, more than the lowest listed ({min(r['days'] for r in rank)})"))
    return out or [("pass", f"downtime of the {len(rank)} ranked wells recomputed, and no unlisted well exceeds them")]


def _real_spills(A, ids, start, end):
    return [r for r in _effective_rows(A, ids, start, end) if r["spill"]]


def _re_spills(A, res, args):
    start, end = _end(A, res)
    real = _real_spills(A, _scope_ids(A, args), start, end)
    n, vol = len(real), round(sum(r["spill_est_volume_bbl"] or 0 for r in real), 6)
    out = []
    if n != res["data"]["count"]:
        out.append(("fail", f"spills recounted as {n}, the answer says {res['data']['count']}"))
    if abs(vol - res["data"]["total_bbl"]) > 0.001:
        out.append(("fail", f"spill volume recomputed as {vol} bbl, the answer says {res['data']['total_bbl']}"))
    return out or [("pass", f"{n} spills totalling {vol} bbl recounted from the inspections")]


def _re_heatmap(A, res, args):
    start, end = _end(A, res)
    ids = _scope_ids(A, {"scope": args.get("scope")}) if args.get("scope") else list(A.wells)
    n = len(_real_spills(A, ids, start, end))
    return [("pass", f"heatmap grand total {n} recounted from the inspections")] if n == res["data"]["grand_total"] else \
           [("fail", f"heatmap spills recounted as {n}, the answer says {res['data']['grand_total']}")]


def _re_repairs(A, res, args):
    start, end = _end(A, res)
    ids = _scope_ids(A, args)
    eq = (args.get("equipment_kind") or "").strip().lower().replace(" ", "_") or None
    mt = (args.get("maintenance_type") or "").strip().lower() or None
    n, total = 0, 0.0
    for chunk in _chunks(ids):
        q = f"SELECT COUNT(*), COALESCE(SUM(cost_total),0) FROM maintenance WHERE asset_id IN ({','.join('?' * len(chunk))}) AND started_date>=? AND started_date<=?"
        p = [*chunk, start, end]
        for col, v in (("equipment_kind", eq), ("maintenance_type", mt)):
            if v:
                q += f" AND {col}=?"
                p.append(v)
        c, t = A.c.execute(q, p).fetchone()
        n, total = n + c, total + t
    d = res["data"]
    out = []
    if n != d["count"]:
        out.append(("fail", f"repairs recounted as {n}, the answer says {d['count']}"))
    if abs(total - d["total_usd"]) > 0.5:
        out.append(("fail", f"repair cost recomputed as {round(total, 2)} USD, the answer says {d['total_usd']}"))
    return out or [("pass", f"{n} repairs costing {round(total)} USD recounted from the maintenance table")]


def _re_technician(A, res, args):
    d = res["data"]
    r = A.c.execute("SELECT m.technician_user_id uid, u.name FROM maintenance m LEFT JOIN users u ON u.user_id=m.technician_user_id WHERE m.maintenance_id=?", (d["maintenance_id"],)).fetchone()
    if r is None:
        return [("fail", f"{d['maintenance_id']} is not in the maintenance table")]
    uid, name = (r["uid"] or None), ((r["name"] or "").strip() or None)
    if (uid, name) != (d["technician_user_id"], d["technician_name"]):
        return [("fail", f"{d['maintenance_id']}: the users join gives {uid}/{name}, the answer says {d['technician_user_id']}/{d['technician_name']}")]
    return [("pass", f"technician of {d['maintenance_id']} re-read by joining users: {name or 'not recorded'}")]


def _re_gas(A, res, args):
    d, out = res["data"], []
    ts = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
    cutoff = datetime.strptime(d["cutoff"], "%d %B %Y" if len(d["cutoff"].split()[1]) > 3 else "%d %b %Y").date()
    for row in res["visuals"]["table"]["rows"]:
        well, reported, resp, hours, verdict = row[0], row[2], row[3], row[4], row[6]
        note = A.c.execute("SELECT created_at FROM notes WHERE note_type='operator_note' AND asset_id=? AND substr(replace(created_at,'T',' '),1,16)||' UTC'=?", (well, reported)).fetchone()
        if note is None:
            out.append(("fail", f"{well}: no operator note at {reported}"))
            continue
        at, limit = ts(note["created_at"]), (d["limits_hours"]["before"] if ts(note["created_at"]).date() < cutoff else d["limits_hours"]["from"])
        if resp == "none":
            later = A.c.execute("SELECT 1 FROM maintenance WHERE asset_id=? AND started_at>? UNION SELECT 1 FROM inspections WHERE asset_id=? AND method='manual' AND inspected_at>? LIMIT 1",
                                (well, note["created_at"], well, note["created_at"])).fetchone()
            if later or verdict != "Missed":
                out.append(("fail", f"{well}: a response exists after {reported}" if later else f"{well}: no response but marked {verdict}"))
            continue
        rid = resp.split(" ")[0]
        r = A.c.execute("SELECT started_at t FROM maintenance WHERE maintenance_id=? UNION SELECT inspected_at FROM inspections WHERE inspection_id=? AND method='manual'", (rid, rid)).fetchone()
        if r is None:
            out.append(("fail", f"{well}: {rid} is not a maintenance job or a manual inspection"))
            continue
        h = (ts(r["t"]) - at).total_seconds() / 3600
        if h <= 0 or abs(h - hours) > 0.06 or (h <= limit + 1e-9) != (verdict == "Met"):
            out.append(("fail", f"{well}: response {rid} is {h:.1f} h after the note against a {limit} h limit, the table says {hours} h and {verdict}"))
    return out or [("pass", f"{len(res['visuals']['table']['rows'])} gas-report rows re-derived from the notes, jobs and inspections and the SOP limits")]


RECHECK = {"well_status": _re_well_status, "downtime": _re_downtime, "downtime_ranking": _re_ranking, "spills": _re_spills, "spill_heatmap": _re_heatmap,
           "repairs": _re_repairs, "maintenance_record": _re_technician, "gas_response": _re_gas}


def _citation_ok(A, ref: str) -> bool:
    """A citation is valid if it is a record, a saved correction/note/rule, or a section of a manual, SOP or repair report that exists."""
    if "#" in ref:
        doc, sec = ref.split("#", 1)
        return A.c.execute("SELECT 1 FROM sections WHERE substr(doc_id, instr(doc_id, ':') + 1)=? AND section_id=? LIMIT 1", (doc, sec)).fetchone() is not None
    return evidence.resolve(A, ref) is not None


def _exists(A, rid: str) -> bool:
    c = A.c
    if rid.startswith("WELL-"):
        return rid in A.wells
    table = {"INS-": ("inspections", "inspection_id"), "MNT-": ("maintenance", "maintenance_id"), "REG-": ("regulatory_events", "event_id"), "CTX-": ("notes", "note_id")}
    for pre, (t, col) in table.items():
        if rid.startswith(pre):
            return c.execute(f"SELECT 1 FROM {t} WHERE {col}=?", (rid,)).fetchone() is not None
    if rid.startswith("COR-") and A.store:
        return A.store.get_correction(rid) is not None
    if rid.startswith("SN-") and A.store:
        return A.store.get_shared_note(rid) is not None
    return True


def verify_answer(A, question: str, shown: str, ungrounded: list[str], results: list[dict], calls: list[dict], citations: list[dict], answer_source: str, withheld: str | None = None) -> dict:
    """Run every check and return {"status", "reasons", "checks"}. A failing check is reported, never repaired: the answer is left as it is."""
    checks = []

    def add(name, outcome, detail):
        checks.append({"check": name, "outcome": outcome, "detail": detail})

    ok = [(r, c) for r, c in zip(results, calls) if "error" not in r]
    if withheld:
        add("claims without records", "fail", withheld)
    if ungrounded:
        add("grounding", "fail", f"The model's wording contained values not found in the records ({', '.join(map(str, ungrounded[:6]))}); the verified facts were shown instead.")
    if not ok:
        add("records consulted", "review", "No records were consulted, so nothing in this answer was checked against the data." if not _REFUSAL.match(shown or "") else "The copilot gave no answer.")
    # citations and record IDs
    try:
        bad = [c["id"] for c in citations if not _citation_ok(A, c["id"])]
        add("citations", "fail" if bad else "pass", f"These citations do not resolve to any record or document: {', '.join(bad[:8])}." if bad else f"{len(citations)} citations all resolve")
        asked = set(_REC.findall(question or ""))
        missing = sorted(i for i in set(_REC.findall(shown or "")) if i not in asked and not _exists(A, i))
        add("record IDs", "fail" if missing else "pass", f"The answer names records that do not exist: {', '.join(missing[:8])}." if missing else "every record ID in the answer exists")
    except Exception as e:  # noqa: BLE001
        add("citations", "review", f"citation check could not run ({type(e).__name__}: {e})")
    # recomputation
    rechecked = 0
    for r, c in ok:
        fn = RECHECK.get(r.get("tool"))
        if fn is None:
            add(f"recompute {r.get('tool')}", "review", f"No independent recomputation exists for {r.get('tool')}, so its result is not verified here.")
            continue
        try:
            out = fn(A, r, c.get("args") or {})
        except Exception as e:  # noqa: BLE001
            add(f"recompute {r.get('tool')}", "review", f"The recomputation for {r.get('tool')} could not run ({type(e).__name__}: {e}).")
            continue
        for outcome, detail in out:
            add(f"recompute {r.get('tool')}", outcome, detail)
        rechecked += any(o == "pass" for o, _ in out)
        if r.get("pending"):
            add("confirmation", "review", "A change is waiting for the user's confirmation, so nothing has been applied or verified yet.")
    # does the question point to the tool that was used? (pattern rules, independent of the model)
    used = {r.get("tool") for r, _ in ok}
    if ok:
        try:
            exp = router.route(A, question, force=True)
        except Exception:  # noqa: BLE001
            exp = None
        if exp and exp[0][0] not in used:
            add("question vs tool", "review", f"The question's wording points to {exp[0][0]}, but the answer used {', '.join(sorted(t for t in used if t))}; that it answers what was asked is not established.")
        elif not exp:
            add("question vs tool", "review", "No independent rule classifies this question, so it cannot be confirmed that the tools used answer what was asked.")
        else:
            add("question vs tool", "pass", f"the question's wording points to {exp[0][0]}, which was used")
        if _AMBIGUOUS.search(question or "") and not _REC.search(question or "") and router.find_scope(A, question or "") is None:
            add("question clarity", "review", "The question refers to something by a pronoun without naming a well, area or record, so which records it means cannot be established from the question alone.")
    outcomes = [c["outcome"] for c in checks]
    if "fail" in outcomes:
        status = "FAIL"
    elif "review" in outcomes or not rechecked:
        status = "NEEDS_REVIEW"
        if not rechecked and "review" not in outcomes:
            add("recomputation", "review", "No number in this answer was recomputed independently.")
    else:
        status = "PASS"
    reasons = [c["detail"] for c in checks if c["outcome"] == ("fail" if status == "FAIL" else "review")] if status != "PASS" else []
    return {"status": status, "reasons": reasons, "checks": checks}
