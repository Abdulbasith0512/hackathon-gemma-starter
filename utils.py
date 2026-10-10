"""Helpers for turning a model response into validated JSON and for error text."""

import json
import re

# Expected top-level fields and their types. Keep in sync with SYSTEM_PROMPT.
REQUIRED_FIELDS = {
    "summary": str,
    "steps": list,
    "confidence": (int, float),
}

_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def extract_json_text(text: str) -> str:
    """Return the JSON portion of a model response.

    Handles bare JSON, JSON inside a ```json fenced block, and JSON surrounded
    by stray prose (takes the span from the first '{' to the last '}').
    """
    text = (text or "").strip()
    fenced = _FENCE.search(text)
    if fenced:
        return fenced.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text


def validate(data) -> dict:
    """Check `data` against REQUIRED_FIELDS. Returns it unchanged or raises ValueError."""
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object, got {type(data).__name__}.")
    missing = [key for key in REQUIRED_FIELDS if key not in data]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}.")
    for key, expected in REQUIRED_FIELDS.items():
        value = data[key]
        # bool is a subclass of int; never accept it as a number.
        if not isinstance(value, expected) or isinstance(value, bool):
            raise ValueError(f"Field '{key}' has the wrong type ({type(value).__name__}).")
    if not 0.0 <= data["confidence"] <= 1.0:
        raise ValueError("Field 'confidence' must be between 0.0 and 1.0.")
    return data


def parse_model_json(text: str) -> dict:
    """Extract, parse, and validate JSON from a model response.

    Raises ValueError with a clear message if the response is unusable.
    """
    try:
        data = json.loads(extract_json_text(text))
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Model response is not valid JSON ({e.msg} at line {e.lineno}, column {e.colno})."
        ) from e
    return validate(data)


def format_error(error: Exception) -> str:
    """One-line message suitable for showing in the UI."""
    return f"{type(error).__name__}: {error}"
