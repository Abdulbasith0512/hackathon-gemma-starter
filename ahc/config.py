"""Settings. Everything is environment-driven so a new dataset loads without code changes.

  AHC_DATA_DIRS  one or more dataset roots, separated by ';' or ','. A root may be the
                 sample-data folder itself or its parent. Later roots extend/override earlier ones.
  AHC_AS_OF      the reference "today" (YYYY-MM-DD)
  AHC_DB         generated, rebuildable dataset database
  AHC_MEMORY_DB  persistent memory: corrections, rules, shared notes, per-user conversations
"""

import os
import re
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# The official Q6 answer for the sample dataset uses 16 Oct 2026 as "today".
DEFAULT_AS_OF = "2026-10-16"


def parse_date(value: str) -> date:
    return date.fromisoformat(value.strip())


def get_as_of() -> date:
    raw = os.getenv("AHC_AS_OF", "").strip()
    return parse_date(raw) if raw else parse_date(DEFAULT_AS_OF)


def _resolve_root(path: Path) -> Path:
    """Accept either the dataset folder (fleet/ + assets/) or its parent containing sample-data/."""
    if (path / "fleet").is_dir() or (path / "assets").is_dir():
        return path
    for child in sorted(path.glob("*")):
        if child.is_dir() and ((child / "fleet").is_dir() or (child / "assets").is_dir()):
            return child
    return path


def get_data_roots() -> list[Path]:
    raw = os.getenv("AHC_DATA_DIRS", "").strip()
    parts = [p.strip() for p in re.split(r"[;,]", raw) if p.strip()] if raw else []
    roots = [Path(p).expanduser() for p in parts] or [DATA_DIR / "sample-data"]
    return [_resolve_root(r) for r in roots]


def get_db_path() -> Path:
    return Path(os.getenv("AHC_DB", "").strip() or DATA_DIR / "ahc.sqlite3")


def get_memory_db_path() -> Path:
    return Path(os.getenv("AHC_MEMORY_DB", "").strip() or DATA_DIR / "ahc_memory.sqlite3")
