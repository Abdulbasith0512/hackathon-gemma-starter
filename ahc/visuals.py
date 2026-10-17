"""Pick the visual: honour an explicitly requested one, otherwise the one that fits the answer.

Every analyst result carries the specs it can render (`visuals`) and the one that fits best
(`natural`). Nothing here calls the model.
"""

import re

# Order matters: the most specific words first.
EXPLICIT = [
    ("heatmap", r"heat\s*-?\s*map"),
    ("line", r"line\s+(chart|graph|plot)|time[\s-]?series"),
    ("bar", r"bar\s+(chart|graph|plot)|\bbars?\b|column chart"),
    ("map", r"\bmap\b|\bpins?\b"),
    ("status_card", r"status\s+card|\bcard\b"),
    ("table", r"\btable\b|\btabular\b|\bspreadsheet\b"),
]
LABELS = {"table": "Table", "bar": "Bar chart", "line": "Line chart", "map": "Map", "heatmap": "Heatmap", "status_card": "Status card"}


def requested_visual(text: str) -> str | None:
    t = (text or "").lower()
    for kind, pattern in EXPLICIT:
        if re.search(pattern, t):
            return kind
    if re.search(r"\bchart\b|\bgraph\b|\bplot\b", t):
        return "chart"
    return None


def _bar_from_table(table: dict) -> dict | None:
    cols, rows = table.get("columns", []), table.get("rows", [])
    if not rows:
        return None
    for ci in range(1, len(cols)):
        vals = []
        for r in rows:
            try:
                vals.append(float(str(r[ci]).replace(",", "").split()[0]))
            except (ValueError, IndexError):
                vals = None
                break
        if vals is not None:
            return {"kind": "bar", "title": cols[ci], "labels": [str(r[0]) for r in rows], "values": vals, "unit": ""}
    return None


def choose(user_text: str, result: dict) -> dict:
    """Returns {kind, spec, note, available}. `note` explains when the request could not be honoured."""
    visuals = dict(result.get("visuals") or {})
    natural = result.get("natural") or (next(iter(visuals)) if visuals else "table")
    wanted = requested_visual(user_text)
    note = None
    if wanted == "chart":
        wanted = natural if natural in ("line", "bar", "heatmap") else "bar"
    if wanted and wanted not in visuals:
        derived = None
        if wanted == "bar" and "table" in visuals:
            derived = _bar_from_table(visuals["table"])
        if derived:
            visuals["bar"] = derived
        elif wanted == "map" and visuals.get("map", {}).get("points"):
            pass
        else:
            note = f"This answer cannot be shown as a {LABELS.get(wanted, wanted).lower()}; showing a {LABELS.get(natural, natural).lower()} instead."
            wanted = None
    if wanted == "map" and not visuals.get("map", {}).get("points"):
        note = "No locations are available for this answer; showing a table instead."
        wanted = None
        natural = "table" if "table" in visuals else natural
    kind = wanted or natural
    if kind not in visuals:
        kind = next(iter(visuals), None)
    available = [k for k in LABELS if k in visuals and (k != "map" or visuals["map"].get("points"))]
    return {"kind": kind, "spec": visuals.get(kind), "note": note, "available": available, "specs": {k: visuals[k] for k in available}}
