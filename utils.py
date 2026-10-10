"""Helpers for turning a model response into validated JSON and for error text.

Task-agnostic: the expected structure is passed in as a schema (see task.py).
"""

import json
import re

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


def _is_number(value) -> bool:
    # bool is a subclass of int; never accept it as a number.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_value(value, template, path: str) -> None:
    """Check `value` against the type that `template` stands for (see task.OUTPUT_SCHEMA)."""
    if template is None:  # any value
        return
    if isinstance(template, bool):
        ok = isinstance(value, bool)
    elif isinstance(template, (int, float)):
        ok = _is_number(value)
    elif isinstance(template, str):
        ok = isinstance(value, str)
    elif isinstance(template, list):
        ok = isinstance(value, list)
    elif isinstance(template, dict):
        ok = isinstance(value, dict)
    else:
        raise ValueError(f"Output schema has an unsupported value at '{path}'.")
    if not ok:
        raise ValueError(f"Field '{path}' has the wrong type ({type(value).__name__}).")

    if isinstance(template, list) and template:  # first item is the sample for all items
        for i, item in enumerate(value):
            _check_value(item, template[0], f"{path}[{i}]")
    elif isinstance(template, dict):
        _check_fields(value, template, path)


def _check_fields(data: dict, schema: dict, prefix: str = "") -> None:
    def name(key):
        return f"{prefix}.{key}" if prefix else key

    missing = [name(key) for key in schema if key not in data]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}.")
    for key, template in schema.items():
        _check_value(data[key], template, name(key))
        if key == "confidence" and _is_number(data[key]) and not 0.0 <= data[key] <= 1.0:
            raise ValueError(f"Field '{name(key)}' must be between 0.0 and 1.0.")


def validate(data, schema: dict | None = None) -> dict:
    """Check `data` is a JSON object matching `schema`. Returns it or raises ValueError.

    With no schema, only checks that `data` is an object.
    """
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object, got {type(data).__name__}.")
    if schema:
        _check_fields(data, schema)
    return data


def parse_model_json(text: str, schema: dict | None = None) -> dict:
    """Extract, parse, and validate JSON from a model response.

    Raises ValueError with a clear message if the response is unusable.
    """
    try:
        data = json.loads(extract_json_text(text))
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Model response is not valid JSON ({e.msg} at line {e.lineno}, column {e.colno})."
        ) from e
    return validate(data, schema)


def format_error(error: Exception) -> str:
    """One-line message suitable for showing in the UI."""
    return f"{type(error).__name__}: {error}"
