"""Built-in question patterns: a fallback for when the model is unavailable.

Gemma normally picks the tool and fills its arguments. If it cannot be reached (rate limit, an
outage), this maps common question shapes to the same deterministic tools so an answer with
citations is still possible. It is deliberately conservative: unsure means no answer, never a
guess. Statements that change shared knowledge (corrections, rules, claims) always need the model.
"""

import re
from datetime import date

from .analyst import Analyst
from .tools import wants_write_tools

NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12}
EQUIPMENT = ["pump jack", "rod string", "downhole pump", "wellhead", "flowline", "separator"]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def find_scope(A: Analyst, text: str) -> str | None:
    """A well ID, area name/ID or team named in the text."""
    m = re.search(r"(?i)\bwell[-\s]?0*(\d+)\b", text)
    if m:
        return f"WELL-{int(m.group(1)):04d}"
    t = " " + _norm(text) + " "
    best = None
    for a in A.areas.values():
        n = _norm(a["name"] or "")
        if n and f" {n} " in t:
            best = best or a["name"]
        i = _norm(a["area_id"]).replace(" ", "")
        letters, digits = re.match(r"([a-z]+)(\d*)", i).groups() if re.match(r"([a-z]+)(\d*)", i) else (i, "")
        if letters and digits and re.search(rf"\b{letters}[\s-]?0*{int(digits)}\b", text.lower()):
            best = best or a["name"]
    if best:
        return best
    for team in A.teams.values():
        if _norm(team["name"] or "") in t:
            return team["name"]
    return None


def find_period(text: str) -> str | None:
    t = text.lower()
    m = re.search(r"(?:last|past)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|twelve)\s+(day|week|month|year)s?", t)
    if m:
        n = NUMBER_WORDS.get(m.group(1), m.group(1))
        return f"last {n} {m.group(2)}s"
    for phrase in ("year to date", "this year", "last year", "this month", "last month", "this quarter", "last quarter", "this summer", "yesterday"):
        if phrase in t:
            return phrase
    m = re.search(r"\b(20\d{2})\b", t)
    if m:
        return m.group(1)
    return None


def find_top_n(text: str) -> int | None:
    t = text.lower()
    m = re.search(r"\b(?:top|which|the)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+wells?\b", t) or re.search(r"\b(\d+)\s+wells?\b", t)
    if m:
        v = m.group(1)
        return int(v) if v.isdigit() else NUMBER_WORDS[v]
    return None


MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def find_date(A: Analyst, text: str) -> str | None:
    m = re.search(r"\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", text.lower())
    if not m:
        return None
    month, day = MONTHS[m.group(2)], int(m.group(1))
    year = A.as_of.year if month <= A.as_of.month else A.as_of.year - 1
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def route(A: Analyst, message: str, force: bool = False) -> list[tuple[str, dict]] | None:
    if not force and wants_write_tools(message):  # a statement, correction or rule: only the model may interpret those
        return None
    t = message.lower()
    scope, period, top_n = find_scope(A, message), find_period(message), find_top_n(message)
    is_well = bool(scope and scope.startswith("WELL-"))
    spill = "spill" in t
    visual_words = {"map": "map" in t, "heat": "heatmap" in t or "heat map" in t, "line": "line chart" in t or "line graph" in t}

    mnt = re.search(r"\bMNT-\d{4}-\d{3}\b", message, re.I)
    if mnt and re.search(r"\bwho\b|technician|carried out|performed|did the (?:work|repair)", t):
        return [("maintenance_record", {"maintenance_id": mnt.group(0).upper()})]
    if re.search(r"\bgas\b|h2s|rotten", t) and re.search(r"operator note|odou?r|smell", t) and re.search(r"response|someone out|in time|deadline", t):
        since = re.search(r"since\s+(\d{1,2}\s+[a-z]{3,9})", t)
        return [("gas_response", {"scope": scope or "all", "period": period, "start": find_date(A, since.group(1)) if since else None, "end": A.as_of_s if since else None})]
    if re.search(r"we discussed|discussed (?:yesterday|earlier|before)|talked about", t):
        return [("recall_discussed", {})] if "cost" not in t else None  # the cost step needs the recalled wells; leave to the model
    if re.search(r"\b(root[- ]cause|rca)\b", t):
        eq = next((e.replace(" ", "_") for e in EQUIPMENT if e in t), "pump_jack")
        return [("rca_candidates", {"scope": scope or "all", "equipment_kind": eq})]
    if re.search(r"not contained|containment|contained within|sop time limit", t) and spill:
        return [("compliance_audit", {"scope": scope or "all", "period": period or "last 90 days", "protocol": "SR-02"})]
    if re.search(r"report to the regulator|needed a report|reportable|written notice", t):
        return [("compliance_audit", {"scope": scope or "all", "period": period or "last 90 days", "protocol": "SR-01"})]
    if re.search(r"rules? .*(broken|violat)|broken|breach|violation|compliance|still open", t) and (is_well or scope):
        return [("compliance_audit", {"scope": scope, "period": period or "last 12 months"})]
    if re.search(r"fines?|notices? of violation|regulator", t) and not spill:
        return [("regulatory_events", {"scope": scope or "all", "period": period or "last 12 months"})]
    if (visual_words["heat"] or re.search(r"by (?:geographic )?area and month", t)) and spill:
        return [("spill_heatmap", {"period": period or "this year"})]
    if visual_words["line"] and is_well:
        m = re.search(r"(\d+)\s+weeks?", t)
        return [("inspection_series", {"asset_id": scope, "weeks": int(m.group(1)) if m else 13})]
    if re.search(r"was the .* spill real|real oil|was .*spill .*real", t) and is_well:
        return [("spill_evidence", {"asset_id": scope, "date": find_date(A, t)})]
    if re.search(r"planned|scheduled", t) and is_well:
        return [("well_context", {"asset_id": scope})]
    if spill and (scope or period):
        return [("spills", {"scope": scope or "all", "period": period or "last 4 years"})]
    if re.search(r"repair", t) and re.search(r"cost|spent|expens", t):
        return [("repair_costs", {"scope": scope or "all", "period": period or "this year", "top_n": top_n})] if scope and not is_well else \
               [("repair_costs", {"wells": [scope], "period": period or "this year"})] if is_well else [("repair_costs", {"scope": "all", "period": period or "this year", "top_n": top_n or 10})]
    if re.search(r"downtime|\bdown\b|days down|were down", t):
        if re.search(r"most|longest|top|highest|worst", t) or top_n:
            return [("downtime_ranking", {"scope": scope or "all", "period": period or "last 4 months", "top_n": top_n or 3})]
        if scope:
            return [("downtime", {"scope": scope, "period": period or "this year"})]
    if re.search(r"planned|shut[- ]?in|scheduled", t) and is_well:
        return [("well_context", {"asset_id": scope})]
    if re.search(r"not producing|isn't producing|stopped|down right now|shut in", t) and scope and not is_well:
        return [("wells_not_producing", {"scope": scope})]
    if re.search(r"producing|status|running", t) and is_well:
        return [("well_status", {"asset_id": scope})]
    if re.search(r"producing|running", t) and scope:
        return [("wells_not_producing", {"scope": scope, "state": "all" if "all" in t else "not_producing"})]
    return None
