# Phase 1: Storage and Configuration - Context

**Gathered:** 2026-02-22
**Status:** Ready for planning

<domain>
## Phase Boundary

The data layer and config system that every subsequent phase depends on: the `JobRecord` Pydantic model, a JSON filesystem store that reads/writes job records, and pydantic-settings configuration loading. No LLM calls, no LaTeX, no HTTP — pure infrastructure.

</domain>

<decisions>
## Implementation Decisions

### Filesystem layout
- Directory naming: `<company-slug>-<role-slug>` (e.g., `google-software-engineer`) — both company and role in the slug so each application always gets its own unique path
- Collision handling: if `google-software-engineer` already exists, append a counter (`google-software-engineer-2`, `google-software-engineer-3`, etc.) — silent auto-increment, no errors raised
- Artifact co-location: all artifacts live flat in the job directory alongside `job.json` — no subdirectories (e.g., `data/google-software-engineer/job.json`, `resume.pdf`, `cover.txt`, `resume_iter_1.tex`)
- List ordering: store returns records sorted most-recent-first by `created_at` timestamp

### Claude's Discretion
- `JobRecord` schema fields, status enum values, and required vs optional field definitions
- Config required vs optional fields and startup error messaging
- Slug sanitization implementation (path traversal protection, special character stripping)
- Internal read/write error handling patterns

</decisions>

<specifics>
## Specific Ideas

- No specific references — the filesystem layout decisions above are the primary constraints

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-storage-and-configuration*
*Context gathered: 2026-02-22*
