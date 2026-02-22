# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** From job description to application-ready resume + cover letter in under 15 minutes, with zero manual formatting work.
**Current focus:** Phase 1 — Storage and Configuration

## Current Position

Phase: 1 of 7 (Storage and Configuration)
Plan: 1 of TBD in current phase
Status: In progress
Last activity: 2026-02-22 — Completed Plan 01 (JobRecord model and AppConfig)

Progress: [█░░░░░░░░░] 5%

## Performance Metrics

**Velocity:**
- Total plans completed: 1
- Average duration: 2 min
- Total execution time: 0.03 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-storage-and-configuration | 1 | 2 min | 2 min |

**Recent Trend:**
- Last 5 plans: 2 min
- Trend: —

*Updated after each plan completion*
| Phase 01-storage-and-configuration P01 | 2 | 2 tasks | 5 files |

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
- [01-01]: anthropic_api_key has no default — raises ValidationError immediately if missing
- [01-01]: No custom to_json/from_json wrappers on JobRecord; call sites use model_dump_json() directly
- [Phase 01-01]: use_enum_values=True in JobRecord.model_config so JSON output contains plain strings not enum objects
- [Phase 01-01]: APP_ env prefix on AppConfig prevents collisions with system env vars; anthropic_api_key required with no default for fail-fast startup validation

### Pending Todos

None yet.

### Blockers/Concerns

- [Research]: Whitespace threshold (40%) for EXPAND trigger not validated for current template — calibrate empirically during Phase 4 with 5 sample resumes before shipping
- [Research]: tectonic first-run downloads LaTeX packages (60-120s) — web UI must communicate this clearly, not show a hung spinner
- [Research]: FastAPI BackgroundTasks tasks are killed on server restart — confirm acceptable for single-user personal tool before Phase 6

## Session Continuity

Last session: 2026-02-22
Stopped at: Completed 01-01-PLAN.md (JobRecord model and AppConfig) — ready for Plan 02 (JobStore filesystem layer)
Resume file: None
