"""
JSON utilities: strip markdown fences and safely parse AI responses.
"""
import json
import re
from typing import Any


def strip_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ``` or ``` ... ```) from text."""
    # Remove ```json ... ``` or ``` ... ``` blocks
    pattern = r"^```[a-zA-Z]*\n?([\s\S]*?)\n?```$"
    match = re.match(pattern, text.strip())
    if match:
        return match.group(1).strip()
    return text.strip()


def safe_json_parse(text: str) -> Any:
    """
    Strip markdown fences from text, then parse as JSON.

    Args:
        text: Raw text from an AI response, possibly wrapped in code fences.

    Returns:
        Parsed Python object.

    Raises:
        ValueError: If the text cannot be parsed as JSON after stripping fences.
    """
    cleaned = strip_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse JSON: {exc}\nText was: {cleaned[:200]}") from exc


def to_json_str(obj: Any, *, indent: int | None = None) -> str:
    """Serialize object to JSON string with consistent settings."""
    return json.dumps(obj, indent=indent, ensure_ascii=False, default=str)
