"""Pull one JSON object out of a model reply."""

import json
import re


def extract_json(text: str) -> dict | None:
    if not text:
        return None
    stripped = text.strip()
    obj = _loads_object(stripped)
    if obj is not None:
        return obj
    for match in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.S):
        obj = _loads_object(match.group(1))
        if obj is not None:
            return obj
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return _loads_object(stripped[start : end + 1])
    return None


def _loads_object(text: str) -> dict | None:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None
