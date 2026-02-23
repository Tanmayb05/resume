"""ResumeService orchestrator — full Phase 4 resume generation pipeline.

Coordinates all Phase 4 modules:
  1. Content selection (selection.py) — LLM ranking + keyword filter
  2. TRIM loop (trimmer.py) — compile-measure-trim-repeat for one-page enforcement
  3. Entity validation (validator.py) — structured field diff against master_resume

Usage:
    service = ResumeService(config, llm_client)
    result = await service.generate(job_record, master_resume)

The service is stateless — safe to share across concurrent requests (each call
receives its own job_record with a unique job_dir). The calling code in Phase 6
(FastAPI) creates a single service instance at startup.
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from src.config import AppConfig
from src.llm.client import LLMClient
from src.models.job_record import JobRecord
from src.resume.selection import select_resume_content
from src.resume.trimmer import trim_loop
from src.resume.validator import validate_content

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ResumeGenerationResult:
    """Structured result from ResumeService.generate().

    Attributes:
        success:              True when resume was compiled and fits on one page.
        pdf_path:             Path to the final PDF (set on success or partial success).
        tex_path:             Path to the final .tex source file.
        iteration_count:      Number of TRIM loop iterations that ran.
        page_fit_warning:     True if loop hit max_iterations without fitting to one page.
        whitespace_warning:   True if final PDF is over-trimmed (whitespace_ratio > 40%).
        validation_warning:   True if entity validation found violations.
        validation_violations: List of human-readable violation descriptions.
        error:                Error description on hard failure (compile failures, etc.).
    """

    success: bool
    pdf_path: Optional[Path] = None
    tex_path: Optional[Path] = None
    iteration_count: int = 0
    page_fit_warning: bool = False      # True if loop hit max_iterations without fitting
    whitespace_warning: bool = False    # True if final PDF is over-trimmed (>40% whitespace)
    validation_warning: bool = False    # True if entity validation found violations
    validation_violations: List[str] = field(default_factory=list)
    error: Optional[str] = None        # Set on hard failure (compile failures, etc.)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class ResumeService:
    """Stateless orchestrator for full resume generation pipeline.

    Coordinates: content selection (Plan 01) -> TRIM loop (Plan 02) ->
    entity validation (Plan 02) -> structured result.

    Stateless design: safe to share across concurrent requests (each call
    receives its own job_record with a unique job_dir).

    Usage:
        service = ResumeService(config, llm_client)
        result = await service.generate(job_record, master_resume)
    """

    def __init__(self, config: AppConfig, llm_client: LLMClient) -> None:
        self.config = config
        self.llm = llm_client

    async def generate(
        self,
        job_record: JobRecord,
        master_resume: dict,
    ) -> ResumeGenerationResult:
        """Generate a resume PDF for a job record.

        Orchestrates the full Phase 4 pipeline:
          1. select_resume_content() — LLM ranks and selects content from master_resume
          2. trim_loop() — compile, analyze, trim, repeat until one page or max iterations
          3. validate_content() — check selected content against master_resume (warn-only)

        Returns ResumeGenerationResult — never raises on business logic failures
        (max iterations, validation violations). Only raises on programming errors
        (bad config, missing files, broken imports).

        Validation runs once on final output — not on each iteration — and never
        blocks the return. The caller always receives a result.

        Args:
            job_record: Job application record (must have company, role, job_dir).
            master_resume: Parsed master_resume.json dict (full contents).

        Returns:
            ResumeGenerationResult with success flag, artifact paths, iteration count,
            warning flags, and optional error description.
        """
        job_dir = Path(job_record.job_dir)

        # Step 1: Select relevant content from master_resume
        logger.info(
            "Phase 4: selecting content for %s @ %s",
            job_record.role,
            job_record.company,
        )
        try:
            selected_content = await select_resume_content(
                job_record, master_resume, self.llm, self.config
            )
        except Exception as exc:
            logger.error("Content selection failed: %s", exc)
            return ResumeGenerationResult(
                success=False,
                error=f"Content selection failed: {exc}",
            )

        # Step 2: TRIM loop — compile, measure, trim, repeat
        max_iter = getattr(self.config, "max_iterations", 5)
        logger.info("Phase 4: starting TRIM loop (max_iterations=%s)", max_iter)

        # Import latex functions here to keep top-level imports clean and
        # allow the service module to be imported without tectonic installed.
        from src.latex import render_resume_tex, compile_tex, analyze_pdf

        loop_result = await trim_loop(
            selected_content=selected_content,
            job_dir=job_dir,
            llm_client=self.llm,
            config=self.config,
            render_fn=render_resume_tex,
            compile_fn=compile_tex,
            analyze_fn=analyze_pdf,
        )

        # Step 3: Entity validation — runs once on final output, never blocks
        validation_warning = False
        validation_violations: List[str] = []
        if loop_result.success or loop_result.pdf_path is not None:
            logger.info("Phase 4: running entity validation")
            val_result = validate_content(selected_content, master_resume)
            validation_warning = val_result.validation_warning
            validation_violations = val_result.violations

        # Step 4: Assemble and return structured result
        return ResumeGenerationResult(
            success=loop_result.success,
            pdf_path=loop_result.pdf_path,
            tex_path=loop_result.tex_path,
            iteration_count=loop_result.iteration_count,
            page_fit_warning=loop_result.page_fit_warning,
            whitespace_warning=loop_result.whitespace_warning,
            validation_warning=validation_warning,
            validation_violations=validation_violations,
            error=loop_result.error,
        )
