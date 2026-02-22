"""Jinja2 LaTeX renderer for resume generation.

Provides render_resume_tex() which converts a structured JSON payload
into a valid, compilable .tex file using a Jinja2 template with custom
delimiters and atomic file writes.
"""
import os
import re
import tempfile
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined


# ---------------------------------------------------------------------------
# LaTeX special character escaping
# ---------------------------------------------------------------------------

# Ordered mapping: backslash MUST be first so its replacement is not
# re-processed by subsequent substitutions.  We use a single regex pass
# to avoid that problem entirely.
_LATEX_ESCAPE_MAP = [
    ("\\", r"\textbackslash{}"),
    ("&",  r"\&"),
    ("%",  r"\%"),
    ("$",  r"\$"),
    ("#",  r"\#"),
    ("_",  r"\_"),
    ("{",  r"\{"),
    ("}",  r"\}"),
    ("~",  r"\textasciitilde{}"),
    ("^",  r"\textasciicircum{}"),
]

# Build a single regex that matches any of the special chars in one pass.
# Single-pass replacement prevents replacement strings from being re-escaped.
_LATEX_ESCAPE_RE = re.compile(
    r"(" + "|".join(re.escape(ch) for ch, _ in _LATEX_ESCAPE_MAP) + r")"
)
_LATEX_ESCAPE_DICT = dict(_LATEX_ESCAPE_MAP)


def latex_escape(value: str) -> str:
    """Escape LaTeX special characters in a user-supplied string.

    Uses a single-pass regex substitution so that replacement strings
    (e.g., ``\\textbackslash{}``) are never themselves re-escaped.
    Applied as a Jinja2 filter inside ``resume_template.tex.j2``.

    Args:
        value: Raw user-supplied string (name, bullet text, company, etc.)

    Returns:
        String safe for inclusion in a LaTeX document body.
    """
    return _LATEX_ESCAPE_RE.sub(
        lambda m: _LATEX_ESCAPE_DICT[m.group(0)], str(value)
    )


# ---------------------------------------------------------------------------
# Module-level cached Jinja2 environment
# ---------------------------------------------------------------------------

_LATEX_ENV: Optional[Environment] = None

# Templates directory is three levels up from src/latex/:
# src/latex/renderer.py -> src/latex/ -> src/ -> project_root/
_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


def _get_latex_env() -> Environment:
    """Return (and lazily create) the module-level cached Jinja2 environment.

    The environment uses custom delimiters to avoid clashing with LaTeX
    syntax:
      - Variables:  ((* ... *))
      - Blocks:     ((% ... %))
      - Comments:   ((# ... #))

    A module-level cache means the environment is built once per process.
    A process restart is required to pick up template file edits.
    """
    global _LATEX_ENV
    if _LATEX_ENV is None:
        env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            undefined=StrictUndefined,
            variable_start_string="((*",
            variable_end_string="*))",
            block_start_string="((%",
            block_end_string="%))",
            comment_start_string="((#",
            comment_end_string="#))",
            trim_blocks=True,
            lstrip_blocks=True,
        )
        # Register the latex_escape filter
        env.filters["latex_escape"] = latex_escape
        _LATEX_ENV = env
    return _LATEX_ENV


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_resume_tex(payload: dict, output_path: Path) -> Path:
    """Render resume JSON payload through resume_template.tex.j2 and save atomically.

    Converts a structured resume dict (matching resume_json_template.json
    schema) to a compilable .tex file.  The write is atomic: content is
    written to a temporary file in the same directory, then moved into place
    via os.replace() so the target is never left in a partially-written state.

    Args:
        payload: Structured resume dict matching resume_json_template.json
                 schema.  Top-level keys: meta, style, header, sections.
        output_path: Full absolute path for the output .tex file
                     (e.g., Path("data/acme/resume_iter_0.tex")).
                     Parent directory must already exist.

    Returns:
        output_path (the path of the written .tex file).

    Raises:
        jinja2.UndefinedError: If template references a variable not present
                               in payload (StrictUndefined mode).
        OSError: If parent directory does not exist or the write fails.
    """
    env = _get_latex_env()
    template = env.get_template("resume_template.tex.j2")

    # Render: unpack payload so each top-level key is a template variable
    tex_content = template.render(**payload)

    # Atomic write: tempfile in same directory -> os.replace
    output_path = Path(output_path)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=output_path.parent, suffix=".tex")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(tex_content)
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        os.unlink(tmp_path)
        raise
    os.replace(tmp_path, output_path)
    return output_path
