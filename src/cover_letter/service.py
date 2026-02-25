"""CoverLetterService orchestrator — generates a 300-400 word cover letter.

Coordinates LLM generation with word-count retry loop, preamble strip,
em-dash cleanup, atomic file write, and PDF compilation via tectonic.
Follows the same stateless async orchestrator pattern as ResumeService.

Usage:
    service = CoverLetterService(config, llm_client)
    result = await service.generate(job_record, selected_resume_json, store)
"""
import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from src.config import AppConfig
from src.latex.renderer import latex_escape
from src.llm.client import LLMClient
from src.llm.errors import LLMError
from src.llm.utils import load_prompt
from src.models.job_record import JobRecord
from src.storage.job_store import JobStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORD_COUNT_MIN = 300
WORD_COUNT_MAX = 400
MAX_WORD_COUNT_RETRIES = 2


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class CoverLetterResult:
    """Structured result from CoverLetterService.generate().

    Attributes:
        success:    True when cover letter was generated and saved to disk.
        txt_path:   Path to the saved cover_letter.txt (set on success).
        pdf_path:   Path to the compiled cover_letter.pdf (set on success, or None if compilation failed).
        word_count: Final word count of the generated cover letter.
        error:      Error description on hard failure.
    """

    success: bool
    txt_path: Optional[Path] = None
    pdf_path: Optional[Path] = None
    word_count: Optional[int] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Module-level helper functions (pure — deterministic, no I/O or LLM calls)
# ---------------------------------------------------------------------------


def _resolve_graduation_date(employment_type: Optional[str]) -> tuple[str, str]:
    """Return (graduation_date, application_type) based on employment_type.

    Internship detection uses substring match on 'intern' (case-insensitive)
    to handle both "internship" and "Software Intern" variants.

    Args:
        employment_type: Employment type string from JD parse, or None.

    Returns:
        Tuple of (graduation_date, application_type):
        - internship: ("Dec 2026", "internship")
        - full-time / unknown / None: ("May 2026", "full-time")
    """
    if employment_type and "intern" in employment_type.lower():
        return "Dec 2026", "internship"
    return "May 2026", "full-time"


def _clean_cover_letter_output(text: str) -> str:
    """Strip LLM preamble, fix em-dashes, and remove [Job Source] placeholder.

    Processing order:
      1. Strip everything before 'Dear' — handles "Here is the cover letter: Dear..."
      2. Replace U+2014 em-dash with comma (COV-05)
      3. Replace double-hyphen (--) with comma (COV-05)
      4. Replace '[Job Source]' placeholder with 'your website'

    Args:
        text: Raw LLM cover letter output.

    Returns:
        Cleaned cover letter text starting from 'Dear'.
    """
    # Strip everything before "Dear" — handles "Here is the cover letter: Dear..."
    text = re.sub(r'^.*?(?=Dear\b)', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Em-dash safety net (COV-05): U+2014 and double-hyphen
    text = text.replace('\u2014', ',')
    text = re.sub(r'\s*--\s*', ', ', text)
    # [Job Source] placeholder fallback (per CONTEXT.md Specifics)
    text = text.replace('[Job Source]', 'your website')
    return text.strip()


def _save_cover_letter_txt(text: str, job_dir: Path) -> Path:
    """Write cover_letter.txt atomically using tempfile + os.replace pattern.

    This is the same atomic write pattern used by JobStore.write() to prevent
    partial-write corruption. The file is never left in a partially-written state.

    Args:
        text: Cleaned cover letter content to write.
        job_dir: Directory where cover_letter.txt will be created.

    Returns:
        Path to the written cover_letter.txt.

    Raises:
        OSError: If the write or atomic replace fails.
    """
    txt_path = job_dir / "cover_letter.txt"
    encoded = text.encode("utf-8")
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=job_dir, delete=False, suffix=".tmp"
    ) as tmp:
        tmp.write(encoded)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    try:
        tmp_path.replace(txt_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    return txt_path


# ---------------------------------------------------------------------------
# PDF generation helpers
# ---------------------------------------------------------------------------

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
_COVER_LETTER_AUTHOR = "Tanmay Bhuskute"


def _render_cover_letter_tex(text: str, output_path: Path) -> Path:
    """Render cover letter plain text to a compilable .tex file atomically.

    Splits the text on blank lines to produce paragraphs, then renders
    via cover_letter_template.tex.j2. The write is atomic (tempfile + replace).

    Args:
        text:        Cleaned cover letter text (plain text, newline-delimited).
        output_path: Full path for the output .tex file. Parent must exist.

    Returns:
        output_path (the path of the written .tex file).
    """
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
    env.filters["latex_escape"] = latex_escape

    template = env.get_template("cover_letter_template.tex.j2")
    paragraphs = [p.strip() for p in re.split(r'\n{2,}', text)]
    tex_content = template.render(name=_COVER_LETTER_AUTHOR, paragraphs=paragraphs)

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


def _compile_cover_letter_pdf(tex_path: Path, job_dir: Path) -> Optional[Path]:
    """Compile a cover letter .tex file to PDF via tectonic.

    Args:
        tex_path: Path to the .tex file to compile.
        job_dir:  Output directory for the compiled PDF.

    Returns:
        Path to the PDF on success, None on any failure.
    """
    try:
        result = subprocess.run(
            ["tectonic", "--outdir", str(job_dir), str(tex_path)],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        pdf_path = job_dir / (tex_path.stem + ".pdf")
        if pdf_path.exists():
            return pdf_path
        logger.warning("tectonic succeeded but PDF not found at %s", pdf_path)
        return None
    except subprocess.CalledProcessError as exc:
        logger.warning("Cover letter PDF compilation failed: %s", exc.stderr[:300] if exc.stderr else "no output")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("Cover letter PDF compilation timed out")
        return None
    except FileNotFoundError:
        logger.warning("tectonic not found in PATH — skipping PDF compilation")
        return None


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class CoverLetterService:
    """Stateless orchestrator for cover letter generation.

    Generates a 300-400 word cover letter from JD context and selected resume
    content. Follows the same stateless async pattern as ResumeService —
    config + llm_client at construction, all call-specific state passed per call.

    Usage:
        service = CoverLetterService(config, llm_client)
        result = await service.generate(job_record, selected_resume_json, store)
    """

    def __init__(self, config: AppConfig, llm_client: LLMClient) -> None:
        self.config = config
        self.llm = llm_client

    async def generate(
        self,
        job_record: JobRecord,
        selected_resume_json: str,
        store: JobStore,
    ) -> CoverLetterResult:
        """Generate cover letter, validate word count, save .txt, update job_record.

        Orchestrates the full cover letter pipeline:
          1. Resolve graduation date and application type from employment_type
          2. Generate cover letter with word-count retry loop (up to 2 retries)
          3. Post-process: strip preamble, em-dashes, [Job Source] placeholder
          4. Write cover_letter.txt atomically to job_dir
          5. Update job_record.cover_letter_path and re-persist via store.write()

        Args:
            job_record: Must have job_dir (absolute), jd_text, and optionally
                        employment_type. cover_letter_path will be set on success.
            selected_resume_json: Full resume content as JSON string — passed to
                                  LLM prompt.
            store: JobStore for re-persisting updated job_record after
                   cover_letter_path is set.

        Returns:
            CoverLetterResult — never raises on word count failure (returns result
            with word_count set to actual count even if outside [300, 400]).
        """
        job_dir = Path(job_record.job_dir)

        # Step 1: Resolve graduation date and application type from employment_type field
        employment_type = getattr(job_record, 'employment_type', None)
        graduation_date, application_type = _resolve_graduation_date(employment_type)
        logger.info(
            "Cover letter: graduation_date=%s, application_type=%s",
            graduation_date, application_type,
        )

        # Step 2: Generate with word count retry loop
        try:
            text = await self._generate_with_word_count_check(
                jd_text=job_record.jd_text or "",
                selected_resume_json=selected_resume_json,
                graduation_date=graduation_date,
                application_type=application_type,
            )
        except LLMError as exc:
            return CoverLetterResult(success=False, error=f"LLM error: {exc}")
        except Exception as exc:
            return CoverLetterResult(success=False, error=f"Cover letter generation failed: {exc}")

        # Step 3: Post-process (preamble strip, em-dash, [Job Source])
        text = _clean_cover_letter_output(text)
        final_word_count = len(text.split())
        logger.info("Cover letter final word count: %d", final_word_count)

        # Step 4: Write cover_letter.txt atomically
        try:
            txt_path = _save_cover_letter_txt(text, job_dir)
        except Exception as exc:
            return CoverLetterResult(success=False, error=f"File write failed: {exc}")

        # Step 5: Compile cover_letter.pdf via tectonic
        pdf_path: Optional[Path] = None
        try:
            tex_path = job_dir / "cover_letter.tex"
            _render_cover_letter_tex(text, tex_path)
            pdf_path = _compile_cover_letter_pdf(tex_path, job_dir)
            if pdf_path:
                logger.info("Cover letter PDF: %s", pdf_path)
            else:
                logger.warning("Cover letter PDF compilation produced no output")
        except Exception as exc:
            logger.warning("Cover letter PDF step failed (non-fatal): %s", exc)

        # Step 6: Update JobRecord with cover_letter_path and re-persist
        # Write file first, then update record (never update record before file exists)
        job_record.cover_letter_path = str(txt_path)
        try:
            store.write(job_record)
        except Exception as exc:
            logger.warning("Failed to update job_record.cover_letter_path: %s", exc)
            # Not fatal — file was written successfully

        return CoverLetterResult(
            success=True,
            txt_path=txt_path,
            pdf_path=pdf_path,
            word_count=final_word_count,
        )

    async def _generate_with_word_count_check(
        self,
        jd_text: str,
        selected_resume_json: str,
        graduation_date: str,
        application_type: str,
    ) -> str:
        """Call LLM, check word count, retry up to MAX_WORD_COUNT_RETRIES times.

        On each attempt, checks whether the output is within [WORD_COUNT_MIN,
        WORD_COUNT_MAX]. If outside the range and retries remain, prepends a
        correction message to the prompt and retries. After all retries, accepts
        the last result with a warning log.

        Args:
            jd_text: Raw job description text.
            selected_resume_json: Selected resume content as JSON string.
            graduation_date: Resolved graduation date string.
            application_type: Resolved application type string.

        Returns:
            Cover letter text (raw, before post-processing).

        Raises:
            LLMError: If the LLM call fails after retries.
        """
        # Variables per generate_cover_letter.md:
        # job_description, selected_resume_json, graduation_date, application_type
        prompt = load_prompt(
            "generate_cover_letter",
            job_description=jd_text,
            selected_resume_json=selected_resume_json,
            graduation_date=graduation_date,
            application_type=application_type,
        )

        for attempt in range(MAX_WORD_COUNT_RETRIES + 1):
            raw = await self.llm.call(prompt)
            text = raw.strip()
            word_count = len(text.split())

            if WORD_COUNT_MIN <= word_count <= WORD_COUNT_MAX:
                logger.info(
                    "Cover letter word count %d in range [%d, %d] on attempt %d",
                    word_count, WORD_COUNT_MIN, WORD_COUNT_MAX, attempt + 1,
                )
                return text

            if attempt < MAX_WORD_COUNT_RETRIES:
                direction = "shorten" if word_count > WORD_COUNT_MAX else "expand"
                correction = (
                    f"Previous version was {word_count} words. Please {direction} it "
                    f"to be between {WORD_COUNT_MIN} and {WORD_COUNT_MAX} words.\n\n"
                    + prompt
                )
                prompt = correction
                logger.warning(
                    "Cover letter word count %d out of range [%d, %d]; retrying (%d/%d)",
                    word_count, WORD_COUNT_MIN, WORD_COUNT_MAX,
                    attempt + 1, MAX_WORD_COUNT_RETRIES,
                )

        # After MAX retries, accept the last result with a warning (do not fail)
        logger.warning(
            "Cover letter word count %d still outside [%d, %d] after %d retries; accepting",
            word_count, WORD_COUNT_MIN, WORD_COUNT_MAX, MAX_WORD_COUNT_RETRIES,
        )
        return text
