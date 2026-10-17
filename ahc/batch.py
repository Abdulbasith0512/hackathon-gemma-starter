"""Run a list of questions through the copilot and write the answers (the "results" page).

    python -m ahc.batch questions/sample_scenarios.json --out results/sample-results.md

Question file: a JSON list of {"id", "user", "chat", "text"}. `user` is a name or user ID; items that
share a `chat` label continue the same conversation, a new label is a new chat. Corrections and
rules are saved automatically (the confirm step is for people in the UI). Memory starts empty
unless --memory points at an existing store, so runs are repeatable.
"""

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

import gemma

from . import config
from .server import Runtime


def resolve_user(users: dict, who: str) -> str:
    if who in users:
        return who
    for u in users.values():
        if u["name"].lower() == who.lower():
            return u["user_id"]
    raise SystemExit(f"Unknown user '{who}'. Known: " + ", ".join(u["name"] for u in users.values()))


def md_table(spec: dict, limit: int = 40) -> str:
    rows = spec["rows"][:limit]
    head = "| " + " | ".join(str(c) for c in spec["columns"]) + " |\n|" + "---|" * len(spec["columns"]) + "\n"
    body = "\n".join("| " + " | ".join("" if c is None else str(c).replace("|", "/") for c in r) + " |" for r in rows)
    return head + body + (f"\n\n_{len(spec['rows']) - limit} more rows not shown_" if len(spec["rows"]) > limit else "")


def render(item: dict, out: dict, seconds: float) -> str:
    lines = [f"### {item.get('id', '')} — {item['user']}: {item['text']}", ""]
    if out.get("error"):
        return "\n".join(lines + [f"**Error:** {out['error']}", ""])
    lines += [out["answer"], ""]
    for b in out.get("blocks", []):
        v = b["visual"]
        lines.append(f"**Visual: {v['kind']}** ({b['title']}" + (f", {b['window']['label']}" if b.get("window") else "") + ")")
        spec = v["specs"].get("table") or v["spec"]
        if spec and spec.get("rows") is not None and "columns" in spec:
            lines += ["", md_table(spec), ""]
        elif v["kind"] == "bar":
            lines += ["", ", ".join(f"{l}: {x}" for l, x in zip(v["spec"]["labels"], v["spec"]["values"])), ""]
    if out.get("flags"):
        lines += ["**Signals:** " + "; ".join(f"{f['type']}: {f['text']}" for f in out["flags"][:8]), ""]
    if out.get("citations"):
        lines += ["**Evidence:** " + ", ".join(c["id"] for c in out["citations"][:30]) + (" …" if len(out["citations"]) > 30 else ""), ""]
    v = out.get("verification") or {}
    if v:
        lines.append(f"**Verification: {v['status']}**" + (" — " + " ".join(v["reasons"][:3]) if v.get("reasons") else " — numbers and records recomputed from the dataset") + (f" ({v['evaluation_id']})" if v.get("evaluation_id") else ""))
    lines.append(f"_tools: {', '.join(c['name'] for c in out.get('tool_calls', []))} · answer: {out['answer_source']} · {seconds:.1f}s_")
    if out.get("warnings"):
        lines.append("_" + " ".join(out["warnings"]) + "_")
    return "\n".join(lines + [""])


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Run questions through the copilot")
    ap.add_argument("questions")
    ap.add_argument("--out", default="results/results.md")
    ap.add_argument("--memory", help="memory database (default: a fresh temporary one)")
    ap.add_argument("--only", help="comma-separated question ids to run")
    args = ap.parse_args(argv)
    items = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    if args.only:
        keep = {s.strip() for s in args.only.split(",")}
        items = [i for i in items if str(i.get("id")) in keep]
    memory = Path(args.memory) if args.memory else Path(tempfile.mkdtemp()) / "memory.sqlite3"
    gemma.get_client()
    rt = Runtime(config.get_data_roots(), config.get_db_path(), memory, config.get_as_of())
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    chats: dict[str, str] = {}
    results, md = [], ["# Copilot results", "", f"Dataset roots: {', '.join(str(r) for r in rt.roots)} · as-of {rt.as_of} · model {gemma.get_model()} · thinking {gemma.get_thinking()}", ""]
    for item in items:
        with rt.session() as A:
            uid = resolve_user(A.users, item["user"])
            key = f"{uid}:{item.get('chat', item.get('id'))}"
            t0 = time.time()
            try:
                out = rt.agent(A).respond(uid, chats.get(key), item["text"], auto_confirm=True)
                chats[key] = out["conv_id"]
            except gemma.GemmaError as e:
                out = {"error": str(e)}
            seconds = time.time() - t0
        print(f"[{item.get('id', '?')}] {item['user']}: {item['text'][:70]}  ({seconds:.1f}s)" + (f"  ERROR {out['error'][:80]}" if out.get("error") else ""), flush=True)
        md.append(render(item, out, seconds))
        results.append({"id": item.get("id"), "user": item["user"], "text": item["text"], "seconds": round(seconds, 1), **{k: out.get(k) for k in ("answer", "answer_source", "tool_calls", "flags", "warnings", "error", "verification")},
                        "citations": [c["id"] for c in out.get("citations", [])], "visuals": [b["visual"]["kind"] for b in out.get("blocks", [])]})
        out_path.write_text("\n".join(md), encoding="utf-8")
        out_path.with_suffix(".json").write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {out_path} and {out_path.with_suffix('.json')}")


if __name__ == "__main__":
    main()
