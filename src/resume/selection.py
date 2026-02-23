"""LLM-driven resume content selection module.

Selects the most relevant work experiences and projects from the master resume
for a given job, using LLM ranking. Skills are filtered separately via keyword
matching. Assembles a resume_json_template.json-compatible payload.

Pipeline position: First stage — selection feeds into render_resume_tex (Plan 03).
"""
import json
import logging
from pathlib import Path

from src.config import AppConfig
from src.llm.client import LLMClient
from src.llm.utils import extract_json, load_prompt
from src.models.job_record import JobRecord

logger = logging.getLogger(__name__)

# Number of top experiences and projects to select
_TOP_EXPERIENCES = 3
_TOP_PROJECTS = 2


async def select_resume_content(
    job_record: JobRecord,
    master_resume: dict,
    llm_client: LLMClient,
    config: AppConfig,
) -> dict:
    """Select relevant resume content for a specific job using LLM ranking.

    Builds a jd_payload from job_record fields, asks the LLM to rank all
    experiences and projects by relevance, then picks the top N of each.
    Skills are selected via keyword matching (not LLM).

    The returned dict matches the resume_json_template.json schema and is
    ready to pass directly to render_resume_tex().

    jd_payload is intentionally sparse for Phase 4 — Phase 5 enriches job_record
    fields (skills, responsibilities, qualifications) from the full JD text.

    Args:
        job_record: Job application record (must have company, role, job_dir).
        master_resume: Parsed master_resume.json as a dict.
        llm_client: Configured async LLM client.
        config: Application configuration.

    Returns:
        dict matching resume_json_template.json schema with selected content.

    Raises:
        ValueError: If the LLM returns unparseable JSON (caller decides retry).
    """
    # Step 1: Extract JD fields from job_record.
    # Phase 4 works with basic fields; Phase 5 will enrich jd_text into structured fields.
    jd_payload = _build_jd_payload(job_record, master_resume)
    logger.debug(
        "select_resume_content: jd_payload built for %s @ %s",
        job_record.role,
        job_record.company,
    )

    # Step 2: Load and render the prompt with structured JD fields + full master resume
    prompt = load_prompt(
        "select_resume",
        jd_fields=json.dumps(jd_payload, indent=2),
        master_resume_json=json.dumps(master_resume, indent=2),
    )

    # Step 3: Call LLM to get ranked experiences and projects
    logger.debug("select_resume_content: calling LLM for ranking")
    try:
        raw = await llm_client.call(prompt)
        ranking = extract_json(raw)
    except ValueError as exc:
        logger.error(
            "select_resume_content: LLM returned unparseable JSON for %s @ %s: %s",
            job_record.role,
            job_record.company,
            exc,
        )
        raise  # Caller (ResumeService in Plan 03) decides whether to retry

    # Step 4: Extract top-N experiences and projects from ranking
    selected_experiences = _select_top_experiences(
        ranking.get("ranked_experiences", []),
        master_resume.get("work_experience", []),
        top_n=_TOP_EXPERIENCES,
    )
    selected_projects = _select_top_projects(
        ranking.get("ranked_projects", []),
        master_resume.get("projects_and_research", []),
        top_n=_TOP_PROJECTS,
    )

    logger.debug(
        "select_resume_content: selected %d experiences, %d projects",
        len(selected_experiences),
        len(selected_projects),
    )

    # Step 5: Skills keyword filter
    selected_skills = _filter_skills(master_resume, jd_payload.get("skills", []))

    # Step 6: Assemble resume_json_template.json-compatible payload
    selected_content = _assemble_payload(
        master_resume=master_resume,
        selected_experiences=selected_experiences,
        selected_projects=selected_projects,
        selected_skills=selected_skills,
    )

    # Step 7: Save to selected_resume.json in the job directory
    job_dir = Path(job_record.job_dir)
    output_path = job_dir / "selected_resume.json"
    output_path.write_text(json.dumps(selected_content, indent=2))
    logger.info("select_resume_content: wrote selected_resume.json to %s", output_path)

    # Step 8: Return the assembled payload
    return selected_content


def _build_jd_payload(job_record: JobRecord, master_resume: dict) -> dict:
    """Build a structured JD payload dict from job_record fields.

    Phase 4 produces a sparse payload — Phase 5 will enrich responsibilities
    and qualifications from the full jd_text via LLM parsing.

    For skills: if jd_text is available, do a simple keyword pass against the
    master resume's flattened technical_skills list. Otherwise empty list.
    """
    # Gather all master skills (flat list) for keyword matching against JD text
    all_master_skills = _flatten_skills(master_resume.get("technical_skills", {}))

    extracted_skills: list[str] = []
    if job_record.jd_text:
        jd_lower = job_record.jd_text.lower()
        extracted_skills = [
            skill for skill in all_master_skills
            if skill.lower() in jd_lower
        ]

    return {
        "job_title": job_record.role,
        "company": job_record.company,
        "skills": extracted_skills,
        "responsibilities": [],   # Phase 5 enriches this
        "qualifications": [],     # Phase 5 enriches this
    }


def _flatten_skills(technical_skills: dict) -> list[str]:
    """Flatten all skill category lists into a single list."""
    flat: list[str] = []
    for category_skills in technical_skills.values():
        if isinstance(category_skills, list):
            flat.extend(category_skills)
    return flat


def _select_top_experiences(
    ranked: list[dict],
    work_experience: list[dict],
    top_n: int,
) -> list[dict]:
    """Sort ranked experiences by relevance_score descending, return top_n full dicts.

    The LLM uses "title|company" as the id. We match by checking if both title
    and company appear in the id string (case-insensitive).
    """
    sorted_ranked = sorted(
        ranked, key=lambda x: x.get("relevance_score", 0), reverse=True
    )

    selected: list[dict] = []
    seen_ids: set[str] = set()

    for item in sorted_ranked:
        if len(selected) >= top_n:
            break
        item_id = item.get("id", "").lower()
        matched = _find_experience(item_id, work_experience)
        if matched is not None:
            exp_key = id(matched)
            if exp_key not in seen_ids:
                seen_ids.add(exp_key)
                selected.append(matched)

    # If LLM ranking didn't cover all experiences or IDs didn't match,
    # fall back to taking the first top_n from master_resume order
    if not selected:
        logger.warning(
            "select_resume_content: LLM ranking produced no matched experiences; "
            "falling back to first %d from master resume",
            top_n,
        )
        selected = work_experience[:top_n]

    return selected


def _find_experience(item_id: str, work_experience: list[dict]) -> dict | None:
    """Find a work experience by matching both title and company in the id string."""
    for exp in work_experience:
        title = exp.get("title", "").lower()
        company = exp.get("company", "").lower()
        if title and company and title in item_id and company in item_id:
            return exp
    # Fallback: try matching just the title
    for exp in work_experience:
        title = exp.get("title", "").lower()
        if title and title in item_id:
            return exp
    return None


def _select_top_projects(
    ranked: list[dict],
    projects: list[dict],
    top_n: int,
) -> list[dict]:
    """Sort ranked projects by relevance_score descending, return top_n full dicts.

    The LLM uses the project's title as the id.
    """
    sorted_ranked = sorted(
        ranked, key=lambda x: x.get("relevance_score", 0), reverse=True
    )

    selected: list[dict] = []
    seen_titles: set[str] = set()

    for item in sorted_ranked:
        if len(selected) >= top_n:
            break
        item_id = item.get("id", "").lower()
        matched = _find_project(item_id, projects)
        if matched is not None:
            title_key = matched.get("title", "").lower()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                selected.append(matched)

    # Fallback: if matching failed, take first top_n from master resume
    if not selected:
        logger.warning(
            "select_resume_content: LLM ranking produced no matched projects; "
            "falling back to first %d from master resume",
            top_n,
        )
        selected = projects[:top_n]

    return selected


def _find_project(item_id: str, projects: list[dict]) -> dict | None:
    """Find a project by matching its title in the id string."""
    # Try exact substring match first
    for proj in projects:
        title = proj.get("title", "").lower()
        if title and title in item_id:
            return proj
    # Try partial match: check if most words from item_id appear in any title
    id_words = set(item_id.split())
    best_match: dict | None = None
    best_overlap = 0
    for proj in projects:
        title = proj.get("title", "").lower()
        title_words = set(title.split())
        overlap = len(id_words & title_words)
        if overlap > best_overlap:
            best_overlap = overlap
            best_match = proj
    return best_match if best_overlap >= 2 else None


def _filter_skills(master_resume: dict, jd_skills: list[str]) -> dict:
    """Filter master resume skills by JD keywords (case-insensitive substring match).

    If jd_skills is empty (Phase 4 sparse mode), returns all master skills.
    Returns a dict preserving category structure from master_resume.
    This is intentionally simple — validation in Plan 02 catches hallucinations.
    """
    technical_skills = master_resume.get("technical_skills", {})

    if not jd_skills:
        # Phase 4 mode: return all master skills, preserving category structure
        return technical_skills

    # Filter: keep skills that appear in the JD skills list (case-insensitive)
    jd_skills_lower = [s.lower() for s in jd_skills]
    filtered: dict = {}

    for category, skills_list in technical_skills.items():
        if not isinstance(skills_list, list):
            continue
        kept = [
            skill for skill in skills_list
            if any(jd_skill in skill.lower() or skill.lower() in jd_skill
                   for jd_skill in jd_skills_lower)
        ]
        if kept:
            filtered[category] = kept

    # If filter produced nothing (very restrictive JD), fall back to all skills
    if not filtered:
        logger.warning(
            "select_resume_content: skill filter produced empty result; "
            "returning all master skills as fallback"
        )
        return technical_skills

    return filtered


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
        "meta": {
            "templateName": "compact_2col_ats_resume",
            "version": "1.0.0",
            "engine": "pdflatex",
            "output": {
                "format": "latex",
                "targetPages": 1,
                "atsReadable": True,
            },
        },
        "style": {
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
        },
        "header": _build_header(master_resume),
        "sections": [
            _build_education_section(master_resume),
            _build_skills_section(selected_skills),
            _build_experience_section(selected_experiences),
            _build_projects_section(selected_projects),
            _build_extracurricular_section(master_resume),
        ],
    }


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
    category_labels = {
        "programming": "Programming & Scripting",
        "frameworks": "Frameworks & Libraries",
        "developer_tools": "Developer Tools",
        "libraries": "Libraries & AI/ML",
    }

    lines = []
    for category, skills_list in selected_skills.items():
        if isinstance(skills_list, list) and skills_list:
            label = category_labels.get(category, category.replace("_", " ").title())
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
