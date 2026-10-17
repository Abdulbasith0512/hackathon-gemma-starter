"""Backend audit log of answer verification. A separate SQLite file from the dataset database and from the users' memory database.

Each answer the copilot gives is stored with the question, the answer as generated (the model's own wording, kept even when the verified
facts were shown instead), the answer as shown, the evidence it cited, the verification status and its reasons, the dataset version and the time.
The report deliberately leaves out user IDs, conversation IDs and anything from private memory.
"""

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS answer_audit (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  evaluation_id TEXT UNIQUE NOT NULL,
  conv_id TEXT, turn_id INTEGER,
  question TEXT NOT NULL,
  generated_answer TEXT, shown_answer TEXT,
  evidence_refs TEXT,
  status TEXT NOT NULL CHECK (status IN ('PASS','FAIL','NEEDS_REVIEW')),
  failure_reasons TEXT,
  checks TEXT, tools TEXT,
  dataset_version TEXT, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_status ON answer_audit(status);
"""


class AuditLog:
    """Opens the file only for the moment of each write or read, so no handle is left behind (the file can be moved, copied or deleted at any time)."""

    def __init__(self, path: Path | str, dataset_version: str = ""):
        self.path, self.dataset_version = str(path), dataset_version
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        with self._open() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _open(self):
        conn = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def close(self) -> None:
        pass

    def record(self, *, question: str, generated: str | None, shown: str | None, evidence_refs: list[str], verification: dict, tools: list[str],
               conv_id: str | None = None, turn_id: int | None = None) -> str:
        eid = "EV-" + uuid.uuid4().hex[:10].upper()
        with self.lock, self._open() as conn:
            conn.execute(
                "INSERT INTO answer_audit(evaluation_id,conv_id,turn_id,question,generated_answer,shown_answer,evidence_refs,status,failure_reasons,checks,tools,dataset_version,created_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (eid, conv_id, turn_id, question, generated, shown, json.dumps(evidence_refs), verification["status"], json.dumps(verification["reasons"]),
                 json.dumps(verification["checks"]), json.dumps(tools), self.dataset_version, datetime.now(timezone.utc).isoformat(timespec="seconds")))
        return eid

    def report(self, limit: int = 200) -> dict:
        """Totals, and every FAIL and NEEDS_REVIEW with its reasons. No user or conversation identifiers."""
        with self.lock, self._open() as conn:
            totals = {r["status"]: r["n"] for r in conn.execute("SELECT status, COUNT(*) n FROM answer_audit GROUP BY status")}
            versions = [r[0] for r in conn.execute("SELECT DISTINCT dataset_version FROM answer_audit ORDER BY dataset_version")]

            def rows(status):
                return [{"evaluation_id": r["evaluation_id"], "question": r["question"], "generated_answer": r["generated_answer"], "shown_answer": r["shown_answer"],
                         "reasons": json.loads(r["failure_reasons"] or "[]"), "evidence": json.loads(r["evidence_refs"] or "[]"), "tools": json.loads(r["tools"] or "[]"),
                         "dataset_version": r["dataset_version"], "created_at": r["created_at"]}
                        for r in conn.execute("SELECT * FROM answer_audit WHERE status=? ORDER BY seq DESC LIMIT ?", (status, int(limit)))]
            out = {"totals": {"PASS": totals.get("PASS", 0), "FAIL": totals.get("FAIL", 0), "NEEDS_REVIEW": totals.get("NEEDS_REVIEW", 0)}, "dataset_versions": versions,
                   "failed": rows("FAIL"), "needs_review": rows("NEEDS_REVIEW")}
        out["totals"]["total"] = sum(out["totals"].values())
        return out
