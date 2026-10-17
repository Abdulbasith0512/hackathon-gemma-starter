"""Rules (thresholds, deadlines) read from the well-type manuals and SOPs.

The documents are the source of truth: each rule keeps the section it came from and the
quoted passage. If a number cannot be found, a clearly-marked fallback default is used
and shown, never silently. A new well type with no parseable rule has no threshold, and
the analyst reports "rule not found" instead of guessing.
"""

import re
import sqlite3
from dataclasses import dataclass, field

WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}

# Used only when the documents yield nothing; always flagged as fallback.
FALLBACKS = {
    "spill.moderate_min_bbl": (1.0, "bbl"), "spill.reportable_min_bbl": (5.0, "bbl"), "spill.major_min_bbl": (25.0, "bbl"),
    "sr01.hours": (24.0, "hours"), "sr01.major_hours": (2.0, "hours"), "sr02.hours": (4.0, "hours"),
    "sr03.days": (60.0, "days"), "sr03.tph_pct": (1.0, "%"), "sr03.min_samples": (4.0, "samples"),
    "rc01.days": (14.0, "days"), "rc02.months": (12.0, "months"), "rc03.days": (14.0, "days"), "rc04.days": (30.0, "days"),
}


@dataclass
class Rule:
    key: str
    value: float
    unit: str
    scope: str                     # 'global' or 'well_type:<T>'
    ref: str                       # citation id, e.g. 'T200#9.3' or 'SR-01'
    doc_id: str | None = None
    section_id: str | None = None
    quote: str = ""
    fallback: bool = False
    inherited_from: str | None = None
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {k: getattr(self, k) for k in ("key", "value", "unit", "scope", "ref", "doc_id", "section_id", "quote", "fallback", "inherited_from")}


def _num(token: str) -> float:
    token = token.strip().lower()
    return float(WORDS[token]) if token in WORDS else float(token)


def _clean(text: str) -> str:
    """Markdown to plain text for display: no bold markers, backticks or table pipes."""
    text = re.sub(r"[*`]", "", text)
    text = re.sub(r"\s*\|\s*", " · ", text)
    return re.sub(r"\s+", " ", text).strip(" ·")


def _quote(text: str, start: int, end: int, pad: int = 70) -> str:
    """The sentence (or table row) around a match, cleaned."""
    left = max(text.rfind("\n", 0, start), text.rfind(". ", 0, start))
    right_candidates = [i for i in (text.find("\n", end), text.find(". ", end)) if i != -1]
    right = min(right_candidates) + 1 if right_candidates else len(text)
    return _clean(text[left + 1:right] if left != -1 else text[:right])


class Rules:
    def __init__(self):
        self._rules: dict[tuple[str, str], Rule] = {}   # (scope, key) -> Rule
        self.well_types: list[str] = []

    def add(self, rule: Rule) -> None:
        self._rules[(rule.scope, rule.key)] = rule

    def get(self, key: str, well_type: str | None = None) -> Rule | None:
        if well_type and (f"well_type:{well_type}", key) in self._rules:
            return self._rules[(f"well_type:{well_type}", key)]
        return self._rules.get(("global", key))

    def value(self, key: str, well_type: str | None = None, default: float | None = None) -> float | None:
        r = self.get(key, well_type)
        return r.value if r else default

    def all(self) -> list[Rule]:
        return sorted(self._rules.values(), key=lambda r: (r.scope, r.key))


_PRODUCING = re.compile(r"producing[\s\S]{0,200}?at least\s*\*{0,2}\s*(\d+(?:\.\d+)?)\s*°?\s*C\s*above", re.I)
_RCA_A = re.compile(r"(\w+)\s+or more\s+\*{0,2}corrective\*{0,2}\s+maintenance events on the same equipment\s+kind in the\s+(\d+)\s+months", re.I)
_RCA_B = re.compile(r"RCA after\s+(\w+)\s+corrective events on the same equipment\s+kind within\s+(\d+)\s+months", re.I)
_DOWNTIME_REPORT = re.compile(r"[Dd]owntime of more than\s+(\d+)\s+consecutive days")
_INHERIT = re.compile(r"follow the\s+(T\d+\w*)\s+manual", re.I)


def _sections(conn: sqlite3.Connection, doc_id: str) -> list[sqlite3.Row]:
    return conn.execute("SELECT section_id, heading, text FROM sections WHERE doc_id=? ORDER BY ord", (doc_id,)).fetchall()


def load_rules(conn: sqlite3.Connection) -> Rules:
    rules = Rules()

    manuals = conn.execute("SELECT doc_id, well_type FROM documents WHERE kind='manual'").fetchall()
    inherits: dict[str, str] = {}
    for m in manuals:
        wt, doc_id = m["well_type"], m["doc_id"]
        rules.well_types.append(wt)
        scope = f"well_type:{wt}"
        secs = _sections(conn, doc_id)
        full = "\n".join(s["text"] for s in secs)
        inh = _INHERIT.search(full)
        if inh and inh.group(1) != wt:
            inherits[wt] = inh.group(1)
        for s in secs:
            t = s["text"]
            if (mo := _PRODUCING.search(t)) and (scope, "production_delta_c") not in rules._rules:
                rules.add(Rule("production_delta_c", float(mo.group(1)), "°C above ambient", scope, f"{wt}#{s['section_id']}", doc_id, s["section_id"], _quote(t, mo.start(), mo.end())))
            mo = _RCA_A.search(t) or _RCA_B.search(t)
            if mo and (scope, "rca_corrective_count") not in rules._rules:
                q = _quote(t, mo.start(), mo.end())
                ref = f"{wt}#{s['section_id']}"
                rules.add(Rule("rca_corrective_count", _num(mo.group(1)), "corrective repairs", scope, ref, doc_id, s["section_id"], q))
                rules.add(Rule("rca_window_months", _num(mo.group(2)), "months", scope, ref, doc_id, s["section_id"], q))
            if (mo := _DOWNTIME_REPORT.search(t)) and (scope, "downtime_report_days") not in rules._rules:
                rules.add(Rule("downtime_report_days", float(mo.group(1)), "consecutive days", scope, f"{wt}#{s['section_id']}", doc_id, s["section_id"], _quote(t, mo.start(), mo.end())))

    # A manual that says "procedures not listed here follow the T200 manual" inherits what it lacks.
    for wt, parent in inherits.items():
        for key in ("rca_corrective_count", "rca_window_months", "downtime_report_days"):
            if (f"well_type:{wt}", key) not in rules._rules and (f"well_type:{parent}", key) in rules._rules:
                p = rules._rules[(f"well_type:{parent}", key)]
                rules.add(Rule(key, p.value, p.unit, f"well_type:{wt}", p.ref, p.doc_id, p.section_id, p.quote, inherited_from=parent))

    # SOP parameters.
    def sop_row(protocol: str) -> tuple[str, str, str] | None:
        r = conn.execute("SELECT doc_id, section_id, text FROM sections WHERE section_id=? AND doc_id LIKE 'sop:%' LIMIT 1", (protocol,)).fetchone()
        return (r["doc_id"], r["section_id"], r["text"]) if r else None

    def put(key, value, unit, ref, doc_id=None, section_id=None, quote=""):
        if value is None:
            value, unit = FALLBACKS[key]
            rules.add(Rule(key, value, unit, "global", ref, doc_id, section_id, "Not found in the documents; fallback default.", fallback=True))
        else:
            rules.add(Rule(key, value, unit, "global", ref, doc_id, section_id, _clean(quote)))

    within = re.compile(r"within\s+\*{0,2}(\d+(?:\.\d+)?)\s+(hours|days)", re.I)
    for protocol, mapping in {
        "SR-01": [("sr01.hours", 0), ("sr01.major_hours", 1)],
        "SR-02": [("sr02.hours", 0)],
        "SR-03": [("sr03.days", 0)],
        "RC-04": [("rc04.days", 0)],
    }.items():
        row = sop_row(protocol)
        found = within.findall(row[2]) if row else []
        for key, idx in mapping:
            val = float(found[idx][0]) if len(found) > idx else None
            put(key, val, found[idx][1] if val is not None else "", protocol, row[0] if row else None, protocol, row[2] if row else "")
    row = sop_row("SR-03")
    mo = re.search(r"(\d+(?:\.\d+)?)%\s*TPH", row[2]) if row else None
    put("sr03.tph_pct", float(mo.group(1)) if mo else None, "%", "SR-03", row[0] if row else None, "SR-03", row[2] if row else "")
    mo = re.search(r"at least\s+\*{0,2}(\d+)\s+soil samples", row[2], re.I) if row else None
    put("sr03.min_samples", float(mo.group(1)) if mo else None, "samples", "SR-03", row[0] if row else None, "SR-03", row[2] if row else "")
    row = sop_row("RC-01")
    mo = re.search(r"every\s+\*{0,2}(\d+)\s+days", row[2], re.I) if row else None
    put("rc01.days", float(mo.group(1)) if mo else None, "days", "RC-01", row[0] if row else None, "RC-01", row[2] if row else "")
    row = sop_row("RC-03")
    mo = re.search(r"more than\s+\*{0,2}(\d+)\s+consecutive days", row[2], re.I) if row else None
    put("rc03.days", float(mo.group(1)) if mo else None, "days", "RC-03", row[0] if row else None, "RC-03", row[2] if row else "")
    row = sop_row("RC-02")
    put("rc02.months", 12.0 if row and re.search(r"calendar year|annual|once per", row[2], re.I) else None, "months", "RC-02", row[0] if row else None, "RC-02", row[2] if row else "")

    # Spill classes (table in the Spill Response SOP, section 3).
    sec = conn.execute("SELECT doc_id, section_id, text FROM sections WHERE doc_id LIKE 'sop:%' AND text LIKE '%Reportable%' AND text LIKE '%Moderate%' LIMIT 1").fetchone()
    text = sec["text"] if sec else ""
    ref = f"{sec['doc_id'].split(':', 1)[1]}#{sec['section_id']}" if sec else "spill-response-sop"
    for key, pat in (("spill.moderate_min_bbl", r"\|\s*Moderate\s*\|\s*(\d+(?:\.\d+)?)\s*bbl"),
                     ("spill.reportable_min_bbl", r"\|\s*Reportable\s*\|\s*(\d+(?:\.\d+)?)\s*bbl"),
                     ("spill.major_min_bbl", r"\|\s*Major\s*\|\s*(\d+(?:\.\d+)?)\s*bbl")):
        mo = re.search(pat, text)
        put(key, float(mo.group(1)) if mo else None, "bbl", ref, sec["doc_id"] if sec else None, sec["section_id"] if sec else None, _quote(text, mo.start(), mo.end()) if mo else "")
    return rules
