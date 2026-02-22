"""LLM utility functions: JSON extraction from LLM output."""
import json
import re
from typing import Any

from json_repair import repair_json


def extract_json(text: str) -> Any:
    """Extract and parse JSON from LLM output, handling all markdown code fence variants.

    Handles:
    - Triple-backtick fences: ```json { ... } ``` or ``` { ... } ```
    - Any language tag after opening fence (json, python, etc.)
    - No fence (direct JSON)
    - Malformed/incomplete JSON (repaired via json_repair.repair_json)

    Args:
        text: Raw text from LLM response.

    Returns:
        Parsed Python object (usually dict).

    Raises:
        ValueError: If no valid JSON can be extracted after repair attempts.
                    Error message includes first 300 chars of input for debugging.
    """
    cleaned = _strip_code_fences(text)

    # Fast path: valid JSON
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Repair path: try json_repair
    try:
        repaired = repair_json(cleaned)
        if not repaired or repaired.strip() in ("", '""', "null"):
            raise ValueError(
                f"Could not extract valid JSON from LLM output.\n"
                f"Input (first 300 chars): {text[:300]!r}\n"
                f"Cleaned: {cleaned[:300]!r}\n"
                f"Error: repair_json returned empty or null result"
            )
        return json.loads(repaired)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            f"Could not extract valid JSON from LLM output.\n"
            f"Input (first 300 chars): {text[:300]!r}\n"
            f"Cleaned: {cleaned[:300]!r}\n"
            f"Error: {exc}"
        ) from exc


def _strip_code_fences(text: str) -> str:
    """Strip triple-backtick code fences from text, returning the inner content.

    Handles:
    - ```json ... ``` (with language tag)
    - ``` ... ``` (bare fence)
    - No fence present (returns text.strip())
    """
    pattern = r"```(?:[a-zA-Z]*)?\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()
    return text.strip()
