"""Deterministic, cited calculations. This is the only code that does arithmetic.

Every public tool returns a JSON-serialisable dict:
  tool, title, data, facts [{text, cites}], flags [{type, text, refs}], citations [{id, kind, label}],
  visuals {kind: spec}, natural (the visual that fits), entities {wells: [...]}, window, as_of

All inspection reads go through `_eff`, the single place where corrections are applied, so a
saved correction changes every later answer for every user. Originals are always kept alongside.
"""

import re
import sqlite3
from datetime import date, datetime, timedelta

from . import periods
from .rules import Rules

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
REASON_WORDS = re.compile(r"shut[\s-]?in|shutdown|planned|workover|maintenance|repair|outage|offline|not producing|\bdown\b", re.I)
CORRECTABLE = {"wellhead_temp_c", "ambient_temp_c", "spill_est_volume_bbl", "spill_area_pct", "spill_detected"}
MAX_CITES = 400


class ToolError(Exception):
    """A user-facing problem with a tool request (unknown well, ambiguous area, bad period...)."""


def fmt_date(iso: str | None) -> str:
    if not iso:
        return "unknown date"
    d = date.fromisoformat(iso[:10])
    return f"{d.day} {MONTH_ABBR[d.month - 1]} {d.year}"


def fmt_num(x, nd: int = 1) -> str:
    if x is None:
        return "n/a"
    s = f"{x:.{nd}f}"
    return s.rstrip("0").rstrip(".") if "." in s and nd > 1 else s


def fmt_g(x) -> str:
    """41.0 -> '41', 7.1 -> '7.1' (hours, limits)."""
    return "n/a" if x is None else f"{x:g}"


def usd(x) -> str:
    return f"USD {x:,.0f}"


def _norm_tokens(text: str) -> set[str]:
    toks = re.sub(r"[^a-z0-9]+", " ", text.lower()).split()
    return {re.sub(r"^0+(?=\d)", "", t) for t in toks}


class Cites:
    def __init__(self):
        self.items: dict[str, dict] = {}

    def add(self, cid: str, kind: str, label: str) -> str:
        self.items.setdefault(cid, {"id": cid, "kind": kind, "label": label})
        return cid

    def list(self) -> list[dict]:
        return list(self.items.values())[:MAX_CITES]


class Analyst:
    def __init__(self, conn: sqlite3.Connection, rules: Rules, store, as_of: date):
        self.c, self.rules, self.store, self.as_of = conn, rules, store, as_of
        self.as_of_s = as_of.isoformat()
        self.wells = {r["asset_id"]: dict(r) for r in conn.execute("SELECT asset_id,name,well_type,area_id,team_id,in_charge_user_id,lat,lon,recorded_status FROM wells")}
        self.areas = {r["area_id"]: dict(r) for r in conn.execute("SELECT area_id,name,team_id,lat,lon FROM areas")}
        self.users = {r["user_id"]: dict(r) for r in conn.execute("SELECT user_id,name,role,team_id FROM users")}
        self.teams = {r["team_id"]: dict(r) for r in conn.execute("SELECT team_id,name,lead_user_id FROM teams")}
        for w in self.wells.values():  # an area that wells name but areas.json lacks still works (by its ID)
            if w["area_id"] and w["area_id"] not in self.areas:
                self.areas[w["area_id"]] = {"area_id": w["area_id"], "name": w["area_id"], "team_id": w["team_id"], "lat": None, "lon": None}
        self._corr = store.active_corrections() if store else {}
        self._override = {}
        for r in conn.execute("SELECT note_id, inspection_id, text, author_user_id, created_at FROM notes WHERE note_type='correction' AND inspection_id IS NOT NULL ORDER BY created_at"):
            self._override[r["inspection_id"]] = dict(r)
        row = conn.execute("SELECT MIN(inspected_date) m FROM inspections").fetchone()
        self.data_min = date.fromisoformat(row["m"]) if row and row["m"] else None

    # ---- names, scopes, periods -------------------------------------------------
    def user_name(self, uid: str | None) -> str:
        return self.users.get(uid or "", {}).get("name", uid or "unknown")

    def well(self, asset_id: str) -> dict:
        m = re.search(r"(?i)well[-\s]?0*(\d+)", asset_id or "")
        key = f"WELL-{int(m.group(1)):04d}" if m else (asset_id or "").strip().upper()
        if key not in self.wells:
            raise ToolError(f"Unknown well '{asset_id}'.")
        return self.wells[key]

    def resolve_scope(self, scope: str | list | None, well_type: str | None = None) -> tuple[list[str], str]:
        """A well, several wells, an area (by name or ID), a well type, or the whole field."""
        if isinstance(scope, list):
            ids = [self.well(s)["asset_id"] for s in scope]
            return ids, ", ".join(ids)
        text = re.sub(r"(?i)^the\s+", "", (scope or "").strip())
        ids: list[str]
        if not text or text.lower() in ("all", "fleet", "field", "everything", "all wells", "whole field", "entire field", "oil field", "all areas", "everywhere"):
            ids, label = list(self.wells), "the whole field"
        elif re.search(r"(?i)well[-\s]?0*\d+", text):
            found = re.findall(r"(?i)well[-\s]?0*(\d+)", text)
            ids = [self.well(f"WELL-{int(n):04d}")["asset_id"] for n in found]
            label = ", ".join(ids)
        elif re.fullmatch(r"(?i)t\d+\w*( wells)?", text):
            wt = text.split()[0].upper()
            ids = [a for a, w in self.wells.items() if w["well_type"] == wt]
            label = f"all {wt} wells"
            if not ids:
                raise ToolError(f"No wells of type '{wt}'.")
        else:
            toks = _norm_tokens(text)
            hits = []
            for a in self.areas.values():
                name_t, id_t = _norm_tokens(a["name"] or ""), _norm_tokens(a["area_id"])
                if toks and (toks <= name_t or toks == id_t or toks <= id_t):
                    hits.append(a)
            exact = [a for a in hits if _norm_tokens(a["name"] or "") == toks or _norm_tokens(a["area_id"]) == toks]
            hits = exact or hits
            team = [t for t in self.teams.values() if toks and (toks <= _norm_tokens(t["name"] or "") or toks == _norm_tokens(t["team_id"]))]
            if not hits and len(team) == 1:
                ids = [a for a, w in self.wells.items() if w["team_id"] == team[0]["team_id"]]
                if ids:
                    return ids, team[0]["name"]
            if not hits:
                names = ", ".join(f"{a['name']} ({a['area_id']})" for a in self.areas.values())
                raise ToolError(f"No area or well matches '{scope}'. Known areas: {names}.")
            if len(hits) > 1:
                raise ToolError(f"'{scope}' is ambiguous: " + ", ".join(a["name"] for a in hits) + ". Name the area in full.")
            ids = [a for a, w in self.wells.items() if w["area_id"] == hits[0]["area_id"]]
            label = hits[0]["name"]
        if well_type:
            ids = [a for a in ids if self.wells[a]["well_type"] == well_type.upper()]
            label += f" ({well_type.upper()} wells)"
        return ids, label

    def period(self, period: str | None, start: str | None = None, end: str | None = None, default: str | None = None) -> periods.Period:
        try:
            return periods.resolve_period(period or default, self.as_of, start, end, self.data_min)
        except ValueError as e:
            raise ToolError(str(e)) from e

    # ---- effective records ---------------------------------------------------
    def threshold_for(self, well_type: str):
        return self.rules.get("production_delta_c", well_type)

    def _eff(self, row: sqlite3.Row | dict) -> dict:
        d = dict(row)
        d.pop("raw", None)
        w = self.wells.get(d["asset_id"], {})
        d["well_type"] = w.get("well_type")
        d["orig"] = {f: d.get(f) for f in CORRECTABLE}
        d["orig"]["spill_detected"] = bool(d["orig"]["spill_detected"])
        d["corrections"] = []
        for f, c in self._corr.get(d["inspection_id"], {}).items():
            if f in CORRECTABLE:
                d[f] = c["new_value"]
                d["corrections"].append(c)
        d["spill"] = bool(d["spill_detected"])
        d["spill_override"] = None
        ov = self._override.get(d["inspection_id"])
        if ov and "spill_detected" not in {c["field"] for c in d["corrections"]}:
            d["spill"], d["spill_override"] = False, ov
        wh, amb = d.get("wellhead_temp_c"), d.get("ambient_temp_c")
        rule = self.threshold_for(d["well_type"]) if d["well_type"] else None
        d["threshold"], d["rule_ref"] = (rule.value, rule.ref) if rule else (None, None)
        d["delta"] = round(wh - amb, 6) if wh is not None and amb is not None else None
        d["producing"] = None if d["delta"] is None or rule is None else d["delta"] >= rule.value - 1e-9
        o_wh, o_amb = d["orig"]["wellhead_temp_c"], d["orig"]["ambient_temp_c"]
        d["orig_delta"] = round(o_wh - o_amb, 6) if o_wh is not None and o_amb is not None else None
        d["orig_producing"] = None if d["orig_delta"] is None or rule is None else d["orig_delta"] >= rule.value - 1e-9
        return d

    def inspections(self, asset_ids: list[str], start: str | None = None, end: str | None = None) -> list[dict]:
        if not asset_ids:
            return []
        q = f"SELECT * FROM inspections WHERE asset_id IN ({','.join('?' * len(asset_ids))})"
        params: list = list(asset_ids)
        if start:
            q += " AND inspected_date>=?"
            params.append(start)
        if end:
            q += " AND inspected_date<=?"
            params.append(end)
        q += " ORDER BY asset_id, inspected_at"
        return [self._eff(r) for r in self.c.execute(q, params)]

    def latest(self, asset_id: str) -> dict | None:
        r = self.c.execute("SELECT * FROM inspections WHERE asset_id=? AND inspected_date<=? ORDER BY inspected_at DESC LIMIT 1", (asset_id, self.as_of_s)).fetchone()
        return self._eff(r) if r else None

    def match_date(self, asset_id: str, date_s: str) -> str:
        """An inspection date for this well. If the exact date has none (typically a wrong year,
        as when "24 Sep" is sent as 2024-09-24), try the same day and month in the as-of year and the year before."""
        d = date.fromisoformat(date_s[:10])
        for year in (d.year, self.as_of.year, self.as_of.year - 1):
            try:
                cand = date(year, d.month, d.day)
            except ValueError:
                continue
            if cand <= self.as_of and self.c.execute("SELECT 1 FROM inspections WHERE asset_id=? AND inspected_date=?", (asset_id, cand.isoformat())).fetchone():
                return cand.isoformat()
        return d.isoformat()

    def get_inspection(self, inspection_id: str) -> dict | None:
        r = self.c.execute("SELECT * FROM inspections WHERE inspection_id=?", (inspection_id,)).fetchone()
        return self._eff(r) if r else None

    def maintenance(self, asset_ids: list[str], start: str | None = None, end: str | None = None) -> list[dict]:
        if not asset_ids:
            return []
        q = f"SELECT * FROM maintenance WHERE asset_id IN ({','.join('?' * len(asset_ids))})"
        params: list = list(asset_ids)
        if start:
            q += " AND started_date>=?"
            params.append(start)
        if end:
            q += " AND started_date<=?"
            params.append(end)
        return [dict(r) for r in self.c.execute(q + " ORDER BY asset_id, started_at", params)]

    # ---- citations -----------------------------------------------------------
    def c_ins(self, cites: Cites, i: dict) -> str:
        return cites.add(i["inspection_id"], "inspection", f"{i['inspection_id']} · {fmt_date(i['inspected_at'])} · {i['asset_id']}")

    def c_mnt(self, cites: Cites, m: dict) -> str:
        return cites.add(m["maintenance_id"], "maintenance", f"{m['maintenance_id']} · {m.get('equipment_kind') or 'repair'} · started {fmt_date(m['started_at'])}")

    def c_reg(self, cites: Cites, r: dict) -> str:
        return cites.add(r["event_id"], "regulatory", f"{r['event_id']} · {r['event_type']} · {fmt_date(r['date'])}")

    def c_note(self, cites: Cites, n: dict) -> str:
        return cites.add(n["note_id"], "note", f"{n['note_id']} · {n.get('note_type')} · {self.user_name(n.get('author_user_id'))}")

    def c_rule(self, cites: Cites, rule) -> str | None:
        if rule is None or rule.fallback:
            return None
        label = rule.ref
        if rule.doc_id and rule.doc_id.startswith("manual:"):
            row = self.c.execute("SELECT heading FROM sections WHERE doc_id=? AND section_id=? LIMIT 1", (rule.doc_id, rule.section_id)).fetchone()
            label = f"{rule.doc_id.split(':', 1)[1]} manual §{rule.section_id}" + (f" {row['heading']}" if row else "")
        elif rule.doc_id:
            label = f"{rule.doc_id.split(':', 1)[1]} · {rule.section_id}"
        return cites.add(rule.ref, "document", label)

    def c_cor(self, cites: Cites, c: dict) -> str:
        return cites.add(c["correction_id"], "correction", f"{c['correction_id']} · {c['field']} on {c['target_id']} · {self.user_name(c['author_user_id'])}")

    def c_well(self, cites: Cites, asset_id: str) -> str:
        w = self.wells[asset_id]
        return cites.add(asset_id, "well", f"{asset_id} · {w['name']} · {w['well_type']}")

    # ---- shared pieces ---------------------------------------------------------
    def notes_for(self, asset_id: str, on: str | None = None, types: tuple | None = None) -> list[dict]:
        """Dataset notes plus shared notes saved in chat; `on` keeps those valid on that date."""
        q = "SELECT * FROM notes WHERE asset_id=? AND note_type<>'correction'" + (f" AND note_type IN ({','.join('?' * len(types))})" if types else "") + " ORDER BY created_at"
        out = [dict(r, source="dataset") for r in self.c.execute(q, (asset_id, *(types or ())))]
        if self.store:
            for s in self.store.shared_notes_for(asset_id):
                out.append({"note_id": s["note_id"], "asset_id": asset_id, "created_at": s["created_at"], "author_user_id": s["author_user_id"],
                            "note_type": s["kind"], "text": s["text"], "valid_from": s["valid_from"], "valid_to": s["valid_to"],
                            "source": "shared", "status": s["status"]})
        if on:
            out = [n for n in out if (not n.get("valid_from") or n["valid_from"] <= on) and (not n.get("valid_to") or n["valid_to"] >= on)]
        return out

    def open_repairs(self, asset_id: str, at: str) -> list[dict]:
        rows = self.c.execute("SELECT * FROM maintenance WHERE asset_id=? AND started_at<=? AND completed_at>=? ORDER BY started_at", (asset_id, at, at)).fetchall()
        return [dict(r) for r in rows]

    def reasons(self, asset_id: str, ins: dict, cites: Cites) -> list[dict]:
        """Why a well is not producing: open repair, then an explanatory note, else 'no recorded reason'."""
        out = []
        for m in self.open_repairs(asset_id, ins["inspected_at"]):
            started = fmt_date(m["started_at"])
            still_open = m["completed_date"] > self.as_of_s
            out.append({"type": "repair", "ref": self.c_mnt(cites, m),
                        "text": f"Repair {m['maintenance_id']}: {m['issue']}, started {started}" + (", still open" if still_open else f", completed {fmt_date(m['completed_at'])}")})
        on = ins["inspected_date"]
        for n in self.notes_for(asset_id, on=max(on, self.as_of_s) if ins["inspected_date"] >= self.as_of_s else on):
            if REASON_WORDS.search(n["text"] or "") and n["note_type"] != "correction":
                ref = n["note_id"]
                cites.add(ref, "note" if n["source"] == "dataset" else "shared_note", f"{ref} · {n['note_type']} · {self.user_name(n['author_user_id'])}")
                out.append({"type": "note", "ref": ref, "text": f"Note {ref} by {self.user_name(n['author_user_id'])} ({fmt_date(n['created_at'])}): \"{n['text']}\"",
                            "status": n.get("status")})
        return out

    def reason_text(self, reasons: list[dict], ins: dict) -> str:
        if reasons:
            return "; ".join(r["text"] for r in reasons)
        base = "No recorded reason"
        return base + (f". The inspector noted \"{ins['notes']}\"" if ins.get("notes") else "")

    @staticmethod
    def gap_text(delta) -> str:
        if delta is None:
            return "no reading"
        return f"only {fmt_num(delta)} °C warmer" if delta >= 0 else f"{fmt_num(abs(delta))} °C cooler than the air"

    def result(self, tool: str, title: str, cites: Cites, **kw) -> dict:
        out = {"tool": tool, "title": title, "as_of": self.as_of_s, "facts": [], "flags": [], "visuals": {}, "natural": "table", "entities": {"wells": []}, "data": {}}
        out.update(kw)
        out["citations"] = cites.list()
        return out

    def correction_flags(self, ins: dict, cites: Cites) -> list[dict]:
        flags = []
        for c in ins.get("corrections", []):
            cid = self.c_cor(cites, c)
            flags.append({"type": "corrected", "refs": [cid, ins["inspection_id"]],
                          "text": f"{c['field']} on {ins['inspection_id']} was corrected from {c['original_value']} to {c['new_value']} by {self.user_name(c['author_user_id'])} ({fmt_date(c['created_at'])}): {c['reason']}"})
        return flags

    # ==== TOOLS ===================================================================
    def well_status(self, asset_id: str) -> dict:
        w = self.well(asset_id)
        aid = w["asset_id"]
        cites = Cites()
        ins = self.latest(aid)
        if not ins:
            raise ToolError(f"{aid} has no inspections on or before {fmt_date(self.as_of_s)}.")
        self.c_well(cites, aid)
        self.c_ins(cites, ins)
        rule = self.threshold_for(w["well_type"])
        rule_ref = self.c_rule(cites, rule)
        facts, flags = [], []
        who = self.user_name(ins["inspector_user_id"])
        if ins["producing"] is None:
            facts.append({"text": f"{aid} cannot be classified: " + ("no production-temperature rule was found for well type " + str(w["well_type"]) if rule is None else "the latest inspection has no temperature reading") + ".", "cites": [ins["inspection_id"]]})
            flags.append({"type": "missing_evidence", "text": "No rule or reading to derive production status.", "refs": [ins["inspection_id"]]})
        else:
            word = "is producing oil" if ins["producing"] else "is not producing oil"
            cmp_ = "at or above" if ins["producing"] else "below"
            facts.append({"text": f"{aid} {word}. At the latest inspection {ins['inspection_id']} the wellhead was {fmt_num(ins['delta'])} °C warmer than the air ({fmt_num(ins['wellhead_temp_c'])} °C vs {fmt_num(ins['ambient_temp_c'])} °C), {cmp_} the {w['well_type']} limit of {fmt_num(rule.value)} °C.",
                          "cites": [ins["inspection_id"], rule_ref] if rule_ref else [ins["inspection_id"]]})
        facts.append({"text": f"Latest inspection {ins['inspection_id']} on {fmt_date(ins['inspected_at'])} by {ins['method']}, by {who}.", "cites": [ins["inspection_id"]]})
        flags += self.correction_flags(ins, cites)
        if ins["corrections"] and ins.get("notes") and ins["producing"] != ins["orig_producing"]:
            facts.append({"text": f"The corrected value of {ins['inspection_id']} (by {self.user_name(ins['corrections'][0]['author_user_id'])}, original {fmt_num(ins['orig']['wellhead_temp_c'])} °C kept) disagrees with the inspector's note \"{ins['notes']}\" ({who}). Please confirm which is right.", "cites": [ins["inspection_id"]] + [c["correction_id"] for c in ins["corrections"]]})
            flags.append({"type": "conflict", "text": f"Corrected reading versus the inspection note \"{ins['notes']}\" ({who}).", "refs": [ins["inspection_id"]]})
        reasons = []
        if ins["producing"] is False:
            reasons = self.reasons(aid, ins, cites)
            if reasons:
                for r in reasons:
                    facts.append({"text": "Reason: " + r["text"] + ("." if not r["text"].endswith(".") else ""), "cites": [r["ref"]]})
            else:
                facts.append({"text": "No recorded reason explains the stop" + (f"; the inspector noted \"{ins['notes']}\"" if ins.get("notes") else "") + ". Suggest a field check.", "cites": [ins["inspection_id"]]})
                flags.append({"type": "missing_evidence", "text": "No repair or note explains why this well is not producing.", "refs": [ins["inspection_id"]]})
            for n in self.notes_for(aid, on=self.as_of_s):
                if "not yet in the maintenance system" in (n["text"] or "").lower() or "work order not yet" in (n["text"] or "").lower():
                    facts.append({"text": f"Note {n['note_id']} says the work order is not yet in the maintenance system.", "cites": [n["note_id"]]})
        rec = w["recorded_status"]
        stale = rec is not None and ins["producing"] is not None and ((rec == "active") != ins["producing"])
        if rec:
            facts.append({"text": f"The recorded status in the system is '{rec}'" + (", which is out of date; the inspections are the truth." if stale else "."), "cites": [aid]})
        if stale:
            flags.append({"type": "stale", "text": f"Recorded status '{rec}' disagrees with the latest inspection.", "refs": [aid]})
        card = {"kind": "status_card", "title": aid, "subtitle": f"{w['name']} · {w['well_type']} · {self.areas.get(w['area_id'], {}).get('name', w['area_id'])}",
                "status": {True: "producing", False: "not producing", None: "unknown"}[ins["producing"]],
                "metrics": [{"label": "Wellhead above air", "value": f"{fmt_num(ins['delta'])} °C", "note": f"needs ≥ {fmt_num(ins['threshold'])} °C"},
                            {"label": "Wellhead / air", "value": f"{fmt_num(ins['wellhead_temp_c'])} / {fmt_num(ins['ambient_temp_c'])} °C"},
                            {"label": "Last inspected", "value": fmt_date(ins["inspected_at"]), "note": f"{ins['method']} · {who}"},
                            {"label": "Recorded status", "value": rec or "n/a", "note": "out of date" if stale else ""}],
                "reasons": [r["text"] for r in reasons], "refs": [ins["inspection_id"]]}
        return self.result("well_status", f"Status of {aid}", cites, data={"asset_id": aid, "producing": ins["producing"], "delta_c": ins["delta"], "threshold_c": ins["threshold"],
                           "inspection_id": ins["inspection_id"], "inspected_at": ins["inspected_at"], "inspector": who, "method": ins["method"],
                           "recorded_status": rec, "recorded_status_stale": stale, "reasons": reasons}, facts=facts, flags=flags,
                           visuals={"status_card": card}, natural="status_card", entities={"wells": [aid]})

    def wells_not_producing(self, scope: str | None = None, well_type: str | None = None, state: str | None = None) -> dict:
        state = (state or "not_producing").lower().replace(" ", "_")
        ids, label = self.resolve_scope(scope, well_type)
        cites = Cites()
        rows, facts, flags, pins = [], [], [], []
        removed = []
        listed_other = []
        for aid in ids:
            ins = self.latest(aid)
            if ins and ins["producing"] is True and ins["orig_producing"] is False and ins["corrections"]:
                removed.append(ins)
            if state in ("producing", "all") and ins and ins["producing"] is not False:
                self.c_ins(cites, ins)
                listed_other.append([aid, f"{fmt_num(ins['delta'])} °C", "producing" if ins["producing"] else "unknown", self.wells[aid]["recorded_status"] or ""])
            if state == "producing" or not ins or ins["producing"] is not False:
                continue
            w = self.wells[aid]
            self.c_ins(cites, ins)
            reasons = self.reasons(aid, ins, cites)
            rec = w["recorded_status"]
            stale = rec is not None and ((rec == "active") != ins["producing"])
            rows.append([aid, f"{fmt_num(ins['delta'])} °C", f"{rec}{' (out of date)' if stale else ''}", self.reason_text(reasons, ins)])
            facts.append({"text": f"{aid} ({w['well_type']}): {fmt_num(ins['delta'])} °C above air on {fmt_date(ins['inspected_at'])}; recorded status {rec}{' (out of date)' if stale else ''}; {self.reason_text(reasons, ins)}.",
                          "cites": [ins["inspection_id"]] + [r["ref"] for r in reasons]})
            if not reasons:
                flags.append({"type": "missing_evidence", "text": f"{aid}: nothing in the records explains the stop; check the pad.", "refs": [ins["inspection_id"]]})
            flags += self.correction_flags(ins, cites)
            if w["lat"] is not None:
                pins.append({"lat": w["lat"], "lon": w["lon"], "label": aid, "ref": aid})
        head = f"{len(rows)} well(s) in {label} are not producing oil right now (latest inspection)."
        if state in ("producing", "all"):
            head = f"In {label}: {len(listed_other)} producing, {len(rows)} not producing (latest inspection, {len(ids)} well(s))."
            rows = ([[r[0], r[1], r[3], "producing"] for r in listed_other] if state == "producing" else rows + [[r[0], r[1], r[3], "producing"] for r in listed_other])
        facts.insert(0, {"text": head, "cites": []})
        for ins in removed:
            self.c_ins(cites, ins)
            cor_refs = [self.c_cor(cites, c) for c in ins["corrections"]]
            facts.append({"text": f"{ins['asset_id']} is no longer listed: its latest reading ({ins['inspection_id']}, {fmt_date(ins['inspected_at'])}) was corrected from {fmt_num(ins['orig']['wellhead_temp_c'])} °C to {fmt_num(ins['wellhead_temp_c'])} °C, which is {fmt_num(ins['delta'])} °C above the air (limit {fmt_num(ins['threshold'])} °C), so it counts as producing. The original value is kept.",
                          "cites": [ins["inspection_id"]] + cor_refs})
            flags += self.correction_flags(ins, cites)
            if ins.get("notes"):
                flags.append({"type": "conflict", "text": f"The same inspection notes \"{ins['notes']}\" ({self.user_name(ins['inspector_user_id'])}), which disagrees with the correction.", "refs": [ins["inspection_id"]]})
        return self.result("wells_not_producing", f"Wells not producing in {label}", cites, data={"scope": label, "count": len(rows)}, facts=facts, flags=flags,
                           visuals={"table": {"kind": "table", "columns": ["Well", "Wellhead above air", "Recorded status", "Reason"], "rows": rows}, "map": {"kind": "map", "points": pins}},
                           natural="table", entities={"wells": [r[0] for r in rows]})

    def inspection_series(self, asset_id: str, weeks: int = 13) -> dict:
        w = self.well(asset_id)
        aid = w["asset_id"]
        rows = self.c.execute("SELECT * FROM inspections WHERE asset_id=? AND inspected_date<=? ORDER BY inspected_at DESC LIMIT ?", (aid, self.as_of_s, int(weeks))).fetchall()
        pts = [self._eff(r) for r in reversed(rows)]
        cites = Cites()
        self.c_well(cites, aid)
        if not pts:
            raise ToolError(f"{aid} has no inspections.")
        down = [p for p in pts if p["producing"] is False]
        for p in pts:
            self.c_ins(cites, p)
        rule = self.threshold_for(w["well_type"])
        self.c_rule(cites, rule)
        facts = [{"text": f"{len(pts)} weekly readings for {aid} from {fmt_date(pts[0]['inspected_at'])} to {fmt_date(pts[-1]['inspected_at'])}.", "cites": [pts[0]["inspection_id"], pts[-1]["inspection_id"]]}]
        if down:
            facts.append({"text": "Not producing oil on " + ", ".join(f"{fmt_date(p['inspected_at'])} ({fmt_num(p['delta'])} °C above air, needs ≥ {fmt_num(p['threshold'])} °C)" for p in down) + ".", "cites": [p["inspection_id"] for p in down]})
        else:
            facts.append({"text": "The well was producing at every reading in this window.", "cites": []})
        flags = []
        for p in pts:
            flags += self.correction_flags(p, cites)
        line = {"kind": "line", "title": f"{aid} wellhead vs air temperature (°C)", "x": [p["inspected_date"] for p in pts],
                "series": [{"name": "Wellhead °C", "values": [p["wellhead_temp_c"] for p in pts]}, {"name": "Air °C", "values": [p["ambient_temp_c"] for p in pts]}],
                "markers": [{"index": i, "label": "Not producing", "ref": p["inspection_id"]} for i, p in enumerate(pts) if p["producing"] is False],
                "refs": [p["inspection_id"] for p in pts]}
        table = {"kind": "table", "columns": ["Date", "Inspection", "Wellhead °C", "Air °C", "Above air °C", "Producing"],
                 "rows": [[p["inspected_date"], p["inspection_id"], p["wellhead_temp_c"], p["ambient_temp_c"], fmt_num(p["delta"]), {True: "yes", False: "no", None: "unknown"}[p["producing"]]] for p in pts]}
        return self.result("inspection_series", f"{aid} temperature, last {len(pts)} weeks", cites, data={"asset_id": aid, "points": len(pts), "not_producing_dates": [p["inspected_date"] for p in down]},
                           facts=facts, flags=flags, visuals={"line": line, "table": table}, natural="line", entities={"wells": [aid]})

    def _spill_rows(self, ids: list[str], per: periods.Period):
        ins = self.inspections(ids, per.start.isoformat(), per.end.isoformat())
        real = [i for i in ins if i["spill"]]
        excluded = [i for i in ins if i["orig"]["spill_detected"] and not i["spill"]]
        return real, excluded

    def spills(self, scope: str | None = None, period: str | None = None, start: str | None = None, end: str | None = None, well_type: str | None = None) -> dict:
        ids, label = self.resolve_scope(scope, well_type)
        per = self.period(period, start, end, default="last 4 years")
        real, excluded = self._spill_rows(ids, per)
        cites = Cites()
        rows, pins, flags = [], [], []
        total, missing_vol = 0.0, 0
        for i in real:
            self.c_ins(cites, i)
            vol = i["spill_est_volume_bbl"]
            if vol is None:
                missing_vol += 1
            else:
                total += vol
            w = self.wells[i["asset_id"]]
            rows.append([i["inspected_date"], i["asset_id"], vol, i["spill_area_pct"], i["inspection_id"]])
            if w["lat"] is not None:
                pins.append({"lat": w["lat"], "lon": w["lon"], "label": f"{i['asset_id']} · {fmt_date(i['inspected_at'])}", "value": vol, "ref": i["inspection_id"], "asset_id": i["asset_id"], "date": i["inspected_date"]})
            flags += self.correction_flags(i, cites)
        facts = [{"text": f"{len(real)} oil spill(s) in {label}, {per.label}, totalling {fmt_num(round(total, 6))} bbl.", "cites": [i["inspection_id"] for i in real][:50]}]
        for i in real:
            facts.append({"text": f"{fmt_date(i['inspected_at'])}: {i['asset_id']}, {fmt_num(i['spill_est_volume_bbl'])} bbl ({i['inspection_id']}).", "cites": [i["inspection_id"]]})
        if excluded:
            for i in excluded:
                self.c_ins(cites, i)
                ov = i["spill_override"]
                ref = ov["note_id"] if ov else None
                if ref:
                    cites.add(ref, "note", f"{ref} · correction · {self.user_name(ov['author_user_id'])}")
                cor_refs = [self.c_cor(cites, c) for c in i["corrections"] if c["field"] == "spill_detected"]
                refs = ([ref] if ref else []) + cor_refs
                facts.append({"text": f"Not counted: {i['inspection_id']} ({fmt_date(i['inspected_at'])}, {i['asset_id']}) was detected as a spill but corrected" + (f" by note {ref}: \"{ov['text']}\"" if ov else "") + (f" by {', '.join(cor_refs)}" if cor_refs else "") + ".", "cites": [i["inspection_id"]] + refs})
                flags.append({"type": "corrected", "text": f"{i['inspection_id']} was detected as a spill but corrected, so it is excluded.", "refs": [i["inspection_id"]] + refs})
        if missing_vol:
            flags.append({"type": "missing_evidence", "text": f"{missing_vol} spill(s) have no volume estimate and are not in the total.", "refs": []})
        if per.assumption:
            facts.append({"text": per.assumption, "cites": []})
        wells_hit = sorted({i["asset_id"] for i in real})
        by_area: dict[str, int] = {}
        for i in real:
            nm = self.areas.get(self.wells[i["asset_id"]]["area_id"], {}).get("name", "?")
            by_area[nm] = by_area.get(nm, 0) + 1
        bar_spec = {"kind": "bar", "labels": [r[0] + " " + r[1] for r in rows], "values": [r[2] or 0 for r in rows], "unit": "bbl"}
        if len(by_area) > 1:
            facts.append({"text": "By area: " + "; ".join(f"{n} {c}" for n, c in sorted(by_area.items(), key=lambda kv: -kv[1])) + ".", "cites": []})
            bar_spec = {"kind": "bar", "title": "Spills by area", "labels": list(by_area), "values": list(by_area.values()), "unit": "spills"}
        return self.result("spills", f"Oil spills in {label}", cites, window=per.as_dict(),
                           data={"scope": label, "count": len(real), "total_bbl": round(total, 6), "excluded": [i["inspection_id"] for i in excluded]}, facts=facts, flags=flags,
                           visuals={"table": {"kind": "table", "columns": ["Date", "Well", "Volume (bbl)", "Pad area %", "Inspection"], "rows": rows},
                                    "map": {"kind": "map", "points": pins},
                                    "bar": bar_spec},
                           natural="table", entities={"wells": wells_hit[:25]})

    def _cause(self, asset_id: str, ins: dict, cites: Cites) -> dict | None:
        m = self.c.execute("SELECT * FROM maintenance WHERE triggered_by_inspection_id=? LIMIT 1", (ins["inspection_id"],)).fetchone()
        if m is None:
            m = self.c.execute("SELECT * FROM maintenance WHERE asset_id=? AND started_at<=? AND completed_at>=? ORDER BY started_at LIMIT 1", (asset_id, ins["inspected_at"], ins["inspected_at"])).fetchone()
        if m is not None:
            return {"ref": self.c_mnt(cites, dict(m)), "text": f"{m['issue']} ({m['maintenance_id']})"}
        for n in self.notes_for(asset_id, on=ins["inspected_date"]):
            if REASON_WORDS.search(n["text"] or ""):
                cites.add(n["note_id"], "note", f"{n['note_id']} · {n['note_type']}")
                return {"ref": n["note_id"], "text": f"note {n['note_id']}: {n['text']}"}
        return None

    def _downtime(self, ids: list[str], per: periods.Period) -> dict[str, dict]:
        ins = self.inspections(ids, per.start.isoformat(), per.end.isoformat())
        out = {a: {"asset_id": a, "down": [], "n": 0, "unknown": 0, "corrected": []} for a in ids}
        for i in ins:
            o = out[i["asset_id"]]
            o["n"] += 1
            if i["corrections"]:
                o["corrected"].append(i)
            if i["producing"] is False:
                o["down"].append(i)
            elif i["producing"] is None:
                o["unknown"] += 1
        for o in out.values():
            o["days"] = 7 * len(o["down"])
        return out

    def group_name(self, asset_id: str, group_by: str) -> str:
        w = self.wells[asset_id]
        return self.areas.get(w["area_id"], {}).get("name", w["area_id"]) if group_by == "area" else (w["well_type"] or "unknown")

    def downtime(self, scope: str, period: str | None = None, start: str | None = None, end: str | None = None, group_by: str | None = None) -> dict:
        ids, label = self.resolve_scope(scope)
        per = self.period(period, start, end, default="this year")
        cites = Cites()
        dt = self._downtime(ids, per)
        facts, flags, rows = [], [], []
        total = sum(o["days"] for o in dt.values())
        group_by = (group_by or "").lower().replace(" ", "_") or None
        if group_by in ("area", "well_type") and len(ids) > 1:
            groups: dict[str, dict] = {}
            for a, o in dt.items():
                g = groups.setdefault(self.group_name(a, group_by), {"days": 0, "wells": 0, "down_wells": 0})
                g["days"] += o["days"]
                g["wells"] += 1
                g["down_wells"] += 1 if o["days"] else 0
            ordered = sorted(groups.items(), key=lambda kv: (-kv[1]["days"], kv[0]))
            rows = [[n, g["days"], g["wells"], round(g["days"] / g["wells"], 1)] for n, g in ordered]
            for n, g in ordered:
                facts.append({"text": f"{n}: {g['days']} downtime days across {g['wells']} well(s) ({g['down_wells']} with downtime), {fmt_num(g['days'] / g['wells'])} days per well, in {per.label}.", "cites": []})
            facts.insert(0, {"text": f"Downtime by {group_by.replace('_', ' ')} for {label}, {per.label}: " + "; ".join(f"{n} {g['days']} days" for n, g in ordered) + ".", "cites": []})
            facts.append({"text": "Downtime counts each weekly inspection that found the well not producing oil as 7 days; missed inspections add none, and repair downtime_hours is not used.", "cites": []})
            bar = {"kind": "bar", "title": f"Downtime days by {group_by.replace('_', ' ')} · {per.label}", "labels": [r[0] for r in rows], "values": [r[1] for r in rows], "unit": "days"}
            return self.result("downtime", f"Downtime by {group_by.replace('_', ' ')}", cites, window=per.as_dict(), data={"scope": label, "total_days": total, "by_group": {r[0]: r[1] for r in rows}},
                               facts=facts, visuals={"bar": bar, "table": {"kind": "table", "columns": [group_by.replace("_", " ").title(), "Downtime days", "Wells", "Days per well"], "rows": rows}}, natural="bar", entities={"wells": []})
        if len(ids) == 1:
            o = dt[ids[0]]
            facts.append({"text": f"{ids[0]} was down {o['days']} days in {per.label}: {len(o['down'])} weekly inspection(s) found it not producing oil, counted as 7 days each.", "cites": [i["inspection_id"] for i in o["down"]]})
            for i in o["down"]:
                self.c_ins(cites, i)
                cause = self._cause(ids[0], i, cites)
                self.c_rule(cites, self.threshold_for(i["well_type"]))
                rows.append([i["inspected_date"], i["inspection_id"], fmt_num(i["wellhead_temp_c"]), fmt_num(i["ambient_temp_c"]), fmt_num(i["delta"]), cause["text"] if cause else "No recorded reason"])
                facts.append({"text": f"{fmt_date(i['inspected_at'])}: wellhead {fmt_num(i['wellhead_temp_c'])} °C, air {fmt_num(i['ambient_temp_c'])} °C, {self.gap_text(i['delta'])} (needs ≥ {fmt_num(i['threshold'])} °C). Cause: {cause['text'] if cause else 'no recorded reason'}.",
                              "cites": [i["inspection_id"]] + ([cause["ref"]] if cause else [])})
                flags += self.correction_flags(i, cites)
            if o["unknown"]:
                flags.append({"type": "missing_evidence", "text": f"{o['unknown']} inspection(s) could not be classified (missing reading or rule).", "refs": []})
        else:
            for a, o in sorted(dt.items(), key=lambda kv: (-kv[1]["days"], kv[0])):
                if o["days"]:
                    rows.append([a, o["days"], len(o["down"])])
            facts.append({"text": f"{label}: {total} downtime days in total across {sum(1 for o in dt.values() if o['days'])} well(s) in {per.label}.", "cites": []})
        seen_cor = {f["refs"][0] for f in flags if f["type"] == "corrected"}
        for o in dt.values():
            for i in o["corrected"]:
                for f in self.correction_flags(i, cites):
                    if f["refs"][0] not in seen_cor:
                        seen_cor.add(f["refs"][0])
                        flags.append(f)
        facts.append({"text": "Downtime counts each weekly inspection that found the well not producing oil as 7 days; missed inspections add none, and repair downtime_hours is not used.", "cites": []})
        cols = ["Date", "Inspection", "Wellhead °C", "Air °C", "Above air °C", "Cause"] if len(ids) == 1 else ["Well", "Downtime days", "Non-producing inspections"]
        return self.result("downtime", f"Downtime for {label}", cites, window=per.as_dict(), data={"scope": label, "total_days": total, "per_well": {a: o["days"] for a, o in dt.items() if o["days"]}},
                           facts=facts, flags=flags, visuals={"table": {"kind": "table", "columns": cols, "rows": rows}}, natural="table", entities={"wells": ids if len(ids) <= 25 else []})

    def downtime_ranking(self, scope: str | None = None, period: str | None = None, top_n: int = 3, start: str | None = None, end: str | None = None, well_type: str | None = None) -> dict:
        ids, label = self.resolve_scope(scope, well_type)
        per = self.period(period, start, end, default="last 4 months")
        top_n = max(1, int(top_n or 3))
        cites = Cites()
        dt = self._downtime(ids, per)
        ranked = sorted(dt.values(), key=lambda o: (-o["days"], o["asset_id"]))
        top = ranked[:top_n]
        nxt = ranked[top_n] if len(ranked) > top_n else None
        rows, facts, flags = [], [], []
        for rank, o in enumerate(top, 1):
            w = self.wells[o["asset_id"]]
            self.c_well(cites, o["asset_id"])
            for i in o["down"]:
                self.c_ins(cites, i)
            rows.append([rank, o["asset_id"], w["well_type"], o["days"], len(o["down"])])
            facts.append({"text": f"{o['asset_id']}: {o['days']} days down ({w['well_type']}), from {len(o['down'])} weekly inspections that found it not producing oil.", "cites": [o["asset_id"]]})
            for i in o["down"]:
                flags += self.correction_flags(i, cites)
        seen_cor = {f["refs"][0] for f in flags if f["type"] == "corrected"}
        for o in top:
            for i in o["corrected"]:
                for f in self.correction_flags(i, cites):
                    if f["refs"][0] not in seen_cor:
                        seen_cor.add(f["refs"][0])
                        flags.append(f)
        for w_type in {self.wells[o["asset_id"]]["well_type"] for o in top}:
            self.c_rule(cites, self.threshold_for(w_type))
        ties = {}
        for o in top:
            ties.setdefault(o["days"], []).append(o["asset_id"])
        for days, g in ties.items():
            if len(g) > 1:
                facts.append({"text": f"{' and '.join(g)} are tied at {days} days.", "cites": g})
        if nxt:
            facts.append({"text": f"The next well is {nxt['asset_id']} with {nxt['days']} days.", "cites": [nxt["asset_id"]]})
            self.c_well(cites, nxt["asset_id"])
        facts.insert(0, {"text": f"Top {len(top)} wells by downtime in {label}, {per.label} (each weekly inspection that found the well not producing oil counts as 7 days).", "cites": []})
        bar = {"kind": "bar", "title": f"Downtime days · {label} · {per.label}", "labels": [r[1] for r in rows], "values": [r[3] for r in rows], "unit": "days",
               "sub": [f"{r[2]}" for r in rows], "refs": [r[1] for r in rows]}
        return self.result("downtime_ranking", f"Downtime ranking, {label}", cites, window=per.as_dict(),
                           data={"scope": label, "ranking": [{"asset_id": o["asset_id"], "days": o["days"], "well_type": self.wells[o["asset_id"]]["well_type"]} for o in top], "next": {"asset_id": nxt["asset_id"], "days": nxt["days"]} if nxt else None},
                           facts=facts, flags=flags, visuals={"bar": bar, "table": {"kind": "table", "columns": ["Rank", "Well", "Type", "Downtime days", "Non-producing weeks"], "rows": rows}},
                           natural="bar", entities={"wells": [o["asset_id"] for o in top]})

    def repair_costs(self, wells: list | str | None = None, period: str | None = None, start: str | None = None, end: str | None = None, scope: str | None = None, top_n: int | None = None,
                     group_by: str | None = None) -> dict:
        target = wells if wells else scope
        ids, label = self.resolve_scope(target if not isinstance(target, str) or target else None) if target else self.resolve_scope(None)
        per = self.period(period, start, end, default="this year")
        cites = Cites()
        ms = self.maintenance(ids, per.start.isoformat(), per.end.isoformat())
        by: dict[str, dict] = {}
        for m in ms:
            b = by.setdefault(m["asset_id"], {"total": 0.0, "n": 0, "ids": []})
            b["total"] += m["cost_total"] or 0
            b["n"] += 1
            b["ids"].append(m["maintenance_id"])
            self.c_mnt(cites, m)
        rows, facts = [], []
        group_by = (group_by or "").lower().replace(" ", "_") or None
        if group_by in ("area", "well_type") and len(ids) > 1:
            groups: dict[str, dict] = {}
            for a in ids:
                g = groups.setdefault(self.group_name(a, group_by), {"total": 0.0, "n": 0, "wells": 0})
                b = by.get(a, {"total": 0.0, "n": 0})
                g["total"] += b["total"]
                g["n"] += b["n"]
                g["wells"] += 1
            ordered = sorted(groups.items(), key=lambda kv: (-kv[1]["total"], kv[0]))
            rows = [[n, round(g["total"]), g["n"], g["wells"]] for n, g in ordered]
            gtotal = sum(g["total"] for g in groups.values())
            facts = [{"text": f"Repair cost by {group_by.replace('_', ' ')} for {label}, {per.label}: " + "; ".join(f"{n} {usd(g['total'])}" for n, g in ordered) + f". Total {usd(gtotal)}.", "cites": []}]
            facts += [{"text": f"{n}: {usd(g['total'])} across {g['n']} repair(s) on {g['wells']} well(s).", "cites": []} for n, g in ordered]
            facts.append({"text": "A repair belongs to a period by its start date; cost is the total of labor and parts.", "cites": []})
            bar = {"kind": "bar", "title": f"Repair cost by {group_by.replace('_', ' ')} · {per.label}", "labels": [r[0] for r in rows], "values": [r[1] for r in rows], "unit": "USD"}
            return self.result("repair_costs", f"Repair costs by {group_by.replace('_', ' ')}", cites, window=per.as_dict(), data={"scope": label, "total_usd": gtotal, "by_group": {r[0]: r[1] for r in rows}},
                               facts=facts, visuals={"bar": bar, "table": {"kind": "table", "columns": [group_by.replace("_", " ").title(), "Repair cost (USD)", "Repairs", "Wells"], "rows": rows}}, natural="bar", entities={"wells": []})
        shown = ids
        if not wells and len(ids) > 10 or top_n:  # a big scope: rank the wells by cost and show the top N
            shown = sorted(ids, key=lambda a: (-by.get(a, {"total": 0})["total"], a))[: int(top_n or 10)]
            facts.append({"text": f"Top {len(shown)} of {len(ids)} well(s) by repair cost in {label}, {per.label}.", "cites": []})
        for a in shown:
            b = by.get(a, {"total": 0.0, "n": 0, "ids": []})
            rows.append([a, round(b["total"]), b["n"]])
            self.c_well(cites, a)
            facts.append({"text": f"{a}: {usd(b['total'])} across {b['n']} repair(s) started in {per.label}.", "cites": [a] + b["ids"][:3]})
        grand = sum(b["total"] for b in by.values())
        if len(ids) > 1 and shown is ids:
            facts.append({"text": f"Total for {label}: {usd(grand)}.", "cites": []})
        elif len(ids) > 1:
            facts.append({"text": f"Total for all {len(ids)} well(s) in {label}: {usd(grand)}.", "cites": []})
        facts.append({"text": "A repair belongs to a period by its start date; cost is the total of labor and parts.", "cites": []})
        return self.result("repair_costs", f"Repair costs, {label}", cites, window=per.as_dict(), data={"scope": label, "total_usd": grand, "per_well": {r[0]: r[1] for r in rows}},
                           facts=facts, visuals={"table": {"kind": "table", "columns": ["Well", "Repair cost (USD)", "Repairs"], "rows": rows},
                                                 "bar": {"kind": "bar", "labels": [r[0] for r in rows], "values": [r[1] for r in rows], "unit": "USD", "refs": [r[0] for r in rows]}},
                           natural="table", entities={"wells": shown if len(shown) <= 25 else []})

    def spill_heatmap(self, period: str | None = None, scope: str | None = None, start: str | None = None, end: str | None = None) -> dict:
        ids, label = self.resolve_scope(scope)
        per = self.period(period, start, end, default="this year")
        real, excluded = self._spill_rows(ids, per)
        cites = Cites()
        months, y, m = [], per.start.year, per.start.month
        while (y, m) <= (per.end.year, per.end.month):
            months.append((y, m))
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        area_ids = sorted({self.wells[a]["area_id"] for a in ids})
        grid = {a: {mo: [] for mo in months} for a in area_ids}
        for i in real:
            d = date.fromisoformat(i["inspected_date"])
            grid[self.wells[i["asset_id"]]["area_id"]][(d.year, d.month)].append(i["inspection_id"])
            self.c_ins(cites, i)
        multi_year = len({y for y, _ in months}) > 1
        cols = [MONTH_ABBR[mo - 1] + (f" {yy}" if multi_year else "") for yy, mo in months]
        values = [[len(grid[a][mo]) for mo in months] for a in area_ids]
        rows = [[self.areas[a]["name"]] + v + [sum(v)] for a, v in zip(area_ids, values)]
        row_totals = [sum(v) for v in values]
        col_totals = [sum(values[r][c] for r in range(len(area_ids))) for c in range(len(months))]
        grand_total = sum(row_totals)
        facts = [{"text": f"Spills by area and month, {per.label}: " + "; ".join(f"{r[0]} {r[-1]}" for r in rows) + ". Corrected detections are not counted.", "cites": []},
                 {"text": f"Total across all areas: {grand_total} spills (the sum of the area totals: " + " + ".join(str(t) for t in row_totals) + ").", "cites": []}]
        # Detections that were removed, grouped by the cell they would have been in, with the reason.
        excluded_cells = [[[] for _ in months] for _ in area_ids]
        for i in excluded:
            self.c_ins(cites, i)
            d = date.fromisoformat(i["inspected_date"])
            ov = i["spill_override"]
            refs, why = [], []
            if ov:
                cites.add(ov["note_id"], "note", f"{ov['note_id']} · correction · {self.user_name(ov['author_user_id'])}")
                refs.append(ov["note_id"])
                why.append(f"correction note {ov['note_id']} by {self.user_name(ov['author_user_id'])}: \"{ov['text']}\"")
            for c in (c for c in i["corrections"] if c["field"] == "spill_detected"):
                refs.append(self.c_cor(cites, c))
                why.append(f"correction {c['correction_id']} by {self.user_name(c['author_user_id'])}: {c['reason']}")
            excluded_cells[area_ids.index(self.wells[i["asset_id"]]["area_id"])][months.index((d.year, d.month))].append(
                {"inspection_id": i["inspection_id"], "asset_id": i["asset_id"], "reason": "; ".join(why) or "marked as not a spill", "refs": refs})
        if excluded:
            facts.append({"text": f"{len(excluded)} detection(s) were removed because a correction says they were not crude spills.", "cites": [i["inspection_id"] for i in excluded][:30]})
        lineage = {
            "calculation": "Each cell counts inspections whose effective spill flag is true, grouped by the well's area and by the month of the inspection date. "
                           "An area total is the sum of its monthly cells, a month total is the sum over areas, and the grand total is the sum of the area totals.",
            "filters": [["Period", f"{per.label} (inspection date, both ends included)"], ["Scope", label], ["As-of date", self.as_of_s],
                        ["Counted as a spill", "the dataset's spill detection, unless a correction says it was not a crude spill"],
                        ["Values used", "dataset records with active corrections applied; originals are kept"], ["Grouping", "area = the well's area ID; month = calendar month of the inspection date (UTC)"]],
            "row_totals": row_totals, "col_totals": col_totals, "grand_total": grand_total, "excluded_total": len(excluded), "excluded_cells": excluded_cells,
            "source_table": "inspections (loaded from assets/<well>/inspections.jsonl; each record lists its file and line)",
        }
        heat = {"kind": "heatmap", "title": f"Spills by area and month · {per.label}", "rows": [self.areas[a]["name"] for a in area_ids], "cols": cols, "values": values,
                "cells": [[grid[a][mo] for mo in months] for a in area_ids], "lineage": lineage}
        return self.result("spill_heatmap", "Spills by area and month", cites, window=per.as_dict(),
                           data={"matrix": {r[0]: r[1:-1] for r in rows}, "totals": {r[0]: r[-1] for r in rows}, "grand_total": grand_total, "excluded_total": len(excluded)},
                           facts=facts, visuals={"heatmap": heat, "table": {"kind": "table", "columns": ["Area"] + cols + ["Total"], "rows": rows}}, natural="heatmap",
                           entities={"areas": area_ids, "wells": []})

    def lineage_rows(self, inspection_ids: list[str]) -> list[dict]:
        """The source records behind a number: effective and original values, source file and line, and corrections."""
        ids = [i for i in dict.fromkeys(inspection_ids) if i][:500]
        if not ids:
            return []
        out = []
        for r in self.c.execute(f"SELECT * FROM inspections WHERE inspection_id IN ({','.join('?' * len(ids))}) ORDER BY inspected_at, inspection_id", ids):
            i = self._eff(r)
            note = None
            if i["spill_override"]:
                n = self.c.execute("SELECT note_id, text, source FROM notes WHERE note_id=?", (i["spill_override"]["note_id"],)).fetchone()
                note = {"note_id": i["spill_override"]["note_id"], "text": i["spill_override"]["text"], "author": self.user_name(i["spill_override"]["author_user_id"]), "source": f"assets/{n['source']}" if n else None}
            out.append({
                "inspection_id": i["inspection_id"], "asset_id": i["asset_id"], "area": self.areas.get(self.wells[i["asset_id"]]["area_id"], {}).get("name"),
                "inspected_at": i["inspected_at"], "counted_as_spill": bool(i["spill"]), "dataset_flag": bool(i["orig"]["spill_detected"]),
                "volume_bbl": i["spill_est_volume_bbl"], "original_volume_bbl": i["orig"]["spill_est_volume_bbl"], "pad_area_pct": i["spill_area_pct"],
                "source": f"assets/{r['source']}", "dataset_correction_note": note,
                "corrections": [{"id": c["correction_id"], "field": c["field"], "original": c["original_value"], "new": c["new_value"], "by": self.user_name(c["author_user_id"]),
                                 "why": c["reason"], "when": c["created_at"]} for c in i["corrections"]],
            })
        return out

    def rca_rule(self, w: dict, equipment_kind: str) -> dict | None:
        sr = self.store.scoped_rule("rca_corrective_count", w["well_type"], w["asset_id"], equipment_kind) if self.store else None
        window = self.rules.value("rca_window_months", w["well_type"], 12)
        if sr:
            return {"threshold": sr["value"], "kind": "user_rule", "ref": sr["rule_id"], "author": sr["author_user_id"], "window": window, "scope": f"{sr['scope_type']} {sr['scope_value']}"}
        r = self.rules.get("rca_corrective_count", w["well_type"])
        return {"threshold": r.value, "kind": "manual", "ref": r.ref, "window": window, "rule": r} if r else None

    def rca_candidates(self, scope: str | None = None, equipment_kind: str = "pump_jack", months: int | None = None) -> dict:
        ids, label = self.resolve_scope(scope)
        eq = (equipment_kind or "pump_jack").lower().replace(" ", "_")
        cites = Cites()
        rows, facts, flags, hits, used = [], [], [], [], {}
        for a in ids:
            w = self.wells[a]
            rule = self.rca_rule(w, eq)
            if not rule:
                continue
            win = int(months or rule["window"])
            start = periods.add_months(self.as_of, -win).isoformat()
            ms = [m for m in self.maintenance([a], start, self.as_of_s) if m["maintenance_type"] == "corrective" and m["equipment_kind"] == eq]
            used[(w["well_type"], rule["ref"])] = rule
            if len(ms) >= rule["threshold"]:
                hits.append(a)
                for m in ms:
                    self.c_mnt(cites, m)
                src = (f"{self.user_name(rule['author'])}'s rule {rule['ref']}" if rule["kind"] == "user_rule" else f"{w['well_type']} manual")
                rows.append([a, w["well_type"], len(ms), int(rule["threshold"]), src])
                facts.append({"text": f"{a} ({w['well_type']}): {len(ms)} corrective {eq.replace('_', ' ')} repairs in the last {win} months (threshold {int(rule['threshold'])}, {src}): " + ", ".join(m["maintenance_id"] for m in ms) + ".",
                              "cites": [m["maintenance_id"] for m in ms] + [rule["ref"]]})
        for (wt, ref), rule in used.items():
            if rule["kind"] == "user_rule":
                sr = self.store.scoped_rule("rca_corrective_count", wt, None, eq) or {}
                cites.add(ref, "rule", f"{ref} · {sr.get('scope_type', '')} {sr.get('scope_value', '')} · {self.user_name(sr.get('author_user_id'))}")
                facts.append({"text": f"For {wt} wells this follows {self.user_name(rule['author'])}'s rule {ref} ({int(rule['threshold'])} repairs), not the manual's {int(self.rules.value('rca_corrective_count', wt, 3))}.", "cites": [ref]})
                flags.append({"type": "rule", "text": f"{wt} threshold comes from a user rule ({ref}), not the manual.", "refs": [ref]})
            else:
                self.c_rule(cites, rule.get("rule"))
        facts.insert(0, {"text": f"{len(hits)} well(s) in {label} need a root-cause analysis on the {eq.replace('_', ' ')}: {', '.join(hits) if hits else 'none'}.", "cites": []})
        return self.result("rca_candidates", f"Root-cause analysis candidates ({eq.replace('_', ' ')})", cites, data={"scope": label, "wells": hits}, facts=facts, flags=flags,
                           visuals={"table": {"kind": "table", "columns": ["Well", "Type", "Corrective repairs", "Threshold", "Rule source"], "rows": rows}}, natural="table", entities={"wells": hits})

    def well_context(self, asset_id: str) -> dict:
        w = self.well(asset_id)
        aid = w["asset_id"]
        cites = Cites()
        self.c_well(cites, aid)
        facts, flags = [], []
        ins = self.latest(aid)
        valid = self.notes_for(aid, on=self.as_of_s)
        planned = [n for n in valid if n["source"] == "shared" or REASON_WORDS.search(n["text"] or "")]
        for n in valid:
            ref = n["note_id"]
            cites.add(ref, "shared_note" if n["source"] == "shared" else "note", f"{ref} · {n['note_type']} · {self.user_name(n['author_user_id'])}")
            span = f"valid {fmt_date(n['valid_from'])}" + (f" to {fmt_date(n['valid_to'])}" if n.get("valid_to") else " onward") if n.get("valid_from") else "no validity dates"
            facts.append({"text": f"{n['note_type']} {ref} by {self.user_name(n['author_user_id'])} ({span}): \"{n['text']}\"" + (f" [status: {n['status']}]" if n.get("status") and n["status"] != "recorded" else ""), "cites": [ref]})
            if n.get("status") in ("unconfirmed", "contradicted"):
                flags.append({"type": "unconfirmed", "text": f"{ref} is {n['status']}.", "refs": [ref]})
        future = [n for n in self.notes_for(aid) if n.get("valid_from") and n["valid_from"] > self.as_of_s]
        for n in future:
            ref = n["note_id"]
            cites.add(ref, "shared_note" if n["source"] == "shared" else "note", f"{ref} · {n['note_type']} · {self.user_name(n['author_user_id'])}")
            facts.append({"text": f"Upcoming: {n['note_type']} {ref} by {self.user_name(n['author_user_id'])}, from {fmt_date(n['valid_from'])}" + (f" to {fmt_date(n['valid_to'])}" if n.get("valid_to") else "") + f": \"{n['text']}\"", "cites": [ref]})
        if ins:
            self.c_ins(cites, ins)
            for m in self.open_repairs(aid, ins["inspected_at"]):
                facts.append({"text": f"Open repair {m['maintenance_id']}: {m['issue']}, started {fmt_date(m['started_at'])}, planned end {fmt_date(m['completed_at'])}.", "cites": [self.c_mnt(cites, m)]})
        if not valid and not future:
            facts.append({"text": f"No notes or planned downtime are recorded for {aid}.", "cites": []})
            flags.append({"type": "missing_evidence", "text": f"No notes found for {aid}.", "refs": []})
        return self.result("well_context", f"Notes and planned work for {aid}", cites, data={"asset_id": aid, "planned": [n["note_id"] for n in planned] + [n["note_id"] for n in future]}, facts=facts, flags=flags,
                           visuals={"table": {"kind": "table", "columns": ["Note", "Type", "Author", "Valid from", "Valid to", "Text"],
                                              "rows": [[n["note_id"], n["note_type"], self.user_name(n["author_user_id"]), n.get("valid_from") or "", n.get("valid_to") or "", n["text"]] for n in valid + future]}},
                           natural="table", entities={"wells": [aid]})

    def search_documents(self, query: str, kind: str | None = None, limit: int = 5) -> dict:
        words = re.findall(r"[A-Za-z0-9\-]+", query or "")
        if not words:
            raise ToolError("Give some words to search for.")
        match = " OR ".join(f'"{w}"' for w in words[:12])
        sql = ("SELECT s.doc_id, s.section_id, s.heading, snippet(sections_fts, 1, '[', ']', ' … ', 24) AS snip, d.kind, d.title FROM sections_fts "
               "JOIN sections s ON s.rowid = sections_fts.rowid JOIN documents d ON d.doc_id = s.doc_id WHERE sections_fts MATCH ?")
        params: list = [match]
        if kind:
            sql += " AND d.kind=?"
            params.append(kind)
        sql += " ORDER BY bm25(sections_fts) LIMIT ?"
        params.append(int(limit))
        cites, facts, rows = Cites(), [], []
        for r in self.c.execute(sql, params):
            ref = r["section_id"] if r["kind"] == "sop" and re.fullmatch(r"[A-Z]{2,3}-\d{2}", r["section_id"]) else f"{r['doc_id'].split(':', 1)[1]}#{r['section_id']}"
            cites.add(ref, "document", f"{r['title']} · {r['heading']}")
            facts.append({"text": f"{r['title']} §{r['section_id']} {r['heading']}: {r['snip']}", "cites": [ref]})
            rows.append([ref, r["title"], r["heading"], r["snip"]])
        if not facts:
            facts.append({"text": "No matching passage was found in the manuals, SOPs or reports.", "cites": []})
        return self.result("search_documents", f"Documents matching '{query}'", cites, facts=facts, flags=[] if rows else [{"type": "missing_evidence", "text": "Nothing found.", "refs": []}],
                           visuals={"table": {"kind": "table", "columns": ["Ref", "Document", "Section", "Passage"], "rows": rows}}, natural="table")

    # ==== compliance, spill evidence, claims ======================================
    def spill_class(self, volume) -> str | None:
        if volume is None:
            return None
        v = self.rules.value
        if volume >= v("spill.major_min_bbl", default=25.0):
            return "major"
        if volume >= v("spill.reportable_min_bbl", default=5.0):
            return "reportable"
        if volume >= v("spill.moderate_min_bbl", default=1.0):
            return "moderate"
        return "minor"

    def events_for(self, inspection_id: str) -> list[dict]:
        return [dict(r) for r in self.c.execute("SELECT * FROM regulatory_events WHERE related_inspection_id=? ORDER BY date, event_id", (inspection_id,))]

    def notes_about(self, inspection_id: str) -> list[dict]:
        """Notes that name this inspection: formal corrections (inspection_id set) and informal notes that quote its ID."""
        out = [dict(r, source="dataset") for r in self.c.execute("SELECT * FROM notes WHERE inspection_id=? OR text LIKE ? ORDER BY created_at", (inspection_id, f"%{inspection_id}%"))]
        if self.store:
            ins = self.c.execute("SELECT asset_id FROM inspections WHERE inspection_id=?", (inspection_id,)).fetchone()
            for s in self.store.shared_notes_for(ins["asset_id"]) if ins else []:
                if inspection_id in (s["text"] or ""):
                    out.append({"note_id": s["note_id"], "asset_id": s["asset_id"], "created_at": s["created_at"], "author_user_id": s["author_user_id"], "note_type": s["kind"],
                                "text": s["text"], "inspection_id": None, "source": "shared", "status": s["status"]})
        return out

    def _report_for(self, inspection_id: str) -> dict | None:
        m = self.c.execute("SELECT m.*, f.containment_hours, f.containment_quote, f.spill_class AS report_class, f.action_required FROM maintenance m "
                           "LEFT JOIN report_facts f ON f.maintenance_id=m.maintenance_id WHERE m.triggered_by_inspection_id=? ORDER BY m.started_at LIMIT 1", (inspection_id,)).fetchone()
        return dict(m) if m else None

    def spill_evidence(self, asset_id: str, date: str | None = None, inspection_id: str | None = None) -> dict:
        """Everything on record about one spill detection: the detection, formal corrections, informal notes, the repair."""
        w = self.well(asset_id)
        aid = w["asset_id"]
        if inspection_id:
            ins = self.get_inspection(inspection_id)
        else:
            date = self.match_date(aid, date) if date else date
            rows = [self._eff(r) for r in self.c.execute("SELECT * FROM inspections WHERE asset_id=? AND spill_detected=1 AND inspected_date<=? ORDER BY inspected_at DESC", (aid, self.as_of_s))]
            ins = next((r for r in rows if date and r["inspected_date"] == date[:10]), None) if date else (rows[0] if rows else None)
            if ins is None and rows:
                raise ToolError(f"{aid} has no spill detection on {date}. Detections: " + ", ".join(r["inspected_date"] for r in rows[:10]) + ".")
        if not ins or not (ins["orig"]["spill_detected"]):
            raise ToolError(f"No spill detection found for {aid}" + (f" on {date}" if date else "") + ".")
        cites = Cites()
        self.c_well(cites, aid)
        self.c_ins(cites, ins)
        facts, flags = [], []
        facts.append({"text": f"The AI analysis of inspection {ins['inspection_id']} ({fmt_date(ins['inspected_at'])}, {aid}) flagged a spill of {fmt_num(ins['orig']['spill_est_volume_bbl'])} bbl covering {fmt_num(ins['orig']['spill_area_pct'])}% of the pad" + (f"; the inspector noted \"{ins['notes']}\"" if ins.get("notes") else "") + ".", "cites": [ins["inspection_id"]]})
        formal = ins["spill_override"] is not None or any(c["field"] == "spill_detected" for c in ins["corrections"])
        notes = [n for n in self.notes_about(ins["inspection_id"]) if n["note_type"] != "correction"]
        if ins["spill_override"]:
            ov = ins["spill_override"]
            cites.add(ov["note_id"], "note", f"{ov['note_id']} · correction · {self.user_name(ov['author_user_id'])}")
            facts.append({"text": f"A formal correction ({ov['note_id']} by {self.user_name(ov['author_user_id'])}) says this was not a crude spill: \"{ov['text']}\" The detection does not stand.", "cites": [ov["note_id"]]})
        rows = []
        for n in notes:
            ref = n["note_id"]
            cites.add(ref, "shared_note" if n["source"] == "shared" else "note", f"{ref} · {n['note_type']} · {self.user_name(n['author_user_id'])}")
            role = (self.users.get(n["author_user_id"], {}).get("role") or "").replace("_", " ")
            facts.append({"text": f"Note {ref} by {self.user_name(n['author_user_id'])}{f' ({role})' if role else ''}, {fmt_date(n['created_at'])}: \"{n['text']}\"", "cites": [ref]})
            rows.append([ref, self.user_name(n["author_user_id"]), role, n["note_type"], n["text"]])
        if len(notes) >= 2:
            flags.append({"type": "conflict", "text": f"{len(notes)} informal notes about {ins['inspection_id']} by different people; read them side by side, none is a formal correction.", "refs": [n["note_id"] for n in notes]})
        rep = self._report_for(ins["inspection_id"])
        if rep:
            self.c_mnt(cites, rep)
            facts.append({"text": f"A spill repair {rep['maintenance_id']} ({rep['issue']}) was carried out on {fmt_date(rep['started_at'])}.", "cites": [rep["maintenance_id"]]})
            if rep.get("report_file"):
                cites.add(f"report:{rep['maintenance_id']}", "report", f"Repair report {rep['maintenance_id']}")
        if not formal:
            facts.append({"text": "Neither note is a formal correction" + (", and a spill repair was done" if rep else "") + f", so the detection stands: this counts as a real spill of {fmt_num(ins['spill_est_volume_bbl'])} bbl." if notes else f"No formal correction exists, so the detection stands: a real spill of {fmt_num(ins['spill_est_volume_bbl'])} bbl.", "cites": [ins["inspection_id"]]})
        flags += self.correction_flags(ins, cites)
        return self.result("spill_evidence", f"Spill evidence for {ins['inspection_id']}", cites, data={"inspection_id": ins["inspection_id"], "detection_stands": not formal, "notes": [n["note_id"] for n in notes]},
                           facts=facts, flags=flags, visuals={"table": {"kind": "table", "columns": ["Note", "Author", "Role", "Type", "Text"], "rows": rows}}, natural="table", entities={"wells": [aid]})

    def compliance_audit(self, scope: str | None = None, period: str | None = None, protocol: str | None = None, start: str | None = None, end: str | None = None, extras: bool = True) -> dict:
        """Spill protocols SR-01..SR-03 and RC-04 per spill, plus (for one well) RC-02, root-cause analysis and unrecorded shut-ins."""
        ids, label = self.resolve_scope(scope)
        per = self.period(period, start, end, default="last 12 months")
        only = (protocol or "").upper() or None
        cites = Cites()
        real, _excl = self._spill_rows(ids, per)
        end_of_as_of = datetime.fromisoformat(self.as_of_s + "T23:59:59+00:00")
        rows, facts, flags, breaches, pending_items = [], [], [], [], []
        fines_open = 0.0
        reportable_n = 0
        r_ = self.rules.value
        for i in real:
            self.c_ins(cites, i)
            vol = i["spill_est_volume_bbl"]
            cls = self.spill_class(vol)
            disc = datetime.fromisoformat(i["inspected_at"].replace("Z", "+00:00"))
            events = self.events_for(i["inspection_id"])
            rep = self._report_for(i["inspection_id"])
            head = f"{i['asset_id']} spill of {fmt_num(vol)} bbl on {fmt_date(i['inspected_at'])} ({i['inspection_id']}), class {cls}"
            vol_cor = [c for c in i["corrections"] if c["field"] == "spill_est_volume_bbl"]
            if vol_cor:
                c0 = vol_cor[0]
                self.c_cor(cites, c0)
                old_cls = self.spill_class(c0["original_value"])
                head += f"; the volume was corrected from {fmt_num(c0['original_value'])} bbl (class {old_cls}) by {self.user_name(c0['author_user_id'])} [{c0['correction_id']}]"
                flags.append({"type": "corrected", "text": f"{i['inspection_id']} volume corrected {fmt_num(c0['original_value'])} → {fmt_num(vol)} bbl; compliance below uses the corrected volume.", "refs": [c0["correction_id"], i["inspection_id"]]})
            lines_before = len(facts)

            def add(proto, status, text, refs):
                if only and proto != only:
                    return
                rows.append([i["asset_id"], i["inspection_id"], proto, status, text, ", ".join(dict.fromkeys(refs))])
                facts.append({"text": f"{proto} {status}: {text}", "cites": [r for r in dict.fromkeys(refs) if r][:4]})
                if status == "breach":
                    breaches.append((i["asset_id"], proto, text))

            # SR-01: written notice for reportable / major spills
            if cls in ("reportable", "major"):
                reportable_n += 1
                limit = r_("sr01.major_hours", default=2.0) if cls == "major" else r_("sr01.hours", default=24.0)
                self.c_rule(cites, self.rules.get("sr01.hours"))
                filed = next((e for e in events if e["event_type"] == "spill_report_filed"), None)
                if filed:
                    self.c_reg(cites, filed)
                    h = filed["hours_to_report"]
                    if h is not None and h > limit:
                        nov = next((e for e in events if e["event_type"] == "notice_of_violation"), None)
                        extra = ""
                        if nov:
                            self.c_reg(cites, nov)
                            extra = f" This led to notice of violation {nov['event_id']} with a {usd(nov['fine_usd'] or 0)} fine, {nov['status']}."
                        add("SR-01", "breach", f"reported after {fmt_g(h)} hours ({filed['event_id']}), against a {fmt_g(limit)}-hour limit.{extra}", [filed["event_id"], "SR-01"] + ([nov["event_id"]] if nov else []))
                    else:
                        add("SR-01", "met", f"the written notice was filed after {fmt_g(h)} hours ({filed['event_id']}), within the {fmt_g(limit)}-hour limit.", [filed["event_id"], "SR-01"])
                else:
                    due = disc + timedelta(hours=limit)
                    if end_of_as_of > due:
                        add("SR-01", "breach", f"a written notice was due within {fmt_g(limit)} hours of the {disc.strftime('%d %b %H:%M').lstrip('0')} inspection (by {due.strftime('%d %b %Y %H:%M').lstrip('0')} UTC) and none is recorded" + (" (possible breach: it follows the corrected volume)" if vol_cor else "") + ".", [i["inspection_id"], "SR-01"])
                    else:
                        add("SR-01", "pending", f"a written notice is due by {due.strftime('%d %b %Y %H:%M').lstrip('0')} UTC.", [i["inspection_id"], "SR-01"])
                # RC-04: notices of violation need an answer within 30 days
                for nov in [e for e in events if e["event_type"] == "notice_of_violation"]:
                    self.c_reg(cites, nov)
                    self.c_rule(cites, self.rules.get("rc04.days"))
                    if (nov["fine_usd"] or 0) and nov["status"] == "open":
                        fines_open += nov["fine_usd"]
                    due_d = date.fromisoformat(nov["date"]) + timedelta(days=int(r_("rc04.days", default=30.0)))
                    resp = next((e for e in events if e["event_type"] == "nov_response_filed"), None)
                    if resp:
                        self.c_reg(cites, resp)
                        add("RC-04", "met", f"the response {resp['event_id']} was filed on {fmt_date(resp['date'])} (due {fmt_date(due_d.isoformat())}).", [resp["event_id"], nov["event_id"], "RC-04"])
                    elif due_d < self.as_of:
                        add("RC-04", "breach", f"notice of violation {nov['event_id']} needed a response by {fmt_date(due_d.isoformat())} and none is recorded.", [nov["event_id"], "RC-04"])
                    else:
                        add("RC-04", "pending", f"notice of violation {nov['event_id']} needs a response by {fmt_date(due_d.isoformat())}.", [nov["event_id"], "RC-04"])
                # SR-03: agency verification within 60 days
                due3 = disc.date() + timedelta(days=int(r_("sr03.days", default=60.0)))
                self.c_rule(cites, self.rules.get("sr03.days"))
                site = next((e for e in events if e["event_type"] == "site_inspection" and e["protocol_id"] == "SR-03"), None)
                if site:
                    self.c_reg(cites, site)
                if site and site["status"] == "closed":
                    add("SR-03", "met", f"remediation was verified by the agency ({site['event_id']}).", [site["event_id"], "SR-03"])
                elif due3 < self.as_of:
                    add("SR-03", "breach", f"cleanup verification was due by {fmt_date(due3.isoformat())} and is still open" + (f" ({site['event_id']})" if site else " (no site inspection recorded)") + ".", ([site["event_id"]] if site else []) + ["SR-03", i["inspection_id"]])
                else:
                    add("SR-03", "pending", f"agency verification of the cleanup is due by {fmt_date(due3.isoformat())}.", ["SR-03", i["inspection_id"]])
            # SR-02: containment time, only found in the repair report
            self.c_rule(cites, self.rules.get("sr02.hours"))
            lim2 = r_("sr02.hours", default=4.0)
            if rep and rep.get("containment_hours") is not None:
                self.c_mnt(cites, rep)
                cites.add(f"report:{rep['maintenance_id']}", "report", f"Repair report {rep['maintenance_id']}")
                hrs = rep["containment_hours"]
                st = "breach" if hrs > lim2 else "met"
                add("SR-02", st, f"contained after about {fmt_g(hrs)} hours, against a {fmt_g(lim2)}-hour limit" + (" (found only in the repair report)." if st == "breach" else "."), [f"report:{rep['maintenance_id']}", rep["maintenance_id"], "SR-02"])
            elif only in (None, "SR-02"):
                add("SR-02", "unknown", "no repair report with a containment time is on record.", [i["inspection_id"], "SR-02"])
            if vol_cor and rep and rep.get("report_class") and rep["report_class"] != cls:
                self.c_mnt(cites, rep)
                facts.append({"text": f"Repair report {rep['maintenance_id']} classed this spill as '{rep['report_class']}'; that was based on the old estimate and no longer holds (now {cls}).", "cites": [rep["maintenance_id"], c0["correction_id"]]})
            if only is None or len(facts) > lines_before:
                facts.insert(lines_before, {"text": head + ".", "cites": [i["inspection_id"]]})

        # well-level duties (single well, no protocol filter)
        if len(ids) == 1 and not only and extras:
            aid = ids[0]
            w = self.wells[aid]
            ms = self.maintenance([aid], periods.add_months(self.as_of, -12).isoformat(), self.as_of_s)
            test = [m for m in self.maintenance([aid]) if re.search(r"integrity test", m["issue"] or "", re.I) and periods.add_months(self.as_of, -int(r_("rc02.months", default=12.0))).isoformat() <= m["started_date"] <= self.as_of_s]
            self.c_rule(cites, self.rules.get("rc02.months"))
            if test:
                m = test[-1]
                self.c_mnt(cites, m)
                rows.append([aid, "", "RC-02", "met", f"annual flowline integrity test done on {fmt_date(m['started_at'])}", f"{m['maintenance_id']}, RC-02"])
                facts.append({"text": f"RC-02 met: the yearly flowline integrity test was done on {fmt_date(m['started_at'])} ({m['maintenance_id']}).", "cites": [m["maintenance_id"], "RC-02"]})
            else:
                rows.append([aid, "", "RC-02", "breach", "no annual flowline integrity test in the last 12 months", "RC-02"])
                facts.append({"text": "RC-02 breach: no yearly flowline integrity test is recorded in the last 12 months.", "cites": ["RC-02"]})
                breaches.append((aid, "RC-02", "no test"))
            by_kind: dict[str, list] = {}
            for m in ms:
                if m["maintenance_type"] == "corrective":
                    by_kind.setdefault(m["equipment_kind"], []).append(m)
            for kind, lst in by_kind.items():
                rule = self.rca_rule(w, kind)
                if rule and len(lst) >= rule["threshold"]:
                    for m in lst:
                        self.c_mnt(cites, m)
                    if rule["kind"] == "manual":
                        self.c_rule(cites, rule.get("rule"))
                    action = [m for m in lst if self.c.execute("SELECT action_required FROM report_facts WHERE maintenance_id=?", (m["maintenance_id"],)).fetchone() and self.c.execute("SELECT action_required FROM report_facts WHERE maintenance_id=?", (m["maintenance_id"],)).fetchone()[0]]
                    txt = f"a root-cause analysis is due on the {kind.replace('_', ' ')}: {len(lst)} corrective repairs in the last 12 months ({', '.join(m['maintenance_id'] for m in lst)})" + (f"; the report for {action[0]['maintenance_id']} marks it as \"Action required\"" if action else "")
                    pending_items.append(txt)
                    rows.append([aid, "", "RCA", "pending", txt, ", ".join(m["maintenance_id"] for m in lst)])
                    facts.append({"text": f"Open action (not a breach): {txt}.", "cites": [m["maintenance_id"] for m in lst][:4] + ([rule["ref"]] if rule["kind"] == "manual" else [])})
            for n in self.notes_for(aid, on=self.as_of_s):
                if re.search(r"not yet in the maintenance system|not (?:yet )?recorded in the maintenance system|work order not yet", n["text"] or "", re.I):
                    cites.add(n["note_id"], "shared_note" if n["source"] == "shared" else "note", f"{n['note_id']} · {n['note_type']} · {self.user_name(n['author_user_id'])}")
                    manual_ref = f"{w['well_type']}#4" if self.c.execute("SELECT 1 FROM sections WHERE doc_id=? AND section_id='4'", (f"manual:{w['well_type']}",)).fetchone() else None
                    if manual_ref:
                        cites.add(manual_ref, "document", f"{w['well_type']} manual §4 Start-up and shut-in")
                    txt = f"the planned shut-in is not yet recorded in the maintenance system, which the {w['well_type']} manual requires before work starts ({n['note_id']})"
                    pending_items.append(txt)
                    rows.append([aid, "", "Shut-in record", "pending", txt, ", ".join(filter(None, [n["note_id"], manual_ref]))])
                    facts.append({"text": f"Open action (not a breach): {txt}.", "cites": [n["note_id"]] + ([manual_ref] if manual_ref else [])})
        head_fact = {"text": f"{len(breaches)} breach(es) in {label} for {per.label}" + (f"; {usd(fines_open)} in fines still open" if fines_open else "") + (f" ({only} only)" if only else "") + (f". {reportable_n} of {len(real)} spill(s) reached the {fmt_g(r_('spill.reportable_min_bbl', default=5.0))} bbl reporting threshold" if only == "SR-01" or reportable_n else "") + ".", "cites": []}
        facts.insert(0, head_fact)
        if only == "SR-01":
            facts.append({"text": f"{reportable_n} of {len(real)} spill(s) in {per.label} reached the {fmt_g(r_('spill.reportable_min_bbl', default=5.0))} bbl threshold that requires a report to the regulator.", "cites": []})
        wells_hit = sorted({r[0] for r in rows if r[0]})
        return self.result("compliance_audit", f"Compliance audit, {label}", cites, window=per.as_dict(), data={"scope": label, "breaches": [{"asset_id": a, "protocol": p, "detail": t} for a, p, t in breaches], "fines_open_usd": fines_open, "pending": pending_items, "reportable": reportable_n},
                           facts=facts, flags=flags, visuals={"table": {"kind": "table", "columns": ["Well", "Inspection", "Protocol", "Status", "Detail", "Evidence"], "rows": rows}}, natural="table", entities={"wells": wells_hit})

    # ---- claims -------------------------------------------------------------------
    def claim_check(self, asset_id: str, asserted_state: str, since: str | None = None) -> dict:
        """Compare what a user says about a well's state with the latest inspection and with what others said."""
        w = self.well(asset_id)
        aid = w["asset_id"]
        state = asserted_state.lower().replace(" ", "_").replace("-", "_")
        wants_producing = state in ("producing", "running", "back_online", "online", "active", "running_fine")
        wants_stopped = state in ("not_producing", "shut_in", "down", "stopped", "offline", "planned_shut_in")
        if not (wants_producing or wants_stopped):
            raise ToolError("asserted_state must be 'producing' or 'not_producing' (shut in / down).")
        ins = self.latest(aid)
        cites = Cites()
        self.c_well(cites, aid)
        facts, flags = [], []
        verdict = {"asserted": "producing" if wants_producing else "not_producing", "producing": None, "matches": None}
        if ins is None or ins["producing"] is None:
            verdict["matches"] = None
            facts.append({"text": f"There is no usable inspection for {aid}, so the claim cannot be checked.", "cites": []})
            flags.append({"type": "missing_evidence", "text": "No inspection to check the claim against.", "refs": []})
        else:
            self.c_ins(cites, ins)
            verdict.update(producing=ins["producing"], matches=(ins["producing"] == wants_producing), inspection_id=ins["inspection_id"], delta=ins["delta"])
            who = self.user_name(ins["inspector_user_id"])
            facts.append({"text": f"The latest inspection {ins['inspection_id']} ({fmt_date(ins['inspected_at'])}, by {who}) shows the wellhead {fmt_num(ins['delta'])} °C above the air, so the well is {'producing' if ins['producing'] else 'not producing'} oil (needs ≥ {fmt_num(ins['threshold'])} °C).", "cites": [ins["inspection_id"]]})
            self.c_rule(cites, self.threshold_for(w["well_type"]))
        others = []
        for n in self.notes_for(aid, on=self.as_of_s):
            ref = n["note_id"]
            cites.add(ref, "shared_note" if n["source"] == "shared" else "note", f"{ref} · {n['note_type']} · {self.user_name(n['author_user_id'])}")
            others.append(n)
        for n in others:
            facts.append({"text": f"Existing note {n['note_id']} by {self.user_name(n['author_user_id'])}: \"{n['text']}\"" + (f" [{n['status']}]" if n.get("status") and n["status"] not in ("recorded",) else ""), "cites": [n["note_id"]]})
        return {"ins": ins, "verdict": verdict, "facts": facts, "flags": flags, "cites": cites, "others": others, "well": w, "since": since}

    # ==== broader questions: repairs, regulator events, inspection gaps, long downtime ====
    def repairs(self, scope: str | None = None, period: str | None = None, equipment_kind: str | None = None, maintenance_type: str | None = None,
                top_n: int = 10, start: str | None = None, end: str | None = None) -> dict:
        ids, label = self.resolve_scope(scope)
        per = self.period(period, start, end, default="this year")
        eq = (equipment_kind or "").strip().lower().replace(" ", "_") or None
        mt = (maintenance_type or "").strip().lower() or None
        ms = [m for m in self.maintenance(ids, per.start.isoformat(), per.end.isoformat()) if (not eq or m["equipment_kind"] == eq) and (not mt or m["maintenance_type"] == mt)]
        cites = Cites()
        total = sum(m["cost_total"] or 0 for m in ms)
        by_kind: dict[str, float] = {}
        for m in ms:
            by_kind[m["equipment_kind"] or "other"] = by_kind.get(m["equipment_kind"] or "other", 0) + (m["cost_total"] or 0)
        top = sorted(ms, key=lambda m: (-(m["cost_total"] or 0), m["maintenance_id"]))[: max(1, int(top_n or 10))]
        rows = []
        for m in top:
            self.c_mnt(cites, m)
            rows.append([m["maintenance_id"], m["asset_id"], m["started_date"], m["maintenance_type"], (m["equipment_kind"] or "").replace("_", " "), m["issue"], round(m["cost_total"] or 0)])
        desc = " ".join(x for x in (mt, eq.replace("_", " ") if eq else None, "repairs") if x)
        facts = [{"text": f"{len(ms)} {desc} in {label}, {per.label}, costing {usd(total)} in total (a repair belongs to the period of its start date).", "cites": []}]
        for r in rows[:5]:
            facts.append({"text": f"{r[0]} on {r[1]} ({fmt_date(r[2])}, {r[3]}, {r[4]}): {r[5]}, {usd(r[6])}.", "cites": [r[0]]})
        if by_kind:
            facts.append({"text": "Cost by equipment: " + "; ".join(f"{k.replace('_', ' ')} {usd(v)}" for k, v in sorted(by_kind.items(), key=lambda kv: -kv[1])) + ".", "cites": []})
        bar = {"kind": "bar", "title": f"Repair cost by equipment · {label} · {per.label}", "labels": [k.replace("_", " ") for k in by_kind], "values": [round(v) for v in by_kind.values()], "unit": "USD"}
        return self.result("repairs", f"Repairs in {label}", cites, window=per.as_dict(), data={"scope": label, "count": len(ms), "total_usd": total, "by_equipment": by_kind},
                           facts=facts, visuals={"table": {"kind": "table", "columns": ["Repair", "Well", "Started", "Type", "Equipment", "Issue", "Cost (USD)"], "rows": rows}, "bar": bar}, natural="table",
                           entities={"wells": sorted({m["asset_id"] for m in top})})

    def regulatory_events(self, scope: str | None = None, period: str | None = None, event_type: str | None = None, status: str | None = None,
                          start: str | None = None, end: str | None = None) -> dict:
        ids, label = self.resolve_scope(scope)
        per = self.period(period, start, end, default="last 12 months")
        q = f"SELECT * FROM regulatory_events WHERE asset_id IN ({','.join('?' * len(ids))}) AND date>=? AND date<=?"
        params: list = [*ids, per.start.isoformat(), per.end.isoformat()]
        if event_type:
            q += " AND event_type=?"
            params.append(event_type.strip().lower())
        if status:
            q += " AND status=?"
            params.append(status.strip().lower())
        evs = [dict(r) for r in self.c.execute(q + " ORDER BY date, event_id", params)]
        cites = Cites()
        rows = []
        for e in evs:
            self.c_reg(cites, e)
            rows.append([e["event_id"], e["asset_id"], e["date"], e["event_type"], e["protocol_id"], e["status"], round(e["fine_usd"] or 0), e["detail"]])
        fines = sum(e["fine_usd"] or 0 for e in evs)
        open_fines = sum(e["fine_usd"] or 0 for e in evs if e["status"] == "open")
        kinds: dict[str, int] = {}
        for e in evs:
            kinds[e["event_type"]] = kinds.get(e["event_type"], 0) + 1
        kinds_txt = ", ".join(str(n) + " " + k.replace("_", " ") for k, n in kinds.items())
        facts = [{"text": f"{len(evs)} regulator event(s) in {label}, {per.label}" + (f" ({kinds_txt})" if kinds else "") + f"; fines {usd(fines)}, of which {usd(open_fines)} still open.", "cites": []}]
        for e in evs[:8]:
            facts.append({"text": f"{e['event_id']} ({fmt_date(e['date'])}, {e['asset_id']}): {e['event_type'].replace('_', ' ')} under {e['protocol_id']}, {e['status']}" + (f", fine {usd(e['fine_usd'])}" if e["fine_usd"] else "") + f". {e['detail']}", "cites": [e["event_id"]]})
        return self.result("regulatory_events", f"Regulator events in {label}", cites, window=per.as_dict(), data={"scope": label, "count": len(evs), "fines_usd": fines, "open_fines_usd": open_fines},
                           facts=facts, visuals={"table": {"kind": "table", "columns": ["Event", "Well", "Date", "Type", "Protocol", "Status", "Fine (USD)", "Detail"], "rows": rows}}, natural="table",
                           entities={"wells": sorted({e["asset_id"] for e in evs})})

    def inspection_gaps(self, scope: str | None = None, period: str | None = None, max_days: int | None = None, start: str | None = None, end: str | None = None) -> dict:
        """RC-01: wells whose inspections are further apart than the SOP allows, or whose latest inspection is too old."""
        ids, label = self.resolve_scope(scope)
        per = self.period(period, start, end, default="last 12 months")
        limit = int(max_days or self.rules.value("rc01.days", default=14.0))
        self.c.row_factory = sqlite3.Row
        cites = Cites()
        rule = self.rules.get("rc01.days")
        self.c_rule(cites, rule)
        rows, worst = [], []
        for a in ids:
            dates = [date.fromisoformat(r["inspected_date"]) for r in self.c.execute("SELECT inspected_date FROM inspections WHERE asset_id=? AND inspected_date>=? AND inspected_date<=? ORDER BY inspected_at", (a, per.start.isoformat(), per.end.isoformat()))]
            gaps = [((b - x).days, x, b) for x, b in zip(dates, dates[1:]) if (b - x).days > limit]
            since = (self.as_of - dates[-1]).days if dates else None
            stale = since is not None and since > limit and per.end >= self.as_of
            if gaps or stale:
                g = max(gaps, key=lambda t: t[0]) if gaps else None
                rows.append([a, len(gaps), f"{g[0]} days ({fmt_date(g[1].isoformat())} to {fmt_date(g[2].isoformat())})" if g else "", dates[-1].isoformat() if dates else "", since if stale else ""])
                worst.append((a, len(gaps), g, since if stale else None))
        rows.sort(key=lambda r: -r[1])
        facts = [{"text": f"{len(rows)} of {len(ids)} well(s) in {label} went more than {limit} days between inspections in {per.label}, or have a latest inspection older than {limit} days (RC-01 allows {fmt_g(self.rules.value('rc01.days', default=14.0))} days).", "cites": [rule.ref] if rule and not rule.fallback else []}]
        for a, n, g, since in worst[:8]:
            facts.append({"text": f"{a}: {n} gap(s) over {limit} days" + (f", longest {g[0]} days ({fmt_date(g[1].isoformat())} to {fmt_date(g[2].isoformat())})" if g else "") + (f"; last inspected {since} days before the as-of date" if since else "") + ".", "cites": [a]})
            self.c_well(cites, a)
        return self.result("inspection_gaps", f"Inspection gaps in {label}", cites, window=per.as_dict(), data={"scope": label, "wells": [r[0] for r in rows], "limit_days": limit}, facts=facts,
                           visuals={"table": {"kind": "table", "columns": ["Well", "Gaps over limit", "Longest gap", "Last inspection", "Days since last inspection"], "rows": rows}}, natural="table", entities={"wells": [r[0] for r in rows][:25]})

    def long_downtime(self, scope: str | None = None, period: str | None = None, min_days: int | None = None, start: str | None = None, end: str | None = None) -> dict:
        """RC-03: runs of consecutive weekly inspections that all found the well not producing, longer than min_days."""
        ids, label = self.resolve_scope(scope)
        per = self.period(period, start, end, default="last 12 months")
        limit = int(min_days or self.rules.value("rc03.days", default=14.0))
        cites = Cites()
        self.c_rule(cites, self.rules.get("rc03.days"))
        rows, facts = [], []
        for a, ins in {a: [i for i in self.inspections([a], per.start.isoformat(), per.end.isoformat())] for a in ids}.items():
            run: list[dict] = []
            runs = []
            for i in ins + [None]:
                if i is not None and i["producing"] is False:
                    run.append(i)
                else:
                    if run and 7 * len(run) > limit:
                        runs.append(run)
                    run = []
            for r in runs:
                for i in (r[0], r[-1]):
                    self.c_ins(cites, i)
                rows.append([a, 7 * len(r), r[0]["inspected_date"], r[-1]["inspected_date"], len(r)])
                facts.append({"text": f"{a} was not producing for {7 * len(r)} consecutive days ({len(r)} weekly inspections, {fmt_date(r[0]['inspected_at'])} to {fmt_date(r[-1]['inspected_at'])}), more than the {limit}-day reporting limit.", "cites": [r[0]["inspection_id"], r[-1]["inspection_id"]]})
        rows.sort(key=lambda r: -r[1])
        facts.insert(0, {"text": f"{len(rows)} run(s) of more than {limit} consecutive days not producing in {label}, {per.label} (must be reported to the area production supervisor).", "cites": []})
        return self.result("long_downtime", f"Long downtime runs in {label}", cites, window=per.as_dict(), data={"scope": label, "runs": len(rows), "wells": sorted({r[0] for r in rows}), "limit_days": limit}, facts=facts[:60],
                           visuals={"table": {"kind": "table", "columns": ["Well", "Consecutive days down", "From", "To", "Weekly inspections"], "rows": rows}}, natural="table", entities={"wells": sorted({r[0] for r in rows})[:25]})
