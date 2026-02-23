"""TRIM loop module — compile-measure-trim-repeat cycle for one-page enforcement.

trim_loop() implements the RES-04 TRIM loop with three explicit termination
conditions:
  1. Success: page_count == 1 AND page_height_inches <= 11.5
  2. Max iterations reached (page_fit_warning=True) — partial success
  3. Two consecutive compilation failures (hard stop — error returned)

Intermediate iteration files are cleaned up; only the final success iteration
and the last failed iteration are kept.
"""

import asyncio  # noqa: F401 — imported for type context in async functions
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.config import AppConfig
from src.llm.utils import extract_json, load_prompt

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class LoopResult:
    """Result returned by trim_loop().

    Attributes:
        success:          True when resume fits on one page (page_count==1, height<=11.5in).
        iteration_count:  Number of iterations that ran (including the final one).
        pdf_path:         Path to the final PDF (success or last iteration).
        tex_path:         Path to the final .tex source.
        page_fit_warning: True when max_iterations reached without fitting to one page.
        whitespace_warning: True when success but whitespace_ratio > 0.40 (over-trimmed).
        error:            Error message string when success=False and not page_fit_warning.
    """

    success: bool
    iteration_count: int
    pdf_path: Optional[Path] = None
    tex_path: Optional[Path] = None
    page_fit_warning: bool = False
    whitespace_warning: bool = False
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _cleanup_iterations(
    all_iteration_paths: List[Tuple[Path, Path]],
    keep_tex: Path,
    keep_pdf: Path,
) -> None:
    """Delete intermediate iteration files, keeping only the specified tex/pdf pair.

    Args:
        all_iteration_paths: List of (tex_path, pdf_path) tuples for all iterations.
        keep_tex: The .tex file to preserve (final iteration).
        keep_pdf: The .pdf file to preserve (final iteration).
    """
    for tex, pdf in all_iteration_paths:
        if tex != keep_tex and tex.exists():
            try:
                tex.unlink()
            except OSError as exc:
                logger.debug("Could not delete intermediate tex %s: %s", tex, exc)
        if pdf != keep_pdf and pdf.exists():
            try:
                pdf.unlink()
            except OSError as exc:
                logger.debug("Could not delete intermediate pdf %s: %s", pdf, exc)


async def _trim_longest_bullets(
    selected_content: dict,
    pct: float,
    llm_client: Any,
    config: Any,
    page_count: int = 0,
    page_height: float = 0.0,
) -> dict:
    """Trim the longest bullet points using the LLM.

    Collects all bullets from work_experience and projects_and_research sections,
    sorts by character count descending, takes the top 5 longest, and asks the
    LLM to shorten them.

    Args:
        selected_content: Current resume dict (resume_json_template.json compatible).
        pct:              Target reduction percentage (e.g. 0.15 for 15%). Not used
                          directly in the prompt — the LLM uses the 100-char threshold
                          heuristic instead. Kept for API symmetry.
        llm_client:       LLMClient instance.
        config:           AppConfig instance.
        page_count:       Current page count (context for prompt).
        page_height:      Current page height in inches (context for prompt).

    Returns:
        Updated resume dict with shortened bullet texts.
    """
    # Collect all bullets across relevant sections
    bullets: List[Tuple[str, int, int, str, int]] = []
    # tuple: (section_type, entry_idx, bullet_idx, bullet_text, char_count)

    sections = selected_content.get("sections", [])
    for section in sections:
        section_type = section.get("type", "")
        if section_type in ("work_experience", "projects_and_research"):
            entries = section.get("entries", [])
            for entry_idx, entry in enumerate(entries):
                for bullet_idx, bullet_text in enumerate(entry.get("bullets", [])):
                    bullets.append(
                        (section_type, entry_idx, bullet_idx, bullet_text, len(bullet_text))
                    )

    if not bullets:
        logger.warning("_trim_longest_bullets: no bullets found in selected_content")
        return selected_content

    # Sort by char count descending, take top 5
    bullets.sort(key=lambda b: b[4], reverse=True)
    top5 = bullets[:5]

    # Build sorted_bullets JSON array for the prompt
    sorted_bullets_payload = [
        {
            "section": section_type,
            "entry_idx": entry_idx,
            "bullet_idx": bullet_idx,
            "text": text,
            "char_count": char_count,
        }
        for section_type, entry_idx, bullet_idx, text, char_count in top5
    ]

    logger.debug(
        "_trim_longest_bullets: targeting %d bullets, longest=%d chars",
        len(top5),
        top5[0][4] if top5 else 0,
    )

    # Render and call the trim prompt
    prompt = load_prompt(
        "trim_resume",
        current_resume_json=json.dumps(selected_content, indent=2),
        sorted_bullets=json.dumps(sorted_bullets_payload, indent=2),
        page_count=page_count,
        page_height_inches=page_height,
    )

    raw = await llm_client.call(prompt)
    updated = extract_json(raw)
    return updated


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def trim_loop(
    selected_content: dict,
    job_dir: Path,
    llm_client: Any,
    config: Any,
    render_fn: Callable,
    compile_fn: Callable,
    analyze_fn: Callable,
) -> LoopResult:
    """Run the compile-measure-trim-repeat loop until resume fits on one page.

    Three termination conditions (in priority order):
      1. page_count == 1 AND page_height_inches <= 11.5 -> success (LoopResult.success=True)
      2. Two consecutive compile failures -> hard stop (LoopResult.error set)
      3. max_iterations reached -> page_fit_warning (LoopResult.page_fit_warning=True)

    Args:
        selected_content: Resume dict (resume_json_template.json compatible).
        job_dir:          Job-specific directory where iter files are written.
        llm_client:       LLMClient instance for LLM trimming calls.
        config:           AppConfig instance (reads config.max_iterations, default 5).
        render_fn:        Callable(payload: dict, output_path: Path) -> Path
                          Maps to render_resume_tex from src.latex.renderer.
        compile_fn:       Callable(tex_path: Path, output_dir: Path) -> dict
                          Maps to compile_tex from src.latex.compiler.
        analyze_fn:       Callable(pdf_path: str) -> dict
                          Maps to analyze_pdf from src.latex.pdf_analyzer.

    Returns:
        LoopResult with outcome, paths, and warning flags.
    """
    max_iterations: int = getattr(config, "max_iterations", 5)
    iteration: int = 0
    consecutive_failures: int = 0
    all_iteration_paths: List[Tuple[Path, Path]] = []

    # Track last known PDF metrics for the trim helper
    last_page_count: int = 0
    last_page_height: float = 0.0

    while iteration < max_iterations:
        iteration += 1
        tex_path = job_dir / f"resume_iter_{iteration}.tex"
        pdf_path = job_dir / f"resume_iter_{iteration}.pdf"
        all_iteration_paths.append((tex_path, pdf_path))

        # Render .tex
        try:
            render_fn(selected_content, tex_path)
        except Exception as exc:
            logger.error("Render failed at iter %d: %s", iteration, exc)
            consecutive_failures += 1
            if consecutive_failures >= 2:
                logger.error("Two consecutive render/compile failures — stopping")
                return LoopResult(
                    success=False,
                    iteration_count=iteration,
                    error="Two consecutive compilation failures",
                )
            selected_content = await _trim_longest_bullets(
                selected_content,
                pct=0.15,
                llm_client=llm_client,
                config=config,
                page_count=last_page_count,
                page_height=last_page_height,
            )
            continue

        # Compile to PDF
        compile_result = compile_fn(tex_path, job_dir)
        if not compile_result.get("success", False):
            consecutive_failures += 1
            logger.warning(
                "Compile failed iter %d: %s",
                iteration,
                compile_result.get("error_type", "unknown"),
            )
            if consecutive_failures >= 2:
                logger.error("Two consecutive compile failures — stopping")
                return LoopResult(
                    success=False,
                    iteration_count=iteration,
                    error="Two consecutive compilation failures",
                )
            # Trim and retry even after compile failure
            selected_content = await _trim_longest_bullets(
                selected_content,
                pct=0.15,
                llm_client=llm_client,
                config=config,
                page_count=last_page_count,
                page_height=last_page_height,
            )
            continue

        consecutive_failures = 0

        # Analyze PDF metrics
        analysis = analyze_fn(str(pdf_path))
        if not analysis.get("success", False):
            logger.warning("PDF analysis failed at iter %d: %s", iteration, analysis.get("error"))
            # Treat as compile failure to be safe
            consecutive_failures += 1
            if consecutive_failures >= 2:
                return LoopResult(
                    success=False,
                    iteration_count=iteration,
                    error="Two consecutive compilation failures",
                )
            selected_content = await _trim_longest_bullets(
                selected_content,
                pct=0.15,
                llm_client=llm_client,
                config=config,
                page_count=last_page_count,
                page_height=last_page_height,
            )
            continue

        page_count: int = analysis["page_count"]
        page_height: float = analysis["page_height_inches"]
        whitespace_ratio: float = analysis["whitespace_ratio"]
        last_page_count = page_count
        last_page_height = page_height

        logger.info(
            "Iter %d: pages=%d height=%.1fin whitespace=%.2f",
            iteration,
            page_count,
            page_height,
            whitespace_ratio,
        )

        # Success condition: page_count == 1 AND height <= 11.5in
        if page_count == 1 and page_height <= 11.5:
            whitespace_warning = whitespace_ratio > 0.40
            _cleanup_iterations(all_iteration_paths, keep_tex=tex_path, keep_pdf=pdf_path)
            return LoopResult(
                success=True,
                iteration_count=iteration,
                pdf_path=pdf_path,
                tex_path=tex_path,
                whitespace_warning=whitespace_warning,
            )

        # Overflow: page_count > 1 or height > 11.5in — check max_iterations
        if iteration >= max_iterations:
            logger.warning(
                "Max iterations (%d) reached without fitting to one page", max_iterations
            )
            _cleanup_iterations(all_iteration_paths, keep_tex=tex_path, keep_pdf=pdf_path)
            return LoopResult(
                success=False,
                iteration_count=iteration,
                pdf_path=pdf_path,
                tex_path=tex_path,
                page_fit_warning=True,
            )

        # Trim and retry
        selected_content = await _trim_longest_bullets(
            selected_content,
            pct=0.15,
            llm_client=llm_client,
            config=config,
            page_count=page_count,
            page_height=page_height,
        )

    # Should not reach here (loop exits via return or iteration >= max_iterations check)
    return LoopResult(success=False, iteration_count=iteration, error="Unexpected loop exit")
