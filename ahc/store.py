"""Persistent, auditable memory (separate from the rebuildable dataset database).

Shared (all users):  corrections (originals kept), scoped rules, shared notes and claims.
Private (one user):  conversations, messages, and the entities each user discussed.

Isolation rule: every private read takes `user_id` from the server session and binds it in
SQL. The model never supplies a user ID, so one user cannot be made to read another's history.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS corrections (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, correction_id TEXT UNIQUE,
  target_type TEXT, target_id TEXT, asset_id TEXT, field TEXT,
  original_value TEXT, previous_value TEXT, new_value TEXT,
  reason TEXT, author_user_id TEXT, created_at TEXT,
  scope_type TEXT, scope_value TEXT, status TEXT, supersedes_id TEXT, source TEXT
);
CREATE INDEX IF NOT EXISTS idx_cor_target ON corrections(target_id, status);
CREATE TABLE IF NOT EXISTS scoped_rules (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, rule_id TEXT UNIQUE,
  scope_type TEXT, scope_value TEXT, key TEXT, equipment_kind TEXT,
  value REAL, unit TEXT, reason TEXT, author_user_id TEXT, created_at TEXT, status TEXT, source_text TEXT
);
CREATE TABLE IF NOT EXISTS shared_notes (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, note_id TEXT UNIQUE,
  asset_id TEXT, kind TEXT, text TEXT, author_user_id TEXT, created_at TEXT,
  valid_from TEXT, valid_to TEXT, status TEXT, verdict TEXT, related_ids TEXT
);
CREATE INDEX IF NOT EXISTS idx_sn_asset ON shared_notes(asset_id);
CREATE TABLE IF NOT EXISTS conversations (
  conv_id TEXT PRIMARY KEY, user_id TEXT, title TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS messages (
  msg_id INTEGER PRIMARY KEY AUTOINCREMENT, conv_id TEXT, user_id TEXT, role TEXT,
  content TEXT, payload TEXT, created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conv_id);
CREATE TABLE IF NOT EXISTS discussed (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, conv_id TEXT, msg_id INTEGER,
  created_at TEXT, entity_type TEXT, entity_id TEXT, topic TEXT
);
CREATE INDEX IF NOT EXISTS idx_disc_user ON discussed(user_id, created_at);
CREATE TABLE IF NOT EXISTS pending_actions (
  action_id TEXT PRIMARY KEY, user_id TEXT, conv_id TEXT, kind TEXT, payload TEXT,
  created_at TEXT, status TEXT
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: Path | str):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    # ---- helpers -------------------------------------------------------
    def _rows(self, sql: str, params: tuple = ()) -> list[dict]:
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    @staticmethod
    def _load(row: dict, *cols: str) -> dict:
        for c in cols:
            if row.get(c) is not None:
                try:
                    row[c] = json.loads(row[c])
                except (TypeError, ValueError):
                    pass
        return row

    # ---- corrections (shared) ------------------------------------------
    def active_corrections(self) -> dict[str, dict[str, dict]]:
        """{inspection_id: {field: correction}} for corrections in force."""
        out: dict[str, dict[str, dict]] = {}
        for r in self._rows("SELECT * FROM corrections WHERE status='active' ORDER BY seq"):
            self._load(r, "original_value", "previous_value", "new_value")
            out.setdefault(r["target_id"], {})[r["field"]] = r
        return out

    def add_correction(self, *, target_id: str, asset_id: str, field: str, original, previous, new, reason: str,
                       author_user_id: str, target_type: str = "inspection", scope_type: str = "record",
                       scope_value: str | None = None, source: str = "chat") -> dict:
        """Save a correction. The dataset's original value is kept; an earlier correction of the
        same field is marked superseded (kept in history), never deleted."""
        prior = self.conn.execute("SELECT correction_id FROM corrections WHERE target_id=? AND field=? AND status='active'", (target_id, field)).fetchone()
        if prior:
            self.conn.execute("UPDATE corrections SET status='superseded' WHERE correction_id=?", (prior["correction_id"],))
        cur = self.conn.execute(
            "INSERT INTO corrections(target_type,target_id,asset_id,field,original_value,previous_value,new_value,reason,author_user_id,created_at,scope_type,scope_value,status,supersedes_id,source)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (target_type, target_id, asset_id, field, json.dumps(original), json.dumps(previous), json.dumps(new), reason,
             author_user_id, now(), scope_type, scope_value or target_id, "active", prior["correction_id"] if prior else None, source))
        cid = f"COR-{cur.lastrowid:04d}"
        self.conn.execute("UPDATE corrections SET correction_id=? WHERE seq=?", (cid, cur.lastrowid))
        return self.get_correction(cid)

    def get_correction(self, correction_id: str) -> dict | None:
        rows = self._rows("SELECT * FROM corrections WHERE correction_id=?", (correction_id,))
        return self._load(rows[0], "original_value", "previous_value", "new_value") if rows else None

    def corrections_for(self, target_id: str) -> list[dict]:
        return [self._load(r, "original_value", "previous_value", "new_value") for r in self._rows("SELECT * FROM corrections WHERE target_id=? ORDER BY seq", (target_id,))]

    def all_corrections(self) -> list[dict]:
        return [self._load(r, "original_value", "previous_value", "new_value") for r in self._rows("SELECT * FROM corrections ORDER BY seq DESC")]

    # ---- scoped rules (shared) -------------------------------------------
    def add_scoped_rule(self, *, scope_type: str, scope_value: str, key: str, value: float, unit: str, reason: str,
                        author_user_id: str, equipment_kind: str | None = None, source_text: str = "") -> dict:
        if scope_type not in ("well_type", "well"):
            raise ValueError("A rule is scoped to a well type or a single well.")
        self.conn.execute("UPDATE scoped_rules SET status='superseded' WHERE scope_type=? AND scope_value=? AND key=? AND COALESCE(equipment_kind,'')=COALESCE(?, '') AND status='active'",
                          (scope_type, scope_value, key, equipment_kind))
        cur = self.conn.execute(
            "INSERT INTO scoped_rules(scope_type,scope_value,key,equipment_kind,value,unit,reason,author_user_id,created_at,status,source_text) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (scope_type, scope_value, key, equipment_kind, value, unit, reason, author_user_id, now(), "active", source_text))
        rid = f"RULE-{cur.lastrowid:04d}"
        self.conn.execute("UPDATE scoped_rules SET rule_id=? WHERE seq=?", (rid, cur.lastrowid))
        return self._rows("SELECT * FROM scoped_rules WHERE rule_id=?", (rid,))[0]

    def scoped_rule(self, key: str, well_type: str | None, asset_id: str | None, equipment_kind: str | None = None) -> dict | None:
        """Most specific active rule: a single-well rule beats a well-type rule."""
        rows = self._rows("SELECT * FROM scoped_rules WHERE key=? AND status='active' ORDER BY seq DESC", (key,))
        for scope_type, scope_value in (("well", asset_id), ("well_type", well_type)):
            for r in rows:
                if r["scope_type"] == scope_type and r["scope_value"] == scope_value and (r["equipment_kind"] in (None, equipment_kind)):
                    return r
        return None

    def all_scoped_rules(self) -> list[dict]:
        return self._rows("SELECT * FROM scoped_rules ORDER BY seq DESC")

    # ---- shared notes and claims -----------------------------------------
    def add_shared_note(self, *, asset_id: str, kind: str, text: str, author_user_id: str, valid_from: str | None = None,
                        valid_to: str | None = None, status: str = "recorded", verdict: dict | None = None,
                        related_ids: list[str] | None = None) -> dict:
        cur = self.conn.execute(
            "INSERT INTO shared_notes(asset_id,kind,text,author_user_id,created_at,valid_from,valid_to,status,verdict,related_ids) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (asset_id, kind, text, author_user_id, now(), valid_from, valid_to, status, json.dumps(verdict) if verdict else None, json.dumps(related_ids or [])))
        nid = f"SN-{cur.lastrowid:04d}"
        self.conn.execute("UPDATE shared_notes SET note_id=? WHERE seq=?", (nid, cur.lastrowid))
        return self.get_shared_note(nid)

    def get_shared_note(self, note_id: str) -> dict | None:
        rows = self._rows("SELECT * FROM shared_notes WHERE note_id=?", (note_id,))
        return self._load(rows[0], "verdict", "related_ids") if rows else None

    def shared_notes_for(self, asset_id: str) -> list[dict]:
        return [self._load(r, "verdict", "related_ids") for r in self._rows("SELECT * FROM shared_notes WHERE asset_id=? ORDER BY seq", (asset_id,))]

    def all_shared_notes(self) -> list[dict]:
        return [self._load(r, "verdict", "related_ids") for r in self._rows("SELECT * FROM shared_notes ORDER BY seq DESC")]

    def update_shared_note_status(self, note_id: str, status: str) -> None:
        self.conn.execute("UPDATE shared_notes SET status=? WHERE note_id=?", (status, note_id))

    # ---- private conversations ---------------------------------------------
    def new_conversation(self, user_id: str, title: str = "") -> str:
        conv_id = f"CV-{uuid.uuid4().hex[:8]}"
        self.conn.execute("INSERT INTO conversations VALUES (?,?,?,?)", (conv_id, user_id, title, now()))
        return conv_id

    def conversation_owner(self, conv_id: str) -> str | None:
        r = self.conn.execute("SELECT user_id FROM conversations WHERE conv_id=?", (conv_id,)).fetchone()
        return r["user_id"] if r else None

    def conversations(self, user_id: str) -> list[dict]:
        return self._rows("SELECT * FROM conversations WHERE user_id=? ORDER BY created_at DESC", (user_id,))

    def add_message(self, conv_id: str, user_id: str, role: str, content: str, payload: dict | None = None) -> int:
        cur = self.conn.execute("INSERT INTO messages(conv_id,user_id,role,content,payload,created_at) VALUES (?,?,?,?,?,?)",
                                (conv_id, user_id, role, content, json.dumps(payload) if payload else None, now()))
        return cur.lastrowid

    def messages(self, conv_id: str, user_id: str) -> list[dict]:
        return [self._load(r, "payload") for r in self._rows("SELECT * FROM messages WHERE conv_id=? AND user_id=? ORDER BY msg_id", (conv_id, user_id))]

    def record_entities(self, user_id: str, conv_id: str, msg_id: int, entities: list[tuple[str, str]], topic: str) -> None:
        for etype, eid in entities:
            self.conn.execute("INSERT INTO discussed(user_id,conv_id,msg_id,created_at,entity_type,entity_id,topic) VALUES (?,?,?,?,?,?,?)",
                              (user_id, conv_id, msg_id, now(), etype, eid, topic))

    def recall(self, user_id: str, exclude_conv_id: str | None = None, entity_type: str = "well") -> list[dict]:
        """This user's earlier discussions, newest first: [{conv_id, msg_id, topic, when, entities}]."""
        rows = self._rows("SELECT * FROM discussed WHERE user_id=? AND entity_type=? AND (? IS NULL OR conv_id<>?) ORDER BY msg_id DESC",
                          (user_id, entity_type, exclude_conv_id, exclude_conv_id))
        groups: dict[int, dict] = {}
        for r in rows:
            g = groups.setdefault(r["msg_id"], {"conv_id": r["conv_id"], "msg_id": r["msg_id"], "topic": r["topic"], "when": r["created_at"], "entities": []})
            g["entities"].append(r["entity_id"])
        return list(groups.values())

    # ---- pending actions (confirm-before-save) -----------------------------
    def create_pending(self, user_id: str, conv_id: str, kind: str, payload: dict) -> str:
        action_id = f"ACT-{uuid.uuid4().hex[:8]}"
        self.conn.execute("INSERT INTO pending_actions VALUES (?,?,?,?,?,?,?)", (action_id, user_id, conv_id, kind, json.dumps(payload), now(), "pending"))
        return action_id

    def get_pending(self, action_id: str) -> dict | None:
        rows = self._rows("SELECT * FROM pending_actions WHERE action_id=?", (action_id,))
        return self._load(rows[0], "payload") if rows else None

    def resolve_pending(self, action_id: str, status: str) -> None:
        self.conn.execute("UPDATE pending_actions SET status=? WHERE action_id=?", (status, action_id))
