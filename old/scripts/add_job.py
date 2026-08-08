#!/usr/bin/env python
"""Deterministic helpers for the /add-job skill.

Claude Code does the creative work — reading the JD, scoring the match, choosing
resume content, writing the cover letter. This script does only the mechanical
parts: slugging, directory creation, Jinja rendering, LaTeX compilation, DOCX
building, and spreadsheet writing.

Every subcommand prints exactly one JSON object to stdout and logs to stderr, so
each step is independently runnable and debuggable:

    .venv/bin/python scripts/add_job.py init --extraction input/last_extraction.json
    .venv/bin/python scripts/add_job.py build-resume --job-dir DIR --content DIR/resume_content.json --iter 1
    .venv/bin/python scripts/add_job.py build-cover-letter --job-dir DIR --text DIR/cover_letter.txt
    .venv/bin/python scripts/add_job.py track --job-dir DIR --extras DIR/tracker_extras.json

Exit code is 0 on success, 1 on failure with {"ok": false, "error": ..., "hint": ...}.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

# Allow running as `python scripts/add_job.py` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import AppConfig  # noqa: E402
from src.cover_letter.docx_writer import (  # noqa: E402
    split_paragraphs,
    write_cover_letter_docx,
)
from src.latex.compiler import check_ats_parsability, compile_tex  # noqa: E402
from src.latex.pdf_analyzer import analyze_pdf  # noqa: E402
from src.latex.renderer import render_resume_tex  # noqa: E402
from src.models.job_record import JobRecord, JobStatus  # noqa: E402
from src.resume.ir_builder import available_ids, build_resume_payload  # noqa: E402
from src.resume.validator import validate_content  # noqa: E402
from src.storage.job_store import JobStore  # noqa: E402
from src.storage.tracker_store import update_application_tracker  # noqa: E402

logger = logging.getLogger("add_job")

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"
MASTER_RESUME_PATH = TEMPLATES_DIR / "master_resume.json"
RESUME_SCHEMA_PATH = TEMPLATES_DIR / "resume_json_template.json"
COVER_LETTER_TEMPLATE = "cover_letter_template.tex.j2"

# Cover-letter checks, from templates/cover_letter_prompt.md.
WORD_COUNT_MIN = 220
WORD_COUNT_MAX = 320
REQUIRED_SALUTATION = "Dear Hiring Committee,"
PLACEHOLDER_TOKENS = ("[Job Source]", "[Job Title]", "[Organization]")
# master_resume.json says Dec 2026; the legacy service says May 2026 and is wrong.
WRONG_GRADUATION = "May 2026"

MAX_STDERR_CHARS = 500


class StepError(Exception):
    """A failure to report as JSON without a traceback."""

    def __init__(self, error: str, hint: str = "", **extra: Any) -> None:
        super().__init__(error)
        self.error = error
        self.hint = hint
        self.extra = extra


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


def cmd_init(args: argparse.Namespace, config: AppConfig) -> dict:
    """Create the job directory and job.json from Claude's extraction JSON."""
    extraction = _read_json(Path(args.extraction), "extraction")

    company = _require_text(extraction, "company")
    role = _require_text(extraction, "role")
    location = _require_text(extraction, "location")

    store = JobStore(config.data_dir)

    existing = _find_duplicate(store, company, role)
    if existing is not None and not args.allow_duplicate:
        return {
            "ok": True,
            "job_dir": existing.job_dir,
            "slug": Path(existing.job_dir).name,
            "created": False,
            "duplicate_of": existing.job_dir,
            "hint": (
                "A record for this company and role already exists. Re-run with "
                "--allow-duplicate to create a separate variant directory."
            ),
        }

    job_dir = store.new_job_dir(company, role)
    job_dir.mkdir(parents=True, exist_ok=True)

    record = JobRecord(
        company=company,
        role=role,
        location=location,
        job_dir=str(job_dir),
        status=JobStatus.DISCOVERED,
        jd_text=extraction.get("jd_text"),
        employment_type=extraction.get("employment_type"),
        department=extraction.get("department"),
        description=extraction.get("description"),
        responsibilities=extraction.get("responsibilities") or [],
        requirements=extraction.get("requirements") or [],
        qualifications=extraction.get("qualifications") or [],
        skills_technical=extraction.get("skills_technical") or [],
        skills_soft=extraction.get("skills_soft") or [],
        education=extraction.get("education") or [],
        experience_required=extraction.get("experience_required"),
        benefits=extraction.get("benefits") or [],
        salary_range=extraction.get("salary_range"),
        date_posted=extraction.get("date_posted"),
        application_deadline=extraction.get("application_deadline"),
        visa_keywords=extraction.get("visa_keywords") or [],
        f1_sponsorship_available=extraction.get("f1_sponsorship_available"),
    )
    store.write(record)

    if record.jd_text:
        (job_dir / "jd.txt").write_text(record.jd_text, encoding="utf-8")

    # Keep the raw extraction (scores, justifications) beside the artifacts.
    (job_dir / "extraction.json").write_text(
        json.dumps(extraction, indent=2), encoding="utf-8"
    )

    return {
        "ok": True,
        "job_dir": str(job_dir),
        "slug": job_dir.name,
        "created": True,
        "duplicate_of": None,
        "available_ids": available_ids(_load_master_resume()),
    }


def _find_duplicate(store: JobStore, company: str, role: str) -> JobRecord | None:
    """Return an existing record matching company+role, ignoring case/spacing."""
    target = (_normalize(company), _normalize(role))
    for record in store.list_all():
        if (_normalize(record.company), _normalize(record.role)) == target:
            return record
    return None


def _normalize(value: str) -> str:
    return " ".join(str(value).strip().lower().split())


# ---------------------------------------------------------------------------
# build-resume
# ---------------------------------------------------------------------------


def cmd_build_resume(args: argparse.Namespace, config: AppConfig) -> dict:
    """Assemble, render, compile, and measure one resume iteration."""
    job_dir = _require_dir(Path(args.job_dir))
    content = _read_json(Path(args.content), "resume content")
    master_resume = _load_master_resume()

    try:
        payload = build_resume_payload(master_resume, content)
    except ValueError as exc:
        raise StepError(
            str(exc),
            hint="Fix resume_content.json — see available_ids from the init step.",
        ) from exc

    _validate_against_schema(payload)

    validation = validate_content(payload, master_resume)

    iteration = args.iteration
    json_path = job_dir / f"resume_iter_{iteration}.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    tex_path = job_dir / f"resume_iter_{iteration}.tex"
    try:
        render_resume_tex(payload, tex_path)
    except Exception as exc:
        raise StepError(
            f"Jinja rendering failed: {exc}",
            hint="The payload is missing a key the template requires.",
            json=str(json_path),
        ) from exc

    result = compile_tex(tex_path, job_dir)
    if not result.get("success"):
        raise StepError(
            f"LaTeX compilation failed: {result.get('error_type')}",
            hint=(
                "Read the .tex around the reported line and fix the *content* in "
                "resume_content.json. Never hand-edit the .tex — it is regenerated."
                if result.get("error_type") == "compilation_failed"
                else "Install tectonic with `brew install tectonic`."
            ),
            error_type=result.get("error_type"),
            stderr=(result.get("stderr") or "")[:MAX_STDERR_CHARS],
            tex=str(tex_path),
            json=str(json_path),
        )

    pdf_path = Path(result["pdf_path"])
    analysis = analyze_pdf(pdf_path)
    verdict = _resume_verdict(analysis, config.whitespace_threshold)

    return {
        "ok": True,
        "iteration": iteration,
        "json": str(json_path),
        "tex": str(tex_path),
        "pdf": str(pdf_path),
        "page_count": analysis.get("page_count"),
        "whitespace_ratio": analysis.get("whitespace_ratio"),
        "whitespace_percent": _whitespace_percent(analysis),
        "whitespace_threshold": config.whitespace_threshold,
        "page_height_inches": analysis.get("page_height_inches"),
        "ats_parsable": check_ats_parsability(pdf_path),
        "verdict": verdict,
        "validation_warning": validation.validation_warning,
        "violations": validation.violations,
    }


def _resume_verdict(analysis: dict, whitespace_threshold: float) -> str:
    """Classify a rendered resume as accept / too_long / too_sparse / unknown.

    Pure threshold arithmetic — the judgment about *what to cut* stays with Claude.
    """
    if not analysis.get("success") or analysis.get("page_count", -1) < 0:
        return "unknown"
    if analysis["page_count"] > 1:
        return "too_long"
    percent = _whitespace_percent(analysis)
    if percent is not None and percent > whitespace_threshold:
        return "too_sparse"
    return "accept"


def _whitespace_percent(analysis: dict) -> float | None:
    """Convert analyze_pdf's 0-1 whitespace ratio to a percentage."""
    ratio = analysis.get("whitespace_ratio")
    if ratio is None or ratio < 0:
        return None
    return round(ratio * 100, 2)


def _validate_against_schema(payload: dict) -> None:
    """Check the payload against resume_json_template.json.

    Runs before Jinja so a shape problem surfaces as a readable JSON-Schema
    error rather than a StrictUndefined traceback.
    """
    try:
        import jsonschema
    except ImportError:
        logger.warning("jsonschema not installed — skipping schema validation")
        return

    schema = _read_json(RESUME_SCHEMA_PATH, "resume schema")
    try:
        jsonschema.validate(payload, schema)
    except jsonschema.ValidationError as exc:
        location = "/".join(str(part) for part in exc.absolute_path) or "(root)"
        raise StepError(
            f"Resume payload failed schema validation at {location}: {exc.message}",
            hint="Adjust resume_content.json so the assembled payload fits the schema.",
        ) from exc


# ---------------------------------------------------------------------------
# build-cover-letter
# ---------------------------------------------------------------------------


def cmd_build_cover_letter(args: argparse.Namespace, config: AppConfig) -> dict:
    """Check the cover-letter text, then render it to .docx and .pdf."""
    job_dir = _require_dir(Path(args.job_dir))
    text_path = Path(args.text)
    if not text_path.exists():
        raise StepError(f"Cover letter text not found: {text_path}")

    text = text_path.read_text(encoding="utf-8")
    word_count = len(text.split())

    _check_cover_letter_text(text, word_count)

    paragraphs = split_paragraphs(text)

    docx_path = write_cover_letter_docx(text, job_dir / "cover_letter.docx")

    tex_path = _render_cover_letter_tex(paragraphs, job_dir / "cover_letter.tex")
    result = compile_tex(tex_path, job_dir)
    if not result.get("success"):
        raise StepError(
            f"Cover letter PDF compilation failed: {result.get('error_type')}",
            hint="Check the .tex for unescaped characters.",
            error_type=result.get("error_type"),
            stderr=(result.get("stderr") or "")[:MAX_STDERR_CHARS],
            txt=str(text_path),
            docx=str(docx_path),
            tex=str(tex_path),
        )

    pdf_path = Path(result["pdf_path"])

    return {
        "ok": True,
        "txt": str(text_path),
        "docx": str(docx_path),
        "tex": str(tex_path),
        "pdf": str(pdf_path),
        "word_count": word_count,
        "paragraph_count": len(paragraphs),
        "pdf_word_count": _pdf_word_count(pdf_path),
    }


def _check_cover_letter_text(text: str, word_count: int) -> None:
    """Enforce the mechanical rules from templates/cover_letter_prompt.md."""
    if not text.strip():
        raise StepError("Cover letter text is empty")

    if REQUIRED_SALUTATION not in text:
        raise StepError(
            f"Missing required salutation {REQUIRED_SALUTATION!r}",
            hint="templates/cover_letter_prompt.md mandates this exact line.",
        )

    if not WORD_COUNT_MIN <= word_count <= WORD_COUNT_MAX:
        raise StepError(
            f"Word count {word_count} is outside {WORD_COUNT_MIN}-{WORD_COUNT_MAX}",
            hint=(
                "Trim a reason or shorten sentences."
                if word_count > WORD_COUNT_MAX
                else "Add specifics to an existing reason."
            ),
            word_count=word_count,
        )

    if "—" in text or "–" in text:
        raise StepError(
            "Cover letter contains an em dash or en dash",
            hint="templates/cover_letter_prompt.md rule 3 bans them. Use commas or periods.",
        )

    found = [token for token in PLACEHOLDER_TOKENS if token in text]
    if found:
        raise StepError(
            f"Unreplaced placeholder(s): {', '.join(found)}",
            hint="Substitute the real job source, title, and organization.",
        )

    if WRONG_GRADUATION in text:
        raise StepError(
            f"Cover letter says {WRONG_GRADUATION!r}, which is wrong",
            hint=(
                "master_resume.json and cover_letter_prompt.md both say December 2026. "
                "src/cover_letter/service.py::_resolve_graduation_date is the stale source."
            ),
        )


def _render_cover_letter_tex(paragraphs: list[str], output_path: Path) -> Path:
    """Render paragraphs through templates/cover_letter_template.tex.j2."""
    from src.latex.renderer import _get_latex_env  # reuses the escape filters

    master_resume = _load_master_resume()
    try:
        template = _get_latex_env().get_template(COVER_LETTER_TEMPLATE)
    except Exception as exc:
        raise StepError(
            f"Cover letter template unavailable: {exc}",
            hint=f"Restore it with `git checkout -- templates/{COVER_LETTER_TEMPLATE}`.",
        ) from exc

    rendered = template.render(
        name=master_resume.get("name", ""),
        paragraphs=paragraphs,
    )
    output_path.write_text(rendered, encoding="utf-8")
    return output_path


def _pdf_word_count(pdf_path: Path) -> int | None:
    """Word count of the compiled PDF via pdftotext, or None if unavailable.

    A cross-check that the PDF really contains the letter, not a blank page.
    """
    import shutil
    import subprocess

    if shutil.which("pdftotext") is None:
        return None
    try:
        result = subprocess.run(
            ["pdftotext", str(pdf_path), "-"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        logger.warning("pdftotext failed: %s", exc)
        return None
    return len(result.stdout.split())


# ---------------------------------------------------------------------------
# track
# ---------------------------------------------------------------------------


def cmd_track(args: argparse.Namespace, config: AppConfig) -> dict:
    """Refresh job.json from artifacts on disk, then write the tracker row."""
    job_dir = _require_dir(Path(args.job_dir))
    store = JobStore(config.data_dir)

    try:
        record = store.read(job_dir)
    except (FileNotFoundError, ValueError) as exc:
        raise StepError(
            str(exc), hint="Run the init step first to create job.json."
        ) from exc

    extras = {}
    if args.extras:
        extras = _read_json(Path(args.extras), "tracker extras")

    resume_pdf = _latest_resume_pdf(job_dir)
    if resume_pdf is not None:
        record.resume_pdf_path = str(resume_pdf)

    cover_letter_txt = job_dir / "cover_letter.txt"
    if cover_letter_txt.exists():
        record.cover_letter_path = str(cover_letter_txt)

    if record.resume_pdf_path and record.cover_letter_path:
        record.status = JobStatus.READY
    record.mark_updated()
    store.write(record)

    try:
        result = update_application_tracker(record, config.tracker_path, extras=extras)
    except (ValueError, TypeError) as exc:
        raise StepError(
            str(exc), hint="Fix tracker_extras.json to satisfy the column rules."
        ) from exc
    except FileNotFoundError as exc:
        raise StepError(
            str(exc), hint=f"Expected the workbook at {config.tracker_path}."
        ) from exc
    except PermissionError as exc:
        raise StepError(
            "tracker_locked",
            hint=(
                "The workbook is open in Excel. Close it and re-run only this step; "
                "all other artifacts are already on disk."
            ),
            detail=str(exc),
        ) from exc

    return {
        "ok": True,
        "workbook": str(result.workbook_path),
        "row_number": result.row_number,
        "created": result.created,
        "status": record.status,
        "resume_pdf_path": record.resume_pdf_path,
        "cover_letter_path": record.cover_letter_path,
    }


def _latest_resume_pdf(job_dir: Path) -> Path | None:
    """Highest-numbered resume_iter_N.pdf, which is the accepted iteration."""
    candidates = sorted(
        job_dir.glob("resume_iter_*.pdf"),
        key=lambda p: _iteration_number(p.stem),
    )
    return candidates[-1] if candidates else None


def _iteration_number(stem: str) -> int:
    try:
        return int(stem.rsplit("_", 1)[-1])
    except ValueError:
        return -1


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _load_master_resume() -> dict:
    return _read_json(MASTER_RESUME_PATH, "master resume")


def _read_json(path: Path, label: str) -> dict:
    if not path.exists():
        raise StepError(f"{label.capitalize()} file not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StepError(
            f"{label.capitalize()} file is not valid JSON: {exc}",
            hint=f"Fix the syntax in {path}.",
        ) from exc


def _require_dir(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_dir():
        raise StepError(f"Job directory not found: {resolved}")
    return resolved


def _require_text(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise StepError(
            f"Extraction is missing required field {key!r}",
            hint=(
                "company, role, and location determine the folder slug and the "
                "tracker dedup key. Ask the user rather than guessing."
            ),
        )
    return value.strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verbose", action="store_true", help="Log debug detail to stderr"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Create the job directory and job.json")
    p_init.add_argument("--extraction", required=True, help="Path to extraction JSON")
    p_init.add_argument(
        "--allow-duplicate",
        action="store_true",
        help="Create a variant directory even if this company+role already exists",
    )
    p_init.set_defaults(func=cmd_init)

    p_resume = sub.add_parser("build-resume", help="Render and compile one iteration")
    p_resume.add_argument("--job-dir", required=True)
    p_resume.add_argument("--content", required=True, help="Path to resume_content.json")
    p_resume.add_argument(
        "--iter", dest="iteration", type=int, default=1, help="Iteration number"
    )
    p_resume.set_defaults(func=cmd_build_resume)

    p_cover = sub.add_parser("build-cover-letter", help="Build the .docx and .pdf")
    p_cover.add_argument("--job-dir", required=True)
    p_cover.add_argument("--text", required=True, help="Path to cover_letter.txt")
    p_cover.set_defaults(func=cmd_build_cover_letter)

    p_track = sub.add_parser("track", help="Write the tracker row")
    p_track.add_argument("--job-dir", required=True)
    p_track.add_argument("--extras", help="Path to tracker_extras.json")
    p_track.set_defaults(func=cmd_track)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        stream=sys.stderr,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        payload = args.func(args, AppConfig())
    except StepError as exc:
        error = {"ok": False, "error": exc.error}
        if exc.hint:
            error["hint"] = exc.hint
        error.update(exc.extra)
        print(json.dumps(error, indent=2))
        return 1
    except Exception as exc:  # unexpected — still emit parseable JSON
        logger.exception("Unhandled error in %s", args.command)
        print(json.dumps({
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "hint": "Re-run with --verbose for a traceback on stderr.",
        }, indent=2))
        return 1

    print(json.dumps(payload, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
