"""Phase 4 end-to-end pipeline smoke test.

Exercises the full Phase 4 pipeline against real artifacts (no mocking):
  1. Load templates/master_resume.json
  2. Load AppConfig from environment (uses .env or defaults)
  3. Create LLMClient with the config
  4. Create a test JobRecord with a realistic job_dir under data/test-phase4/
  5. Create ResumeService and call generate()
  6. Print result with all warning flags
  7. Assert success or print clear failure message

Requirements:
  - Ollama running locally (same as Phase 2 requirements)
  - tectonic installed (same as Phase 3 requirements)
  - templates/master_resume.json populated
  - .env file with APP_DATA_DIR configured

Runtime: 30-120 seconds depending on Ollama speed and TRIM iterations needed.
         tectonic first-run may download LaTeX packages (60-120s additional).

Usage:
    python scripts/test_pipeline.py
"""
import asyncio
import json
import sys
import traceback
from pathlib import Path

print("=== Phase 4 Pipeline Smoke Test ===")
print("NOTE: This requires Ollama running and tectonic installed.")
print()

# ---------------------------------------------------------------------------
# Setup: ensure project root is on sys.path so src.* imports work
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Imports (after sys.path fix)
# ---------------------------------------------------------------------------

from src.config import AppConfig
from src.llm.client import LLMClient
from src.models.job_record import JobRecord
from src.resume.service import ResumeService


# ---------------------------------------------------------------------------
# Load master_resume.json
# ---------------------------------------------------------------------------

def load_master_resume() -> dict:
    """Load the master resume from templates/master_resume.json."""
    master_resume_path = PROJECT_ROOT / "templates" / "master_resume.json"
    if not master_resume_path.exists():
        print(f"ERROR: master_resume.json not found at {master_resume_path}")
        print("Please populate templates/master_resume.json before running this test.")
        sys.exit(1)
    with master_resume_path.open() as f:
        data = json.load(f)
    print(f"Loaded master_resume.json ({len(str(data))} chars)")
    return data


# ---------------------------------------------------------------------------
# Main async entry point
# ---------------------------------------------------------------------------

async def main() -> "ResumeGenerationResult":
    """Run the full Phase 4 pipeline smoke test."""

    # --- Load config ---
    config = AppConfig()
    print(f"AppConfig loaded: data_dir={config.data_dir}, llm_host={config.llm_host}, model={config.llm_default_model}")

    # --- Load master resume ---
    master_resume = load_master_resume()

    # --- Create LLM client ---
    llm_client = LLMClient(config)
    print(f"LLMClient created (host={config.llm_host})")

    # --- Load JD from input/jd.txt ---
    jd_path = PROJECT_ROOT / "input" / "jd.txt"
    if not jd_path.exists():
        print(f"ERROR: input/jd.txt not found at {jd_path}")
        print("Please paste your job description into input/jd.txt before running.")
        sys.exit(1)
    jd_text = jd_path.read_text(encoding="utf-8").strip()
    if not jd_text:
        print("ERROR: input/jd.txt is empty. Please paste a job description into it.")
        sys.exit(1)
    print(f"Loaded input/jd.txt ({len(jd_text)} chars)")

    # --- Create test job directory ---
    test_dir = PROJECT_ROOT / "data" / "test-phase4"
    test_dir.mkdir(parents=True, exist_ok=True)
    print(f"Test job directory: {test_dir.resolve()}")

    # --- Create test JobRecord ---
    job_record = JobRecord(
        company="Test Corp",
        role="Software Engineer",
        location="San Francisco, CA",
        job_dir=str(test_dir.resolve()),
        jd_text=jd_text,
    )
    print(f"JobRecord: {job_record.role} @ {job_record.company}")
    print()

    # --- Create service and generate ---
    service = ResumeService(config, llm_client)
    print("Starting generate() call — this may take 30-120 seconds...")
    print()

    result = await service.generate(job_record, master_resume)

    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

try:
    result = asyncio.run(main())

    print()
    print("=== Phase 4 Pipeline Result ===")
    print(f"Success:             {result.success}")
    print(f"PDF path:            {result.pdf_path}")
    print(f"TeX path:            {result.tex_path}")
    print(f"Iterations:          {result.iteration_count}")
    print(f"page_fit_warning:    {result.page_fit_warning}")
    print(f"whitespace_warning:  {result.whitespace_warning}")
    print(f"validation_warning:  {result.validation_warning}")
    if result.validation_violations:
        print(f"Violations:          {result.validation_violations}")
    if result.error:
        print(f"Error:               {result.error}")

    print()
    if result.success:
        print(f"RESULT: SUCCESS")
        if result.pdf_path:
            print(f"Generated PDF: {result.pdf_path.resolve()}")
    elif result.page_fit_warning:
        print("RESULT: PARTIAL SUCCESS (page_fit_warning — max iterations reached)")
        if result.pdf_path:
            print(f"Partial PDF: {result.pdf_path.resolve()}")
    else:
        print(f"RESULT: FAILED")
        if result.error:
            print(f"Failure reason: {result.error}")
        sys.exit(1)

except KeyboardInterrupt:
    print("\nInterrupted by user.")
    sys.exit(130)

except Exception:
    print()
    print("=== Pipeline Error ===")
    traceback.print_exc()
    sys.exit(1)
