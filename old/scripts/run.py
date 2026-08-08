"""End-to-end pipeline: JD intake -> resume PDF + cover letter TXT + tracker row.

Reads input/jd.txt, parses it with JDService, generates a tailored resume
PDF with ResumeService, then generates a cover letter TXT with CoverLetterService.
All artifacts are saved under data/<company_slug>/ and the job application
tracker workbook is updated.

Usage:
    python scripts/run.py

Requirements:
    - Ollama running locally (ollama serve)
    - tectonic installed (brew install tectonic)
    - input/jd.txt populated with a job description
    - templates/master_resume.json populated
    - .env file with APP_LLM_DEFAULT_MODEL set (e.g. APP_LLM_DEFAULT_MODEL=llama3.1:8b)
"""
import asyncio
import json
import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import AppConfig
from src.cover_letter.service import CoverLetterService
from src.jd.service import JDService
from src.llm.client import LLMClient
from src.models.job_record import JobStatus
from src.resume.service import ResumeService
from src.storage.job_store import JobStore
from src.storage.tracker_store import update_application_tracker


def load_input_jd() -> str:
    jd_path = PROJECT_ROOT / "input" / "jd.txt"
    if not jd_path.exists():
        print(f"ERROR: input/jd.txt not found at {jd_path}")
        print("Paste your job description into input/jd.txt and re-run.")
        sys.exit(1)
    text = jd_path.read_text(encoding="utf-8").strip()
    if not text:
        print("ERROR: input/jd.txt is empty. Paste a job description into it.")
        sys.exit(1)
    return text


def load_master_resume() -> dict:
    path = PROJECT_ROOT / "templates" / "master_resume.json"
    if not path.exists():
        print(f"ERROR: templates/master_resume.json not found at {path}")
        sys.exit(1)
    with path.open() as f:
        return json.load(f)


async def main() -> None:
    print("=== Resume + Cover Letter Pipeline ===")
    print()

    # --- Load inputs ---
    jd_text = load_input_jd()
    print(f"Loaded input/jd.txt ({len(jd_text)} chars)")

    master_resume = load_master_resume()
    print(f"Loaded master_resume.json ({len(str(master_resume))} chars)")

    # --- Config + clients ---
    config = AppConfig()
    print(f"Model: {config.llm_default_model}  |  Host: {config.llm_host}")
    print()

    llm_client = LLMClient(config)
    store = JobStore(config.data_dir)

    # -------------------------------------------------------------------------
    # Step 1: Parse JD → JobRecord
    # -------------------------------------------------------------------------
    print("Step 1/4: Parsing job description...")
    jd_service = JDService(config, llm_client)
    jd_result = await jd_service.parse_and_persist(jd_text, store)

    if not jd_result.success:
        print(f"\nERROR: JD parsing failed — {jd_result.error}")
        sys.exit(1)

    job_record = jd_result.job_record
    print(f"  Parsed:  {job_record.role} @ {job_record.company}")
    print(f"  Location: {job_record.location}")
    f1_label = {True: "yes", False: "no", None: "unknown"}[job_record.f1_sponsorship_available]
    print(f"  F1 sponsorship: {f1_label}")
    print(f"  Job dir: {job_record.job_dir}")
    print()

    # -------------------------------------------------------------------------
    # Step 2: Generate resume PDF
    # -------------------------------------------------------------------------
    print("Step 2/4: Generating tailored resume (this may take 1-3 minutes)...")
    resume_service = ResumeService(config, llm_client)
    resume_result = await resume_service.generate(job_record, master_resume)

    if not resume_result.success and resume_result.pdf_path is None:
        print(f"\nERROR: Resume generation failed — {resume_result.error}")
        sys.exit(1)

    if resume_result.page_fit_warning:
        print("  WARNING: Resume may not fit on one page (max iterations reached)")
    if resume_result.validation_warning:
        print(f"  WARNING: Validation issues: {resume_result.validation_violations}")

    print(f"  PDF:  {resume_result.pdf_path}")
    print(f"  TeX:  {resume_result.tex_path}")
    print(f"  Iterations: {resume_result.iteration_count}")
    print()

    # Update job_record with resume path for cover letter context
    if resume_result.pdf_path:
        job_record.resume_pdf_path = str(resume_result.pdf_path)
        store.write(job_record)

    # -------------------------------------------------------------------------
    # Step 3: Generate cover letter
    # -------------------------------------------------------------------------
    print("Step 3/4: Generating cover letter...")

    # Read selected_resume.json written by the TRIM loop — this is the
    # tailored resume content the cover letter should reference.
    selected_resume_path = Path(job_record.job_dir) / "selected_resume.json"
    if selected_resume_path.exists():
        selected_resume_json = selected_resume_path.read_text(encoding="utf-8")
    else:
        # Fallback: use full master resume if selection file is missing
        selected_resume_json = json.dumps(master_resume)

    cl_service = CoverLetterService(config, llm_client)
    cl_result = await cl_service.generate(job_record, selected_resume_json, store)

    if not cl_result.success:
        print(f"\nERROR: Cover letter generation failed — {cl_result.error}")
        sys.exit(1)

    print(f"  TXT:  {cl_result.txt_path}")
    if cl_result.pdf_path:
        print(f"  PDF:  {cl_result.pdf_path}")
    else:
        print("  PDF:  (compilation skipped or failed)")
    print(f"  Word count: {cl_result.word_count}")
    print()

    # Mark artifacts ready only after both generation stages finish.
    job_record.status = JobStatus.READY
    job_record.mark_updated()
    store.write(job_record)

    # -------------------------------------------------------------------------
    # Step 4: Update job application tracker
    # -------------------------------------------------------------------------
    print("Step 4/4: Updating job application tracker...")
    tracker_result = None
    try:
        tracker_result = update_application_tracker(job_record, config.tracker_path)
        action = "Added" if tracker_result.created else "Updated"
        print(f"  {action} tracker row: {tracker_result.row_number}")
        print(f"  Workbook: {tracker_result.workbook_path}")
    except Exception as exc:
        print(f"  WARNING: Tracker update failed — {exc}")
    print()

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print("=== Done ===")
    print(f"Company:       {job_record.company}")
    print(f"Role:          {job_record.role}")
    print(f"Output dir:    {job_record.job_dir}")
    print(f"Resume PDF:    {resume_result.pdf_path}")
    print(f"Cover letter:  {cl_result.txt_path}")
    if cl_result.pdf_path:
        print(f"Cover letter PDF: {cl_result.pdf_path}")
    if tracker_result:
        print(f"Tracker row:   {tracker_result.row_number}")


try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nInterrupted.")
    sys.exit(130)
except Exception:
    print()
    print("=== Unexpected Error ===")
    traceback.print_exc()
    sys.exit(1)
