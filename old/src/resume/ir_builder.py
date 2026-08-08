"""Pure render-IR assembly — master_resume + content selection -> template payload.

This module is deliberately free of LLM imports. It converts master_resume.json
naming (technical_skills / achievements / tech_stack / details) into the
resume_json_template.json render IR that resume_template.tex.j2 consumes
(section.lines / entry.bullets / entry.techStack / entry.techBracket).

Two entry points share the same builders:
  - _assemble_payload() — legacy signature used by selection.py (pre-selected dicts)
  - build_resume_payload() — id-based signature used by the /add-job skill

build_resume_payload is the fabrication-proof path: the caller names *which*
entries to include and may override only bullet text. Dates, employers, roles,
degrees, institutions, and tech stacks are always read from master_resume, so a
caller cannot express a changed date or employer at all.
"""
import logging
import re

logger = logging.getLogger(__name__)

# Fixed section order — resume_json_template.json pins sections to exactly 5.
SECTION_ORDER = (
    "education",
    "technical_skills",
    "work_experience",
    "projects_and_research",
    "extracurricular",
)

_CATEGORY_LABELS = {
    "programming": "Programming & Scripting",
    "frameworks": "Frameworks & Libraries",
    "developer_tools": "Developer Tools",
    "libraries": "Libraries & AI/ML",
}

_STATIC_META = {
    "templateName": "compact_2col_ats_resume",
    "version": "1.0.0",
    "engine": "pdflatex",
    "output": {
        "format": "latex",
        "targetPages": 1,
        "atsReadable": True,
    },
}

_STATIC_STYLE = {
    "document": {
        "class": "article",
        "options": ["9pt", "letterpaper"],
    },
    "page": {
        "geometry": {
            "ignoreHeadFoot": True,
            "topCm": 0.5,
            "bottomCm": 0.5,
            "leftCm": 0.7,
            "rightCm": 0.7,
            "footskipCm": 0.2,
        }
    },
    "typography": {
        "fontFamily": "charter",
        "raggedRight": True,
        "paragraphIndentPt": 0,
        "topSkipPt": 0,
        "pageStyle": "empty",
        "pageNumbering": "gobble",
    },
    "layout": {
        "columnSepCm": 0.15,
        "rightDateColumnWidthCm": 4.5,
    },
    "sections": {
        "uppercaseTitles": True,
        "bold": True,
        "size": "large",
        "ruleUnderTitle": True,
        "spacing": {
            "leftPt": -1,
            "topCm": 0.05,
            "bottomCm": 0.05,
        },
    },
    "lists": {
        "bullet": "small_bullet",
        "highlights": {
            "topsepCm": 0.05,
            "parsepPt": 0,
            "partopsepPt": 0,
            "itemsepPt": 0,
            "leftmarginPt": 10,
        },
    },
    "constraints": {
        "singlePage": True,
        "noGraphics": True,
        "noTablesForLayout": True,
        "noIcons": True,
        "noEmDash": True,
        "noFirstPerson": True,
    },
}


# ---------------------------------------------------------------------------
# Id derivation — the stable handles a content selection refers to
# ---------------------------------------------------------------------------


def _full_slug(text: str) -> str:
    """Slugify without sanitize_slug's 50-char cap.

    The cap exists for directory names; ids need to stay distinguishable.
    Two Siemens roles in master_resume differ only past character 45, so a
    truncated id would risk silent collisions as entries are added.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    if not slug:
        raise ValueError(f"Cannot derive an id from {text!r}")
    return slug


def experience_id(experience: dict) -> str:
    """Stable slug id for a work_experience entry: '<company>-<title>'."""
    company = experience.get("company", "")
    title = experience.get("title", "")
    return _full_slug(f"{company} {title}")


def project_id(project: dict) -> str:
    """Stable slug id for a projects_and_research entry: '<title>'."""
    return _full_slug(project.get("title", ""))


def available_ids(master_resume: dict) -> dict:
    """Enumerate the ids a resume_content.json may reference.

    Returns a dict with 'experience_ids', 'project_ids', 'skill_categories',
    and 'extracurricular_count' — the vocabulary a caller must stay inside.

    Raises:
        ValueError: if two entries derive the same id, which would make a
                    content selection ambiguous.
    """
    experience_ids = [
        experience_id(exp) for exp in master_resume.get("work_experience", [])
    ]
    project_ids = [
        project_id(proj) for proj in master_resume.get("projects_and_research", [])
    ]
    _reject_duplicate_ids(experience_ids, "work_experience")
    _reject_duplicate_ids(project_ids, "projects_and_research")

    return {
        "experience_ids": experience_ids,
        "project_ids": project_ids,
        "skill_categories": sorted(master_resume.get("technical_skills", {})),
        "extracurricular_count": len(master_resume.get("extracurricular", [])),
    }


def _reject_duplicate_ids(ids: list[str], source: str) -> None:
    """Fail loudly on colliding ids rather than silently dropping an entry."""
    duplicates = sorted({entry for entry in ids if ids.count(entry) > 1})
    if duplicates:
        raise ValueError(
            f"master_resume {source} produces duplicate ids {duplicates}; "
            "disambiguate the titles or companies"
        )


# ---------------------------------------------------------------------------
# Public API — id-based (the /add-job path)
# ---------------------------------------------------------------------------


def build_resume_payload(master_resume: dict, content: dict) -> dict:
    """Assemble a render-IR payload from master_resume plus a content selection.

    content shape (all keys optional except experience_ids / project_ids):
        {
          "experience_ids": ["siemens-...", ...],       # order = resume order
          "project_ids": ["policypilot", ...],
          "skills": {"programming": [...], ...},        # subset of master
          "experience_overrides": {"<id>": {"bullets": [...]}},
          "project_overrides": {"<id>": {"bullets": [...]}},
          "extracurricular_indices": [0, 1],
          "summary": "..."                             # optional rewrite
        }

    Only bullet text (and the optional summary) may be overridden. Every factual
    field comes from master_resume.

    Raises:
        ValueError: unknown id, unknown skill category, skill not in master,
                    out-of-range extracurricular index, or an override carrying
                    a disallowed key.
    """
    experiences = _resolve_experiences(master_resume, content)
    projects = _resolve_projects(master_resume, content)
    skills = _resolve_skills(master_resume, content)
    extracurricular = _resolve_extracurricular(master_resume, content)

    # No 'summary' key: resume_json_template.json sets additionalProperties:false
    # at the root and allows only meta/style/header/sections. The template's
    # PROFESSIONAL SUMMARY block is unreachable by design, matching
    # resume_generation_prompt.md rule 6 ("do not add a Summary section").
    if content.get("summary"):
        raise ValueError(
            "resume_content.json must not set 'summary': the render schema "
            "forbids it and resume_generation_prompt.md rule 6 bans adding a "
            "Summary section. Fold the framing into the first experience bullets."
        )

    return {
        "meta": _deep_copy(_STATIC_META),
        "style": _deep_copy(_STATIC_STYLE),
        "header": _build_header(master_resume),
        "sections": [
            _build_education_section(master_resume),
            _build_skills_section(skills),
            _build_experience_section(experiences),
            _build_projects_section(projects),
            _build_extracurricular_section({"extracurricular": extracurricular}),
        ],
    }


def _resolve_experiences(master_resume: dict, content: dict) -> list[dict]:
    """Select and bullet-override work experiences by id, preserving caller order."""
    by_id = {
        experience_id(exp): exp for exp in master_resume.get("work_experience", [])
    }
    ids = content.get("experience_ids") or list(by_id)
    overrides = content.get("experience_overrides") or {}
    _reject_unknown_override_keys(overrides, by_id, "experience")

    resolved = []
    for entry_id in ids:
        source = by_id.get(entry_id)
        if source is None:
            raise ValueError(
                f"Unknown experience_id {entry_id!r}. Valid ids: {sorted(by_id)}"
            )
        merged = dict(source)
        bullets = _override_bullets(overrides.get(entry_id), entry_id)
        if bullets is not None:
            merged["achievements"] = bullets
        resolved.append(merged)
    return resolved


def _resolve_projects(master_resume: dict, content: dict) -> list[dict]:
    """Select and bullet-override projects by id, preserving caller order."""
    by_id = {
        project_id(proj): proj
        for proj in master_resume.get("projects_and_research", [])
    }
    ids = content.get("project_ids") or list(by_id)
    overrides = content.get("project_overrides") or {}
    _reject_unknown_override_keys(overrides, by_id, "project")

    resolved = []
    for entry_id in ids:
        source = by_id.get(entry_id)
        if source is None:
            raise ValueError(
                f"Unknown project_id {entry_id!r}. Valid ids: {sorted(by_id)}"
            )
        merged = dict(source)
        bullets = _override_bullets(overrides.get(entry_id), entry_id)
        if bullets is not None:
            merged["details"] = bullets
        resolved.append(merged)
    return resolved


def _override_bullets(override: dict | None, entry_id: str) -> list[str] | None:
    """Extract the 'bullets' list from an override, rejecting any other key.

    Rejecting unknown keys is what makes date/company tampering impossible:
    an attempt to override 'dates' fails loudly instead of being ignored.
    """
    if override is None:
        return None
    if not isinstance(override, dict):
        raise ValueError(f"Override for {entry_id!r} must be an object")

    extra = set(override) - {"bullets"}
    if extra:
        raise ValueError(
            f"Override for {entry_id!r} may only set 'bullets'; "
            f"got disallowed keys {sorted(extra)}. Dates, companies, roles, and "
            "tech stacks always come from master_resume.json."
        )

    bullets = override.get("bullets")
    if bullets is None:
        return None
    if not isinstance(bullets, list) or not all(isinstance(b, str) for b in bullets):
        raise ValueError(f"Override bullets for {entry_id!r} must be a list of strings")
    if not bullets:
        raise ValueError(f"Override bullets for {entry_id!r} must not be empty")
    return bullets


def _reject_unknown_override_keys(overrides: dict, by_id: dict, kind: str) -> None:
    """Fail loudly when an override targets an id that does not exist."""
    unknown = set(overrides) - set(by_id)
    if unknown:
        raise ValueError(
            f"Unknown {kind} override id(s) {sorted(unknown)}. "
            f"Valid ids: {sorted(by_id)}"
        )


def _resolve_skills(master_resume: dict, content: dict) -> dict:
    """Filter master skills to the caller's selection, preserving category keys.

    Every category and every item must exist in master_resume.technical_skills.
    Omitting 'skills' entirely keeps all master skills.
    """
    master_skills = master_resume.get("technical_skills", {})
    selection = content.get("skills")
    if not selection:
        return master_skills

    resolved: dict[str, list[str]] = {}
    for category, items in selection.items():
        if category not in master_skills:
            raise ValueError(
                f"Unknown skill category {category!r}. "
                f"Valid categories: {sorted(master_skills)}"
            )
        master_items = master_skills[category]
        master_lookup = {item.lower(): item for item in master_items}

        kept = []
        for item in items:
            canonical = master_lookup.get(item.lower())
            if canonical is None:
                raise ValueError(
                    f"Skill {item!r} is not in master_resume "
                    f"technical_skills.{category}. Valid: {master_items}"
                )
            kept.append(canonical)
        if kept:
            resolved[category] = kept

    if not resolved:
        raise ValueError("Skill selection resolved to zero categories")
    return resolved


def _resolve_extracurricular(master_resume: dict, content: dict) -> list[str]:
    """Select extracurricular bullets by index; omitting the key keeps all."""
    bullets = master_resume.get("extracurricular", [])
    indices = content.get("extracurricular_indices")
    if indices is None:
        return bullets

    resolved = []
    for index in indices:
        if not isinstance(index, int) or not 0 <= index < len(bullets):
            raise ValueError(
                f"extracurricular_indices entry {index!r} out of range "
                f"(0..{len(bullets) - 1})"
            )
        resolved.append(bullets[index])
    return resolved


def _deep_copy(value):
    """Copy nested dict/list literals so callers cannot mutate module constants."""
    if isinstance(value, dict):
        return {key: _deep_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_deep_copy(item) for item in value]
    return value


# ---------------------------------------------------------------------------
# Public API — legacy signature (selection.py path, behavior-preserving)
# ---------------------------------------------------------------------------


def _assemble_payload(
    master_resume: dict,
    selected_experiences: list[dict],
    selected_projects: list[dict],
    selected_skills: dict,
) -> dict:
    """Assemble the final resume_json_template.json-compatible payload.

    Uses hardcoded standard values for meta and style (matching the template defaults).
    Populates header from master_resume contact fields.
    Populates sections with education (all), skills (filtered), top experiences,
    top projects, and extracurricular (all).
    """
    return {
        "meta": _deep_copy(_STATIC_META),
        "style": _deep_copy(_STATIC_STYLE),
        "header": _build_header(master_resume),
        "sections": [
            _build_education_section(master_resume),
            _build_skills_section(selected_skills),
            _build_experience_section(selected_experiences),
            _build_projects_section(selected_projects),
            _build_extracurricular_section(master_resume),
        ],
    }


# ---------------------------------------------------------------------------
# Section builders — shared by both entry points
# ---------------------------------------------------------------------------


def _build_header(master_resume: dict) -> dict:
    """Build the header section from master_resume name and contact fields."""
    contact = master_resume.get("contact", {})
    contact_line = []

    if contact.get("email"):
        contact_line.append({"kind": "email", "text": contact["email"]})
    if contact.get("linkedin"):
        contact_line.append({"kind": "linkedin", "text": contact["linkedin"]})
    if contact.get("github"):
        contact_line.append({"kind": "github", "text": contact["github"]})
    if contact.get("portfolio"):
        contact_line.append({"kind": "portfolio", "text": contact["portfolio"]})
    if contact.get("phone"):
        contact_line.append({"kind": "phone", "text": contact["phone"]})

    return {
        "name": master_resume.get("name", ""),
        "nameFontPt": 16,
        "nameLineHeightPt": 26,
        "separator": "|",
        "contactLine": contact_line,
    }


def _build_education_section(master_resume: dict) -> dict:
    """Build education section from all master_resume education entries."""
    entries = []
    for edu in master_resume.get("education", []):
        start = edu.get("start_date", "")
        end = edu.get("end_date", "")
        dates = f"{start} - {end}" if start and end else start or end
        coursework = edu.get("coursework", [])
        coursework_line = (
            "Relevant Coursework: " + ", ".join(coursework) + "."
            if coursework
            else ""
        )
        entries.append({
            "degree": edu.get("degree", ""),
            "institution": edu.get("institution", ""),
            "dates": dates,
            "courseworkLine": coursework_line,
        })

    return {
        "type": "education",
        "title": "EDUCATION",
        "entries": entries,
    }


def _build_skills_section(selected_skills: dict) -> dict:
    """Build technical skills section from the filtered skills dict.

    Maps category keys to human-readable labels for the resume.
    """
    lines = []
    for category, skills_list in selected_skills.items():
        if isinstance(skills_list, list) and skills_list:
            label = _CATEGORY_LABELS.get(
                category, category.replace("_", " ").title()
            )
            lines.append({"label": label, "items": skills_list})

    return {
        "type": "technical_skills",
        "title": "TECHNICAL SKILLS",
        "lines": lines,
    }


def _build_experience_section(selected_experiences: list[dict]) -> dict:
    """Build work experience section from selected master_resume experiences."""
    entries = []
    for exp in selected_experiences:
        start = exp.get("start_date", "")
        end = exp.get("end_date", "")
        dates = f"{start} - {end}" if start and end else start or end

        entries.append({
            "company": exp.get("company", ""),
            "role": exp.get("title", ""),
            "dates": dates,
            "techStack": exp.get("tech_stack", []),
            "bullets": exp.get("achievements", []),
        })

    return {
        "type": "work_experience",
        "title": "WORK EXPERIENCE",
        "entries": entries,
    }


def _build_projects_section(selected_projects: list[dict]) -> dict:
    """Build projects and research section from selected master_resume projects."""
    entries = []
    for proj in selected_projects:
        entries.append({
            "title": proj.get("title", ""),
            "date": proj.get("date", ""),
            "techBracket": proj.get("tech_stack", []),
            "bullets": proj.get("details", []),
        })

    return {
        "type": "projects_and_research",
        "title": "PROJECTS AND RESEARCH",
        "entries": entries,
    }


def _build_extracurricular_section(master_resume: dict) -> dict:
    """Build extracurricular section from all master_resume extracurricular entries."""
    bullets = master_resume.get("extracurricular", [])
    return {
        "type": "extracurricular",
        "title": "EXTRACURRICULAR ACTIVITIES",
        "bullets": bullets,
    }
