"""The tools Gemma can call. Each wraps one deterministic analyst function.

Gemma picks a tool and fills its arguments from the question; the arithmetic, windows, rules
and citations all come from the analyst. The user's identity is never a tool argument: it comes
from the server session, so a prompt cannot make one user read another's private memory.
"""

import inspect
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from google.genai import types

from . import actions
from .analyst import Analyst, Cites, ToolError, fmt_date


@dataclass
class Ctx:
    analyst: Analyst
    store: Any
    user_id: str
    conv_id: str
    auto_confirm: bool = False
    message: str = ""


@dataclass
class Tool:
    name: str
    description: str
    params: list[tuple]            # (name, type, description, required)
    fn: Callable[[Ctx, dict], dict]
    writes: bool = False


REGISTRY: dict[str, Tool] = {}


def tool(name: str, description: str, params: list[tuple], writes: bool = False):
    def deco(fn):
        REGISTRY[name] = Tool(name, description, params, fn, writes)
        return fn
    return deco


PERIOD = ("period", "string", "Time phrase copied from the question, e.g. 'last 4 months', '2025', 'this year'. Do not compute dates.", False)
START = ("start", "string", "Exact start date YYYY-MM-DD, only if given.", False)
END = ("end", "string", "Exact end date YYYY-MM-DD, only if given.", False)
SCOPE = ("scope", "string", "Well ID, area name, well type (T350) or 'all'.", True)
WELL_TYPE = ("well_type", "string", "Optional well type filter such as T200 or T350.", False)


def _call(ctx: Ctx, name: str, fn_name: str, args: dict) -> dict:
    fn = getattr(ctx.analyst, fn_name)
    allowed = inspect.signature(fn).parameters
    kwargs = {k: v for k, v in args.items() if k in allowed and v not in (None, "")}
    for k in ("top_n", "weeks", "months"):
        if k in kwargs:
            kwargs[k] = int(float(kwargs[k]))
    return fn(**kwargs)


@tool("well_status", "Is one well producing oil now? Status from the latest inspection and manual, inspector, time, reason if stopped, stale recorded status.",
      [("asset_id", "string", "Well ID such as WELL-0001.", True)])
def _well_status(ctx, a):
    return _call(ctx, "well_status", "well_status", a)


@tool("wells_not_producing", "Wells not producing oil now in an area/type/field, with the reason for each or 'no recorded reason'.",
      [SCOPE, WELL_TYPE, ("state", "string", "not_producing (default), producing or all", False)])
def _wnp(ctx, a):
    return _call(ctx, "wells_not_producing", "wells_not_producing", a)


@tool("inspection_series", "Weekly wellhead vs air temperature for one well over the last N weeks, non-producing weeks marked (line chart).",
      [("asset_id", "string", "Well ID.", True), ("weeks", "integer", "Number of most recent weekly readings (default 13).", False)])
def _series(ctx, a):
    return _call(ctx, "inspection_series", "inspection_series", a)


@tool("spills", "Real oil spills (corrected detections excluded) in a period: count, total bbl, each spill with date, volume, location. For counts, lists, maps.",
      [SCOPE, PERIOD, START, END, WELL_TYPE])
def _spills(ctx, a):
    return _call(ctx, "spills", "spills", a)


@tool("downtime", "Downtime days for a well/area/field in a period (7 days per weekly inspection that found it not producing). For one well lists each inspection and cause.",
      [SCOPE, PERIOD, START, END, ("group_by", "string", "area or well_type, to compare groups", False)])
def _downtime(ctx, a):
    return _call(ctx, "downtime", "downtime", a)


@tool("downtime_ranking", "Top N wells by downtime in a period for an area/type/field.",
      [SCOPE, PERIOD, ("top_n", "integer", "How many wells to return (default 3).", False), START, END, WELL_TYPE])
def _ranking(ctx, a):
    return _call(ctx, "downtime_ranking", "downtime_ranking", a)


@tool("repair_costs", "Repair cost and count per well in a period (by start date).",
      [("wells", "array", "List of well IDs, e.g. ['WELL-0121','WELL-0138'].", False), ("scope", "string", "Area, well type or 'all' when no specific wells are given.", False), PERIOD, START, END, ("top_n", "integer", "how many wells to show", False), ("group_by", "string", "area or well_type, to compare groups", False)])
def _costs(ctx, a):
    return _call(ctx, "repair_costs", "repair_costs", a)


@tool("spill_heatmap", "Spill counts by area and month (heatmap data).", [PERIOD, ("scope", "string", "Optional: restrict to an area or well type; default all areas.", False), START, END])
def _heat(ctx, a):
    return _call(ctx, "spill_heatmap", "spill_heatmap", a)


@tool("rca_candidates", "Wells needing a root-cause analysis on an equipment kind (too many corrective repairs in 12 months). Uses the manual threshold or a user-set type rule.",
      [("scope", "string", "Area, type or 'all'.", False), ("equipment_kind", "string", "pump_jack (default), rod_string, downhole_pump, wellhead, flowline, separator.", False)])
def _rca(ctx, a):
    return _call(ctx, "rca_candidates", "rca_candidates", a)


@tool("well_context", "Notes, planned work/shut-ins and open repairs for one well, including notes shared by users.",
      [("asset_id", "string", "Well ID.", True)])
def _context(ctx, a):
    return _call(ctx, "well_context", "well_context", a)


@tool("search_documents", "Search manuals, SOPs and repair reports for a rule or procedure.",
      [("query", "string", "Keywords to search for.", True), ("kind", "string", "Optional: manual, sop or report.", False)])
def _search(ctx, a):
    return _call(ctx, "search_documents", "search_documents", a)


@tool("recall_discussed", "Wells this user discussed in earlier conversations ('the three wells we discussed yesterday').",
      [("count", "integer", "How many wells the user said, e.g. 3 for 'the three wells'", False), ("topic", "string", "A word from what was discussed, if the user gave one", False)])
def _recall(ctx, a):
    cites = Cites()
    all_groups = ctx.store.recall(ctx.user_id, exclude_conv_id=ctx.conv_id, entity_type="well")
    groups = all_groups
    want = a.get("count")
    if want not in (None, ""):
        groups = [g for g in groups if len(g["entities"]) == int(float(want))]
    if a.get("topic"):
        words = [w for w in re.findall(r"[a-z0-9]+", str(a["topic"]).lower()) if len(w) > 2]
        groups = [g for g in groups if all(w in g["topic"].lower() for w in words)] or groups
    res = ctx.analyst.result("recall_discussed", "Wells you discussed earlier", cites)
    if not groups:
        res["facts"] = [{"text": "You have no earlier conversation with me that mentions " + (f"{int(float(want))} wells" if want not in (None, "") else "wells") + ", so there is nothing to recall.", "cites": []}]
        res["flags"] = [{"type": "missing_evidence", "text": "No earlier conversation found for this user.", "refs": []}]
        res["data"] = {"found": False}
        res["natural"] = "table"
        return res
    g = groups[0]
    res["facts"] = [{"text": f"In your earlier conversation ({fmt_date(g['when'])}) you asked \"{g['topic']}\" which covered: {', '.join(g['entities'])}.", "cites": []}]
    if len(groups) > 1:
        res["facts"].append({"text": f"{len(groups) - 1} other earlier discussion(s) also match; the most recent one is used.", "cites": []})
    elif len(all_groups) > 1 and want in (None, ""):
        res["facts"].append({"text": f"You have {len(all_groups) - 1} other earlier discussion(s) of wells; the most recent one is used.", "cites": []})
    res["data"] = {"found": True, "wells": g["entities"], "topic": g["topic"], "when": g["when"]}
    res["intermediate"] = True  # a lookup: the question still needs another tool on these wells
    for w in g["entities"]:
        if w in ctx.analyst.wells:
            ctx.analyst.c_well(cites, w)
    res["citations"] = cites.list()
    res["entities"] = {"wells": []}
    res["visuals"] = {"table": {"kind": "table", "columns": ["Well", "Discussed when asked"], "rows": [[w, g["topic"]] for w in g["entities"]]}}
    return res


@tool("compliance_audit", "Spill-protocol compliance for a well/area in a period: SR-01 written notice (24 h), SR-02 containment (4 h, from repair reports), SR-03 cleanup verification (60 d), RC-04 violation response (30 d); for one well also RC-02 flowline test, root-cause analyses due and unrecorded shut-ins. Use protocol to filter (e.g. SR-02 for 'not contained in time', SR-01 for 'needed a report to the regulator').",
      [SCOPE, PERIOD, ("protocol", "string", "Optional: SR-01, SR-02, SR-03 or RC-04.", False), START, END])
def _compliance(ctx, a):
    return _call(ctx, "compliance_audit", "compliance_audit", a)


@tool("spill_evidence", "Everything on record about one spill detection: the AI detection, formal corrections, informal notes by different people, and the repair. Use for 'was that spill real?'.",
      [("asset_id", "string", "Well ID.", True), ("date", "string", "Date of the inspection YYYY-MM-DD (the year of the as-of date if the user gives only day and month).", False), ("inspection_id", "string", "Inspection ID if known.", False)])
def _spill_ev(ctx, a):
    return _call(ctx, "spill_evidence", "spill_evidence", a)


@tool("propose_correction", "Use when a user says a recorded value is wrong (a raw reading or the AI's spill estimate). Prepares a correction for the user to confirm; nothing is saved yet. Never say it is saved until the user confirms.",
      [("asset_id", "string", "Well ID.", True), ("date", "string", "Inspection date YYYY-MM-DD (omit for the latest inspection).", False), ("inspection_id", "string", "Inspection ID if known.", False),
       ("field", "string", "wellhead_temp_c, ambient_temp_c, spill_est_volume_bbl or spill_area_pct.", True), ("new_value", "number", "The corrected value.", True), ("reason", "string", "Why, in the user's words.", True)], writes=True)
def _propose_cor(ctx, a):
    return actions.propose_correction(ctx, a)


@tool("propose_rule", "Use when a user gives a rule for a whole well type or one well, e.g. 'for all T350 wells do a root-cause analysis after 2 repairs, not 3'. Prepares it for confirmation; it applies only to that scope.",
      [("scope_type", "string", "well_type or well.", True), ("scope_value", "string", "The well type (T350) or well ID.", True), ("key", "string", "rca_corrective_count (repairs that trigger a root-cause analysis).", True),
       ("value", "number", "The new threshold.", True), ("equipment_kind", "string", "Equipment the rule covers, e.g. pump_jack.", False), ("reason", "string", "Why, in the user's words.", False)], writes=True)
def _propose_rule(ctx, a):
    return actions.propose_rule(ctx, a)


@tool("add_shared_note", "Save something a user tells everyone about a well (e.g. 'WELL-0007 will be shut in from 17 Oct for a 10-day workover'). Shared knowledge: other users asking about the well will see it.",
      [("asset_id", "string", "Well ID.", True), ("text", "string", "The note in the user's words.", True), ("kind", "string", "planned_downtime or info.", False),
       ("valid_from", "string", "Start date YYYY-MM-DD.", False), ("valid_to", "string", "End date YYYY-MM-DD.", False), ("duration_days", "number", "Length in days when only a duration is given.", False)], writes=True)
def _add_note(ctx, a):
    return actions.add_shared_note(ctx, a)


@tool("check_claim", "Use when a user states the current state of a well ('WELL-0175 is running fine', 'WELL-0001 is back online since 14 Oct', 'it has been shut in since 14 Oct'). Checks it against the latest inspection and other users' statements, keeps every statement, and flags unconfirmed ones.",
      [("asset_id", "string", "Well ID.", True), ("asserted_state", "string", "producing (running/online) or not_producing (shut in/down).", True), ("claim_text", "string", "The user's statement verbatim.", True), ("since", "string", "Date it started, YYYY-MM-DD.", False)], writes=True)
def _check_claim(ctx, a):
    return actions.check_claim(ctx, a)


_BRIEF = {
    "well_status": "Is a well producing oil now? Latest inspection, inspector, reason if stopped.",
    "wells_not_producing": "Wells by current production status (default not producing), with reasons.",
    "inspection_series": "Weekly wellhead vs air temperature for one well (line chart).",
    "spills": "Real oil spills (corrected ones excluded): count, total bbl, list, locations.",
    "downtime": "Downtime days (7 per non-producing weekly inspection) for a well, area or field; group_by compares areas or types.",
    "downtime_ranking": "Top N wells by downtime.",
    "repair_costs": "Repair cost and count per well in a period; big scopes show the top N wells; group_by compares areas or types.",
    "spill_heatmap": "Spill counts by area and month.",
    "rca_candidates": "Wells needing a root-cause analysis (too many corrective repairs).",
    "well_context": "Notes, planned work and open repairs for one well.",
    "search_documents": "Search manuals, SOPs and repair reports.",
    "recall_discussed": "Wells this user discussed in earlier conversations.",
    "compliance_audit": "Rules broken / breaches / compliance. protocol=SR-02 for 'not contained within the SOP time limit', SR-01 for 'needed a report to the regulator', SR-03 cleanup verification, RC-04 violation response. One well also RC-02, root-cause analyses, shut-in records.",
    "spill_evidence": "Evidence for one spill detection: notes, corrections, repair.",
    "propose_correction": "User says a recorded value is wrong: prepare a correction for confirmation.",
    "propose_rule": "User gives a rule for a well type or well: prepare it for confirmation.",
    "add_shared_note": "Save a note everyone should see about a well (e.g. a planned shut-in).",
    "check_claim": "User states a well's current state: check it against records and others' statements.",
    "repairs": "Repairs and cost in a period, by equipment or type; most expensive first.",
    "regulatory_events": "Regulator events and fines in a period.",
    "inspection_gaps": "Wells inspected less often than the SOP allows, or not recently.",
    "long_downtime": "Wells not producing for more than N consecutive days.",
}
_PARAM = {
    "asset_id": None, "scope": "Well ID, area name, type (T350) or 'all'.", "period": "Phrase from the question, e.g. 'last 4 months', '2025'. For other windows pass start and end instead.", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD",
    "well_type": "e.g. T350", "weeks": None, "top_n": None, "wells": "Well IDs", "equipment_kind": "e.g. pump_jack, flowline", "query": None, "kind": None, "protocol": "SR-01, SR-02, SR-03 or RC-04",
    "date": "Inspection date YYYY-MM-DD", "inspection_id": None, "field": "wellhead_temp_c, ambient_temp_c, spill_est_volume_bbl or spill_area_pct", "new_value": None, "reason": "User's reason",
    "scope_type": "well_type or well", "scope_value": "T350 or a well ID", "key": "rca_corrective_count", "value": None, "text": "In the user's words", "valid_from": "YYYY-MM-DD", "valid_to": "YYYY-MM-DD",
    "duration_days": None, "group_by": None, "count": None, "topic": None, "state": "not_producing, producing or all", "maintenance_type": None, "event_type": None, "status": None, "max_days": None, "min_days": None, "asserted_state": "producing or not_producing", "claim_text": "User's statement verbatim", "since": "YYYY-MM-DD",
}
def _apply_brief() -> None:
    for _name, _desc in _BRIEF.items():
        if _name in REGISTRY:
            REGISTRY[_name].description = _desc

_STATEMENT_HINT = re.compile(r"\b(wrong|incorrect|correct(ion)?|re-?measured|measured|faulty|fyi|note for|from now on|going forward|is (running|back|shut)|has been (shut|down)|will be shut)\b", re.I)
_QUESTION_START = re.compile(r"^\s*(is|are|was|were|which|how|what|when|who|where|why|does|do|did|show|list|give|tell|compare|rank|can you (show|list|tell))\b", re.I)


def wants_write_tools(message: str) -> bool:
    """Send the write tools only when the message looks like a statement or correction, not a question."""
    m = (message or "").strip()
    if _STATEMENT_HINT.search(m):
        return True
    return not (m.endswith("?") or _QUESTION_START.match(m))


@tool("repairs", "Repairs and their cost in a period for a well/area/field, optionally one equipment kind or type (scheduled/corrective); most expensive first, cost by equipment.",
      [SCOPE, PERIOD, ("equipment_kind", "string", "pump_jack, flowline...", False), ("maintenance_type", "string", "scheduled or corrective", False), ("top_n", "integer", "rows to list", False), START, END])
def _repairs(ctx, a):
    return _call(ctx, "repairs", "repairs", a)


@tool("maintenance_record", "Who carried out one maintenance job/repair (technician name from the user records), cited to the job. Give the maintenance ID, or the inspection ID that triggered the repair. Says so when the technician is not recorded.",
      [("maintenance_id", "string", "Maintenance ID such as MNT-0155-002.", False), ("inspection_id", "string", "Inspection ID whose spill triggered the repair.", False)])
def _maintenance_record(ctx, a):
    return _call(ctx, "maintenance_record", "maintenance_record", a)


@tool("gas_response", "Gas-odor operator notes (gas smell, rotten-egg smell, H2S alarm) in a period and whether a field response (a repair job or a manual inspection on that well) started within the Operations SOP OPS-1 deadline; lists every report with Met/Missed.",
      [SCOPE, PERIOD, START, END])
def _gas_response(ctx, a):
    return _call(ctx, "gas_response", "gas_response", a)


@tool("regulatory_events","Regulator events (spill reports, notices of violation, site inspections) and fines in a period for a well/area/field.",
      [SCOPE, PERIOD, ("event_type", "string", "spill_report_filed, notice_of_violation, site_inspection or nov_response_filed", False), ("status", "string", "open or closed", False), START, END])
def _reg(ctx, a):
    return _call(ctx, "regulatory_events", "regulatory_events", a)


@tool("inspection_gaps", "Wells inspected less often than the SOP allows (RC-01) or not inspected recently.",
      [SCOPE, PERIOD, ("max_days", "integer", "allowed days between inspections (default from the SOP)", False), START, END])
def _gaps(ctx, a):
    return _call(ctx, "inspection_gaps", "inspection_gaps", a)


@tool("long_downtime", "Wells not producing for more than N consecutive days (RC-03 reporting limit), with the run dates.",
      [SCOPE, PERIOD, ("min_days", "integer", "limit in days (default from the SOP)", False), START, END])
def _longdt(ctx, a):
    return _call(ctx, "long_downtime", "long_downtime", a)


def declarations(include_writes: bool = True) -> list[types.Tool]:
    _apply_brief()
    decls = []
    for t in REGISTRY.values():
        if t.writes and not include_writes:
            continue
        props, required = {}, []
        for name, ptype, desc, req in t.params:
            d = _PARAM.get(name, desc)
            if ptype == "array":
                props[name] = types.Schema(type="ARRAY", items=types.Schema(type="STRING"), description=d)
            elif ptype == "number":
                props[name] = types.Schema(type="NUMBER", description=d)
            else:
                props[name] = types.Schema(type=ptype.upper(), description=d)
            if req:
                required.append(name)
        decls.append(types.FunctionDeclaration(
            name=t.name, description=t.description,
            parameters=types.Schema(type="OBJECT", properties=props, required=required or None) if props else None))
    return [types.Tool(function_declarations=decls)]


def run_tool(ctx: Ctx, name: str, args: dict) -> dict:
    t = REGISTRY.get(name)
    if t is None:
        return {"tool": name, "error": f"Unknown tool '{name}'."}
    try:
        return t.fn(ctx, dict(args or {}))
    except ToolError as e:
        return {"tool": name, "error": str(e)}
    except (ValueError, TypeError, KeyError) as e:
        return {"tool": name, "error": f"Could not run {name}: {type(e).__name__}: {e}"}
