# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** From job description to application-ready resume + cover letter in under 15 minutes, with zero manual formatting work.
**Current focus:** Phase 4 — Resume Generation Pipeline

## Current Position

Phase: 4 of 7 (Resume Generation Pipeline)
Plan: 1 of TBD in current phase
Status: In progress
Last activity: 2026-02-23 — Completed Plan 01 (resume content selection module)

Progress: [████░░░░░░] 30%

## Performance Metrics

**Velocity:**
- Total plans completed: 4
- Average duration: 2 min
- Total execution time: 0.10 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-storage-and-configuration | 2 | 4 min | 2 min |
| 02-llm-client-and-prompt-registry | 2 | 4 min | 2 min |

**Recent Trend:**
- Last 5 plans: 2 min
- Trend: Stable

*Updated after each plan completion*
| Phase 01-storage-and-configuration P01 | 2 | 2 tasks | 5 files |
| Phase 01-storage-and-configuration P02 | 2 | 2 tasks | 6 files |
| Phase 02-llm-client-and-prompt-registry P01 | 2 | 2 tasks | 6 files |
| Phase 02-llm-client-and-prompt-registry P02 | 2 | 2 tasks | 4 files |
| Phase 02-llm-client-and-prompt-registry P03 | 2 | 2 tasks | 6 files |
| Phase 03-latex-engine-and-pdf-analyzer P02 | 1 | 2 tasks | 3 files |
| Phase 04-resume-generation-pipeline P01 | 2 | 1 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: LLM must never emit raw LaTeX — LLM produces JSON, Jinja2 produces .tex (eliminates largest bug class)
- [Init]: PDF page count (`fitz page_count > 1`) is the primary overflow signal, not whitespace percentage
- [Init]: Cover letter output is plain .txt — eliminates docx/LibreOffice dependency entirely
- [Init]: FastAPI BackgroundTasks (not Celery/Redis) for generation — sufficient for single-user personal tool
- [01-01]: use_enum_values=True in JobRecord.model_config so JSON output contains plain strings, not enum objects
- [01-01]: APP_ env prefix on AppConfig prevents collisions with system env vars
- [01-01]: data_dir resolved to absolute path via field_validator at config load time
- [01-01]: No custom to_json/from_json wrappers on JobRecord; call sites use model_dump_json() directly
- [01-02]: No python-slugify dependency — slug sanitization uses stdlib re with full control and zero extra dependency
- [01-02]: Path traversal pre-check before character stripping — catches '../../../etc' before re.sub makes it appear safe
- [01-02]: Atomic write via tempfile+fsync+os.replace — job.json never left in partially-written state
- [01-02]: write() enforces absolute job_dir with ValueError — prevents silent relative-path bugs when cwd differs
- [01-02]: list_all() silently skips directories without valid job.json (DEBUG log) — robust to manually created dirs
- [02-01]: anthropic_api_key made optional (default=None) — Ollama replaces Anthropic; old .env files still load without error
- [02-01]: llm_model renamed to llm_default_model — aligns with Ollama multi-model usage pattern
- [02-01]: llm_timeout_seconds default lowered from 120s to 60s — local Ollama inference is faster than remote API
- [02-01]: _is_transient() uses string matching on error repr — avoids brittle isinstance checks against Ollama internals
- [02-01]: LLMError wraps RetryError from Tenacity — callers see one consistent exception type regardless of failure mode
- [Phase 02-llm-client-and-prompt-registry]: json-repair used instead of fix-busted-json — fix-busted-json 0.0.19 crashes on Python 3.13 with IndexError; json-repair is maintained and compatible
- [Phase 02-llm-client-and-prompt-registry]: ValueError raised with first 300 chars of input when repair returns empty/null — gives callers actionable debug info for LLM output parse failures
- [Phase 02-llm-client-and-prompt-registry]: Jinja2 FileSystemLoader with StrictUndefined — prompt variables must be explicitly supplied, catches mismatches at render time
- [Phase 02-llm-client-and-prompt-registry]: Memory caching via module-level _JINJA_ENV — process restart required to pick up prompt file edits (acceptable for single-user CLI tool)
- [Phase 02-llm-client-and-prompt-registry]: FileNotFoundError lists available prompts — callers get actionable debug info without inspecting filesystem
- [Phase 03-latex-engine-and-pdf-analyzer]: compile_tex does not handle iter_N naming — caller names .tex file, tectonic derives PDF name from stem (thin wrapper)
- [Phase 03-latex-engine-and-pdf-analyzer]: analyze_pdf page_height_inches field enables Phase 4 single-tall-page overflow detection (> 11.5in, tectonic Pitfall 3)
- [Phase 03-latex-engine-and-pdf-analyzer]: check_ats_parsability returns True when pdftotext not installed — non-blocking, assume OK
- [Phase 04-01]: jd_payload intentionally sparse in Phase 4 (basic fields only) — Phase 5 enriches responsibilities/qualifications via LLM JD parsing
- [Phase 04-01]: LLM ranks experiences/projects; skills filtered via keyword matching only — avoids skill hallucination
- [Phase 04-01]: select_resume.md updated: jd_fields input (not raw job_description), ranked_experiences/ranked_projects output, ONLY-from-master constraint

### Pending Todos

None yet.

### Blockers/Concerns

- [Research]: Whitespace threshold (40%) for EXPAND trigger not validated for current template — calibrate empirically during Phase 4 with 5 sample resumes before shipping
- [Research]: tectonic first-run downloads LaTeX packages (60-120s) — web UI must communicate this clearly, not show a hung spinner
- [Research]: FastAPI BackgroundTasks tasks are killed on server restart — confirm acceptable for single-user personal tool before Phase 6

## Session Continuity

Last session: 2026-02-23
Stopped at: Completed 04-01-PLAN.md (resume content selection module)
Resume file: None
