"""The copilot loop: Gemma chooses tools and explains their results; Python does the facts.

Gemma never calculates. Its final text is accepted only if every number and record ID in it also
appears in the tool results (the grounding check); otherwise the deterministic facts are shown
instead. Citations, flags and visuals always come from the tools, not from the model's text.
"""

import json
import os
import re
import threading
import time
from collections import deque
from dataclasses import dataclass

import gemma
from google.genai import types

from . import router
from . import tools as toolbox
from . import visuals
from .analyst import Analyst
from .tools import Ctx

MAX_ROUNDS = 5
SKIP_EXPLANATION_WAIT = 25.0   # seconds of quota wait we will spend on the optional wording step
MAX_TOOL_CALLS = 6             # per question
HISTORY_MESSAGES = 4

SYSTEM = """You are the Asset Intelligence Copilot for an oil-field operator. As-of ("today") date: {as_of}. User: {name} ({role}, {team}).
Rules:
1. Get every fact from the tools. Never calculate, estimate or recall numbers yourself. If no tool fits, say so.
2. Pass time phrases exactly as written ("last 4 months", "2025") in `period`, and area names as written.
3. Answer ONLY from tool results; copy numbers, names, dates and IDs exactly. Cite key records like [INS-0001-0203] (at most 3 per statement, only IDs from tool results).
4. One-sentence direct answer first, then short supporting bullets. Be concise; do not repeat tables, charts or cards (they are drawn for you).
5. Always state flags: corrected data (original kept), conflicts, unconfirmed claims, missing evidence ("no recorded reason"), stale recorded status. Never hide a disagreement or pick a side silently.
6. Tool error: explain plainly or ask one short question.
7. "Wells we discussed earlier": call recall_discussed first.
8. Earlier turns only help resolve references ("those wells"); never reuse an earlier well or area unless the user refers to it. For "the N wells we discussed", pass count=N to recall_discussed.
9. User says a value is wrong: propose_correction (never say saved before they confirm). Rule for a well type: propose_rule. Tells everyone something about a well: add_shared_note. States a well's current state: check_claim. Report any conflict returned.
{extra}"""

_ID = re.compile(r"\b(?:WELL|INS|MNT|REG|CTX|COR|SN|RULE|SR|RC|WS|U)-\d[\d-]*\b")
_NUM = re.compile(r"(?<![\w.#-])\d+(?:\.\d+)?")
_ANYNUM = re.compile(r"\d+(?:\.\d+)?")
_DATA_HINT = re.compile(r"\b(wells?|areas?|blocks?|spills?|downtime|down|repairs?|costs?|inspect\w*|producing|production|status|oil|reports?|regulator|rules?|breach\w*|violation\w*|fines?|notes?|correct\w*|maintenance|technicians?|carried out|measured|temperature|wellhead|map|chart|table|heat ?map|how many|which|show|list|compare|rank)\b|WELL-|\d", re.I)
_GREETING = re.compile(r"^\s*(hi|hello|hey|thanks|thank you|ok|okay|good (morning|afternoon|evening))\b[\s!.?]*$", re.I)


class GemmaLLM:
    """Gemma with a rolling input-token budget. The free tier allows 16,000 input tokens a minute;
    this waits (or lets the caller skip the optional explanation call) instead of failing."""

    def __init__(self, tpm: int | None = None):
        self.tpm = tpm or int(os.getenv("AHC_TPM", "13500"))
        self.window: deque = deque()
        self.lock = threading.Lock()

    @staticmethod
    def estimate(contents: list, tool_list: list, system: str) -> int:
        chars = len(system) + len(json.dumps([t.model_dump(exclude_none=True) for t in tool_list], default=str))
        for c in contents:
            for p in (c.parts or []):
                chars += len(str(p.text or ""))
                if p.function_call:
                    chars += len(json.dumps(dict(p.function_call.args or {}), default=str))
                if p.function_response:
                    chars += len(json.dumps(p.function_response.response, default=str))
        return int(chars / 3.3) + 50

    def _used(self) -> int:
        cutoff = time.time() - 60
        while self.window and self.window[0][0] < cutoff:
            self.window.popleft()
        return sum(t for _, t in self.window)

    def wait_needed(self, need: int) -> float:
        with self.lock:
            used = self._used()
            if used + need <= self.tpm:
                return 0.0
            freed = 0
            for ts, t in self.window:
                freed += t
                if used - freed + need <= self.tpm:
                    return max(0.0, ts + 60 - time.time()) + 0.5
            return 60.0

    def generate(self, contents: list, tool_list: list, system: str, force_call: bool = False):
        need = self.estimate(contents, tool_list, system)
        time.sleep(min(self.wait_needed(need), 70))
        resp = None
        waits = [6.0, 15.0]  # sustained server errors: the SDK retried within seconds; wait longer, at most twice more
        for attempt in range(3):
            try:
                resp = gemma.generate_with_tools(contents, tool_list, system, force_call)
                break
            except gemma.GemmaError as e:
                m = re.search(r"retry in ([\d.]+)s", str(e))
                if "429" in str(e) and m and attempt == 0:  # quota: wait as long as the API asks, once
                    time.sleep(min(float(m.group(1)) + 1, 70))
                    continue
                if re.search(r"\b50[0-4]\b", str(e)) and attempt < len(waits):
                    time.sleep(waits[attempt])
                    continue
                raise
        used = getattr(getattr(resp, "usage_metadata", None), "prompt_token_count", None) or need
        with self.lock:
            self.window.append((time.time(), used))
        return resp


def to_llm(res: dict) -> dict:
    """A compact view of a tool result for the model (no drawing specs)."""
    if "error" in res:
        return {"error": res["error"]}
    out = {"tool": res["tool"], "title": res.get("title"), "window": res.get("window"),
           "facts": [{"text": f["text"], "cites": f["cites"][:3]} for f in res["facts"][:10]],
           "flags": [{"type": f["type"], "text": f["text"]} for f in res["flags"][:6]]}
    table = (res.get("visuals") or {}).get("table")
    if table and table.get("rows"):
        out["table"] = {"columns": table["columns"], "rows": table["rows"][:8], "row_count": len(table["rows"])}
    if res.get("pending"):
        out["pending_confirmation"] = res["pending"]["preview"]
    data = json.dumps(res.get("data", {}), default=str)
    if len(data) < 500:
        out["data"] = res.get("data")
    return out


def evidence_blob(results: list[dict], question: str = "") -> str:
    parts = [question]
    for r in results:
        if "error" in r:
            continue
        parts.append(json.dumps({k: r.get(k) for k in ("title", "window", "data", "facts", "flags", "citations")}, default=str))
        for spec in (r.get("visuals") or {}).values():
            parts.append(json.dumps(spec, default=str))
        if r.get("pending"):
            parts.append(json.dumps(r["pending"], default=str))
    return re.sub(r"(?<=\d),(?=\d)", "", " ".join(parts))


_WORD_VALUES = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_WORD_VALUES.update({w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())})
_NUMWORDS = re.compile(
    r"\b((?:(?:" + "|".join(_WORD_VALUES) + r"|hundred|thousand|and)[\s-]+)*(?:" + "|".join(_WORD_VALUES) + r"|hundred|thousand))\b"
    r"(\s+(?:spills?|wells?|days?|repairs?|inspections?|breach(?:es)?|hours?|barrels?|bbl|weeks?|months?|events?|fines?|areas?|records?))?", re.I)


def _spelled_numbers(text: str) -> list[tuple[str, int, bool]]:
    """Numbers written as words: (phrase, value, followed_by_a_counted_noun)."""
    out = []
    for m in _NUMWORDS.finditer(text):
        total = current = 0
        for w in re.split(r"[\s-]+", m.group(1).lower()):
            if w in _WORD_VALUES:
                current += _WORD_VALUES[w]
            elif w == "hundred":
                current = (current or 1) * 100
            elif w == "thousand":
                total, current = total + (current or 1) * 1000, 0
        out.append((re.sub(r"^(?:and[\s-]+)+", "", m.group(1), flags=re.I), total + current, bool(m.group(2))))
    return out


def _names_in(text: str, names) -> list[str]:
    """Which of the given people's names the text mentions."""
    return [n for n in names if n and re.search(rf"(?<!\w){re.escape(n)}(?!\w)", text, re.I)]


def ground_check(answer: str, results: list[dict], question: str = "", names: tuple | list = ()) -> list[str]:
    """Numbers and record IDs in `answer` that no tool result (or the question) contains. Empty means grounded.

    IDs (including user IDs such as U-303) must appear exactly; numbers must appear as whole numbers (digits
    inside record IDs do not count). `names` are people's names that may not be mentioned unless the evidence
    names them, so a technician cannot be invented.
    Numbers spelled out in words are checked too when they are 20 or more, use 'hundred'/'thousand',
    or count something ("three wells"), so spelling a number out is not a way around the check.
    """
    blob = evidence_blob(results, question)
    allowed = set(_ANYNUM.findall(re.sub(r"(?<=\d),(?=\d)", "", _ID.sub(" ", blob))))
    allowed |= {str(v) for _p, v, _c in _spelled_numbers(blob)}
    text = re.sub(r"(?m)^\s*(?:\d+[.)]|[-*•])\s+", "", answer)
    bad = [cid for cid in set(_ID.findall(text)) if cid not in blob]
    bad += [n for n in _names_in(text, names) if n.lower() not in blob.lower()]
    for num in set(_NUM.findall(re.sub(r"(?<=\d),(?=\d)", "", _ID.sub(" ", text)))):
        if num not in allowed:
            bad.append(num)
    for phrase, value, counted in _spelled_numbers(text):
        if (value >= 20 or counted or re.search(r"hundred|thousand", phrase, re.I)) and str(value) not in allowed:
            bad.append(phrase.strip())
    return sorted(bad)


def deterministic_answer(results: list[dict]) -> str:
    lines = []
    for r in results:
        if "error" in r:
            lines.append(r["error"])
            continue
        for f in r["facts"]:
            cites = [c for c in dict.fromkeys(f["cites"]) if c and c not in f["text"]][:3]
            lines.append(f["text"] + (" [" + ", ".join(cites) + "]" if cites else ""))
        for fl in r["flags"]:
            if fl["type"] in ("conflict", "unconfirmed", "needs_confirmation"):
                lines.append(f"⚠ {fl['text']}")
    return "\n".join(lines)


@dataclass
class Agent:
    analyst: Analyst
    store: object
    llm: object = None
    extra_prompt: str = ""

    def __post_init__(self):
        self.llm = self.llm or GemmaLLM()

    def _system(self, user_id: str) -> str:
        u = self.analyst.users.get(user_id, {})
        team = self.analyst.users.get(user_id, {}).get("team_id", "")
        return SYSTEM.format(as_of=self.analyst.as_of_s, name=u.get("name", user_id), role=(u.get("role") or "user").replace("_", " "), team=team, extra=self.extra_prompt)

    def _run_routed(self, ctx: Ctx, routed: list, results: list, calls: list) -> None:
        for name, args in routed:
            res = toolbox.run_tool(ctx, name, {k: v for k, v in args.items() if v is not None})
            results.append(res)
            calls.append({"name": name, "args": args, "ok": "error" not in res, "error": res.get("error")})

    def _history(self, conv_id: str, user_id: str) -> list:
        msgs = self.store.messages(conv_id, user_id)[-HISTORY_MESSAGES:]
        return [types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part(text=m["content"])]) for m in msgs if m["content"]]

    def respond(self, user_id: str, conv_id: str | None, message: str, auto_confirm: bool = False) -> dict:
        if user_id not in self.analyst.users:
            raise ValueError(f"Unknown user '{user_id}'.")
        if conv_id:
            if self.store.conversation_owner(conv_id) != user_id:
                raise PermissionError("That conversation belongs to a different user.")
        else:
            conv_id = self.store.new_conversation(user_id, message[:60])
        ctx = Ctx(self.analyst, self.store, user_id, conv_id, auto_confirm, message)
        user_parts = [types.Part(text=message)]
        hint = None if toolbox.wants_write_tools(message) else router.route(self.analyst, message)
        if hint:  # a pattern suggestion the model may follow or ignore; it keeps the model on the specialised tool
            user_parts.append(types.Part(text="[Pattern hint, may be wrong: " + "; ".join(f"{n}({json.dumps({k: v for k, v in a.items() if v is not None})})" for n, a in hint) + "]"))
        contents = self._history(conv_id, user_id) + [types.Content(role="user", parts=user_parts)]
        user_msg_id = self.store.add_message(conv_id, user_id, "user", message)
        results, calls, final_text = [], [], None
        system, tool_list = self._system(user_id), toolbox.declarations(toolbox.wants_write_tools(message))
        skipped, down_note, cache, forced = False, None, {}, False
        for round_no in range(MAX_ROUNDS):
            unfinished = bool(results) and (results[-1].get("intermediate") or "error" in results[-1])  # a lookup step, or an error the model may fix
            if round_no > 0 and results and not unfinished and hasattr(self.llm, "wait_needed") and self.llm.wait_needed(self.llm.estimate(contents, tool_list, system)) > SKIP_EXPLANATION_WAIT:
                skipped = True  # the tools already answered; do not stall on the optional wording step
                break
            try:
                use_force, forced = forced, False  # forcing a call applies to one retry only
                resp = self.llm.generate(contents, tool_list, system, force_call=True) if use_force else self.llm.generate(contents, tool_list, system)
            except gemma.GemmaError as e:
                if results:  # the tools already answered; only the wording step failed
                    skipped, down_note = True, f"The model could not be reached for the wording step ({str(e)[:90]})."
                    break
                routed = router.route(self.analyst, message)
                if not routed:
                    raise
                down_note = f"The model could not be reached ({str(e)[:90]}), so this was answered with built-in question patterns and the same verified tools."
                self._run_routed(ctx, routed, results, calls)
                break
            cand = resp.candidates[0] if resp.candidates else None
            parts = list(cand.content.parts) if cand and cand.content and cand.content.parts else []
            fcs = [p.function_call for p in parts if getattr(p, "function_call", None)]
            if not fcs:
                final_text = "".join(p.text for p in parts if getattr(p, "text", None) and not getattr(p, "thought", False)).strip()
                if not results and _DATA_HINT.search(message) and not _GREETING.match(message):
                    # Answering a data question without consulting the records is never accepted.
                    routed = router.route(self.analyst, message)
                    if routed:
                        down_note = "The model answered without consulting the records, so the verified tools were used instead."
                        self._run_routed(ctx, routed, results, calls)
                        final_text = None
                        break
                    if not use_force and round_no == 0:
                        forced = True  # one more try, this time requiring a tool call
                        continue
                    if re.search(r"\d", final_text) or _ID.search(final_text) or _names_in(final_text, [u["name"] for u in self.analyst.users.values() if u.get("name")]):
                        final_text = None  # numbers, record IDs and people's names need records behind them
                break
            contents.append(cand.content)
            answers = []
            for fc in fcs:
                args = dict(fc.args or {})
                key = fc.name + json.dumps(args, sort_keys=True, default=str)
                if key in cache:  # the model repeated itself: reuse the result, do not show it twice
                    res = cache[key]
                elif len(results) >= MAX_TOOL_CALLS:  # a runaway loop of lookups: stop and answer from what we have
                    res = {"tool": fc.name, "error": "Too many tool calls for one question; answer from the results already returned."}
                else:
                    res = cache[key] = toolbox.run_tool(ctx, fc.name, args)
                    results.append(res)
                    calls.append({"name": fc.name, "args": args, "ok": "error" not in res, "error": res.get("error")})
                answers.append(types.Part.from_function_response(name=fc.name, response=to_llm(res)))
            contents.append(types.Content(role="user", parts=answers))
        return self._finish(ctx, message, user_msg_id, results, calls, final_text, skipped, down_note)

    def _finish(self, ctx: Ctx, message: str, user_msg_id: int, results: list[dict], calls: list[dict], final_text: str | None, skipped: bool = False, down_note: str | None = None) -> dict:
        ok = [r for r in results if "error" not in r]
        warnings = []
        source = "model"
        if final_text:
            people = [u["name"] for u in self.analyst.users.values() if u.get("name")] if any(r.get("tool") == "maintenance_record" for r in ok) else []
            ungrounded = ground_check(final_text, ok, message, people)
            if ungrounded:
                warnings.append("The model's wording contained values not found in the records (" + ", ".join(ungrounded[:6]) + "); showing the verified facts instead.")
                final_text = None
        if not final_text:
            final_text = deterministic_answer(results) or "I could not find an answer in the records."
            source = "verified facts"
            if down_note:
                warnings.append(down_note)
            elif skipped:
                warnings.append("Showing the verified facts directly: the model rate limit was nearly used up, so the wording step was skipped.")
        blocks, citations, flags, seen_c = [], [], [], set()
        for r in ok:
            for c in r.get("citations", []):
                if c["id"] not in seen_c:
                    seen_c.add(c["id"])
                    citations.append(c)
            flags += r.get("flags", [])
            if r.get("visuals"):
                chosen = visuals.choose(message, r)
                if chosen["spec"] is not None:
                    blocks.append({"tool": r["tool"], "title": r.get("title"), "window": r.get("window"), "visual": chosen, "facts": r.get("facts", [])})
        pending = [r["pending"] for r in ok if r.get("pending")]
        errors = [r["error"] for r in results if "error" in r]
        uniq_flags, seen_f = [], set()
        for f in flags:
            k = (f["type"], f["text"])
            if k not in seen_f:
                seen_f.add(k)
                uniq_flags.append(f)
        payload = {"answer": final_text, "answer_source": source, "blocks": blocks, "citations": citations, "flags": uniq_flags, "pending": pending,
                   "tool_calls": calls, "errors": errors, "warnings": warnings, "as_of": self.analyst.as_of_s}
        msg_id = self.store.add_message(ctx.conv_id, ctx.user_id, "assistant", final_text, payload)
        ents = []
        for r in ok:
            ents += [("well", w) for w in (r.get("entities") or {}).get("wells", [])]
        if ents:
            self.store.record_entities(ctx.user_id, ctx.conv_id, msg_id, list(dict.fromkeys(ents)), message[:200])
        payload.update({"conv_id": ctx.conv_id, "message_id": msg_id, "user_message_id": user_msg_id})
        return payload
