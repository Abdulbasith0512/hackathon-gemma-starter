"""FastAPI server + static front-end for the copilot.

    python -m ahc            # http://127.0.0.1:8000

Private memory is enforced here: a conversation is only readable by its owner, and the user ID
used for every private lookup comes from the request body/query validated against that owner.
"""

import argparse
import logging
import os
import sys
import threading
from contextlib import contextmanager
from datetime import date

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import gemma

from . import config, db, evidence
from . import ingest as ingest_mod
from . import rules as rules_mod
from .agent import Agent
from .analyst import Analyst
from .store import Store

log = logging.getLogger("ahc")
WEB = config.PROJECT_ROOT / "web"


class ChatIn(BaseModel):
    user_id: str
    message: str
    conv_id: str | None = None
    auto_confirm: bool = False


class ActionIn(BaseModel):
    user_id: str


class SettingsIn(BaseModel):
    as_of: str


class Runtime:
    """Shared state: the dataset database, the persistent memory store, rules and the as-of date."""

    def __init__(self, roots, db_path, memory_path, as_of: date, llm=None):
        self.roots, self.db_path = list(roots), db_path
        self.stats = ingest_mod.ingest(self.roots, db_path)
        self.store = Store(memory_path)
        conn = db.connect(db_path)
        self.rules = rules_mod.load_rules(conn)
        conn.close()
        self.as_of, self.llm = as_of, llm
        self.lock = threading.Lock()

    @contextmanager
    def session(self):
        conn = db.connect(self.db_path)
        try:
            yield Analyst(conn, self.rules, self.store, self.as_of)
        finally:
            conn.close()

    def agent(self, analyst: Analyst) -> Agent:
        if self.llm is None:
            from .agent import GemmaLLM
            self.llm = GemmaLLM()
        return Agent(analyst, self.store, self.llm)


def suggestions(A: Analyst) -> list[str]:
    """Starter prompts built from the loaded dataset (no hardcoded IDs or names)."""
    wells = sorted(A.wells)
    areas = sorted(A.areas.values(), key=lambda a: a["name"] or "")
    if not wells or not areas:
        return []
    ref = A.c.execute("SELECT asset_id FROM inspections WHERE spill_detected=1 GROUP BY asset_id ORDER BY COUNT(*) DESC, asset_id LIMIT 1").fetchone()
    well = ref["asset_id"] if ref else wells[0]
    area = areas[-1]["name"]
    return [
        f"Is {well} producing oil right now? When was it last inspected, and by whom?",
        f"Which 3 wells in {area} had the most downtime in the last 4 months? Show a bar chart.",
        f"How many oil spills has {well} had in the last 4 years, and how much oil in total? List them in a table.",
        f"Which wells in {area} are not producing oil right now, and why? Show them in a table.",
        "Show a heatmap of 2026 spills by geographic area and month.",
    ]


def create_app(roots=None, db_path=None, memory_path=None, as_of: date | None = None, llm=None) -> FastAPI:
    rt = Runtime(roots or config.get_data_roots(), db_path or config.get_db_path(), memory_path or config.get_memory_db_path(), as_of or config.get_as_of(), llm)
    app = FastAPI(title="Asset Intelligence Copilot")
    app.state.rt = rt

    @app.get("/api/bootstrap")
    def bootstrap():
        with rt.session() as A:
            try:
                model, thinking = gemma.get_model(), gemma.get_thinking()
            except gemma.GemmaError as e:
                model, thinking = gemma.get_model(), f"invalid: {e}"
            types_in_data = sorted({w["well_type"] for w in A.wells.values() if w["well_type"]})
            warnings = [f"No production-temperature rule was found in the manuals for well type {t}; its wells cannot be classified as producing or not." for t in types_in_data if rt.rules.get("production_delta_c", t) is None]
            warnings += [f"Rule '{r.key}' was not found in the documents; a fallback default is used." for r in rt.rules.all() if r.fallback]
            if rt.stats.get("issue_count"):
                warnings.append(f"{rt.stats['issue_count']} data issue(s) while loading, e.g. " + "; ".join(rt.stats.get("issues", [])[:2]))
            return {"as_of": rt.as_of.isoformat(), "stats": rt.stats, "model": model, "thinking": thinking, "warnings": warnings,
                    "users": sorted(A.users.values(), key=lambda u: u["user_id"]),
                    "areas": list(A.areas.values()), "well_count": len(A.wells), "suggestions": suggestions(A),
                    "rules": [r.as_dict() for r in rt.rules.all()]}

    @app.post("/api/chat")
    def chat(body: ChatIn):
        message = body.message.strip()
        if not message:
            raise HTTPException(400, "Type a question first.")
        with rt.session() as A:
            if body.user_id not in A.users:
                raise HTTPException(400, f"Unknown user '{body.user_id}'.")
            try:
                return rt.agent(A).respond(body.user_id, body.conv_id, message, body.auto_confirm)
            except PermissionError as e:
                raise HTTPException(403, str(e))
            except gemma.GemmaError as e:
                return JSONResponse({"error": str(e), "retryable": True, "conv_id": body.conv_id}, status_code=200)

    @app.get("/api/conversations")
    def conversations(user_id: str):
        return rt.store.conversations(user_id)

    @app.get("/api/conversations/{conv_id}")
    def conversation(conv_id: str, user_id: str):
        if rt.store.conversation_owner(conv_id) != user_id:
            raise HTTPException(403, "That conversation belongs to a different user.")
        return rt.store.messages(conv_id, user_id)

    @app.get("/api/evidence")
    def get_evidence(ref: str = Query(...)):
        with rt.session() as A:
            res = evidence.resolve(A, ref)
        if not res:
            raise HTTPException(404, f"No record or document found for '{ref}'.")
        return res

    @app.get("/api/lineage/inspections")
    def lineage_inspections(ids: str = Query(..., description="comma-separated inspection IDs")):
        wanted = [i.strip() for i in ids.split(",") if i.strip()]
        if not wanted:
            raise HTTPException(400, "Give at least one inspection ID.")
        if len(wanted) > 500:
            raise HTTPException(400, "At most 500 inspection IDs at a time.")
        with rt.session() as A:
            rows = A.lineage_rows(wanted)
        return {"rows": rows, "missing": sorted(set(wanted) - {r["inspection_id"] for r in rows})}

    @app.get("/api/audit")
    def audit():
        with rt.session() as A:
            return {"corrections": rt.store.all_corrections(), "rules": rt.store.all_scoped_rules(), "shared_notes": rt.store.all_shared_notes(),
                    "users": {u["user_id"]: u["name"] for u in A.users.values()}}

    @app.post("/api/settings")
    def settings(body: SettingsIn):
        try:
            rt.as_of = date.fromisoformat(body.as_of)
        except ValueError:
            raise HTTPException(400, "Use a date like 2026-10-16.")
        return {"as_of": rt.as_of.isoformat()}

    @app.post("/api/actions/{action_id}/{decision}")
    def action(action_id: str, decision: str, body: ActionIn):
        from . import actions
        if decision not in ("confirm", "cancel"):
            raise HTTPException(404, "Unknown decision.")
        with rt.session() as A:
            try:
                return actions.decide(A, rt.store, rt.agent(A), body.user_id, action_id, decision == "confirm")
            except PermissionError as e:
                raise HTTPException(403, str(e))
            except LookupError as e:
                raise HTTPException(404, str(e))
            except ValueError as e:
                raise HTTPException(400, str(e))

    @app.get("/")
    def index():
        return FileResponse(WEB / "index.html")

    app.mount("/static", StaticFiles(directory=str(WEB)), name="static")
    return app


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Asset Intelligence Copilot")
    ap.add_argument("--host", default=os.getenv("AHC_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.getenv("AHC_PORT", "8000")))
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        gemma.get_client()
    except gemma.GemmaError as e:
        sys.exit(f"Configuration error: {e}")
    try:
        app = create_app()
    except FileNotFoundError as e:
        sys.exit(f"Dataset error: {e}")
    rt = app.state.rt
    s = rt.stats
    log.info("Dataset: %s wells, %s inspections, %s repairs, %s reports%s | as-of %s | model %s",
             s["wells"], s["inspections"], s["maintenance"], s["reports"], " (cached)" if s.get("reused") else "", rt.as_of, gemma.get_model())
    log.info("Open http://%s:%s", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
