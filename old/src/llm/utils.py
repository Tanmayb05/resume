"""LLM utility functions: JSON extraction from LLM output."""
import json
import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound
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


# Module-level cache — Jinja2 Environment with compiled templates.
# Process restart required to pick up prompt file edits (documented behavior).
_JINJA_ENV: Environment | None = None


def _get_jinja_env() -> Environment:
    """Return (or lazily create) the shared Jinja2 environment for llm/prompts/."""
    global _JINJA_ENV
    if _JINJA_ENV is None:
        prompts_dir = Path(__file__).parent / "prompts"
        _JINJA_ENV = Environment(
            loader=FileSystemLoader(str(prompts_dir)),
            undefined=StrictUndefined,   # Raise on undefined variables — fail fast
            trim_blocks=True,            # Remove newline after block tags
            lstrip_blocks=True,          # Strip leading whitespace from block tags
            keep_trailing_newline=True,
        )
    return _JINJA_ENV


def load_prompt(name: str, **variables: Any) -> str:
    """Load and render a Jinja2 prompt template from llm/prompts/{name}.md.

    Templates use {{ variable }} syntax for substitution. All referenced
    variables must be supplied as keyword arguments — StrictUndefined raises
    jinja2.UndefinedError if any are missing.

    The Jinja2 environment (and compiled templates) is cached in memory after
    first call. Restart the process to pick up edits to .md files.

    Args:
        name: Prompt name without extension, e.g. 'select_resume'
              maps to llm/prompts/select_resume.md.
        **variables: Jinja2 template variables to substitute.

    Returns:
        Fully rendered prompt string ready to pass to LLMClient.call().

    Raises:
        FileNotFoundError: If prompts/{name}.md does not exist.
                           Message lists available prompt names.
        jinja2.UndefinedError: If template references a variable not supplied.

    Example:
        prompt = load_prompt(
            'select_resume',
            job_description='Senior Python engineer...',
            master_resume_json='[{"id": 1, ...}]',
        )
    """
    env = _get_jinja_env()
    template_name = f"{name}.md"

    try:
        template = env.get_template(template_name)
    except TemplateNotFound:
        prompts_dir = Path(__file__).parent / "prompts"
        available = sorted(p.stem for p in prompts_dir.glob("*.md"))
        raise FileNotFoundError(
            f"Prompt '{name}' not found in llm/prompts/. "
            f"Available: {', '.join(available) if available else '(none)'}"
        )

    return template.render(**variables)


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
