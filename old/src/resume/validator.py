"""Entity validation module — structured field diff against master_resume.

validate_content() checks a selected_content dict (resume_json_template.json
structure) against the master_resume source-of-truth via structured field diff.

Key design decisions (per CONTEXT.md locked decisions):
  - No NER, no regex entity extraction — pure Python dict comparison
  - No PDF text extraction — compares selected_content dict directly
  - Warn-and-return policy — NEVER raises exceptions; validation failure is a
    warning flag, not a crash (job-hunt tool where partial output > no output)
  - Violations produce validation_warning=True; the result.success is always True
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Result returned by validate_content().

    Attributes:
        success:            Always True (validation never crashes the pipeline).
        validation_warning: True if any violations were found.
        violations:         List of human-readable violation descriptions.
    """

    success: bool
    validation_warning: bool = False
    violations: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_skill(skill: str) -> str:
    """Normalize a skill string for comparison.

    Strips trailing version numbers (e.g., "Python 3.10" -> "python") and
    converts to lowercase.

    Args:
        skill: Raw skill string.

    Returns:
        Normalized lowercase skill string.
    """
    # Strip trailing version numbers: "Python 3.10", "Node.js 18", "Go 1.21"
    normalized = re.sub(r"\s+\d[\d.]*$", "", skill.strip()).lower()
    return normalized


def _extract_selected_skills(selected_content: dict) -> list:
    """Extract all skill items from selected_content technical_skills section.

    Args:
        selected_content: Resume dict (resume_json_template.json structure).

    Returns:
        List of skill strings from all lines in the technical_skills section.
    """
    skills = []
    for section in selected_content.get("sections", []):
        if section.get("type") == "technical_skills":
            for line in section.get("lines", []):
                skills.extend(line.get("items", []))
    return skills


def _extract_master_skills(master_resume: dict) -> dict:
    """Flatten all master_resume technical_skills into a lowercase -> original mapping.

    Args:
        master_resume: Full master resume dict.

    Returns:
        Dict of {lowercase_skill: original_skill}.
    """
    master_skills_lower = {}
    technical_skills = master_resume.get("technical_skills", {})
    if isinstance(technical_skills, dict):
        for category_items in technical_skills.values():
            if isinstance(category_items, list):
                for skill in category_items:
                    if isinstance(skill, str):
                        master_skills_lower[skill.lower()] = skill
    elif isinstance(technical_skills, list):
        # Some master_resume formats may use a flat list
        for skill in technical_skills:
            if isinstance(skill, str):
                master_skills_lower[skill.lower()] = skill
    return master_skills_lower


def _skill_in_master(skill: str, master_skills_lower: dict) -> bool:
    """Check if a skill (possibly with version) is present in master skills.

    Matching strategy:
    1. Try exact lowercase match
    2. Try normalized form (version stripped) as exact match
    3. Try normalized form as substring of any master skill key
    4. Try any master skill key as substring of normalized form

    Args:
        skill: Skill string from selected_content.
        master_skills_lower: Dict of {lowercase_master_skill: original}.

    Returns:
        True if the skill can be matched to any master skill.
    """
    skill_lower = skill.lower()
    normalized = _normalize_skill(skill)

    # 1. Exact lowercase match
    if skill_lower in master_skills_lower:
        return True

    # 2. Exact normalized match
    if normalized in master_skills_lower:
        return True

    # 3. Normalized form is substring of any master skill
    for master_lower in master_skills_lower:
        if normalized in master_lower:
            return True
        # 4. Any master skill is substring of normalized form
        if master_lower in normalized:
            return True

    return False


def _extract_selected_companies(selected_content: dict) -> set:
    """Extract company names from selected_content work_experience sections.

    Args:
        selected_content: Resume dict.

    Returns:
        Set of company name strings.
    """
    companies = set()
    for section in selected_content.get("sections", []):
        if section.get("type") == "work_experience":
            for entry in section.get("entries", []):
                company = entry.get("company", "")
                if company:
                    companies.add(company)
    return companies


def _extract_master_companies(master_resume: dict) -> set:
    """Extract all company names from master_resume work_experience.

    Args:
        master_resume: Full master resume dict.

    Returns:
        Set of company name strings.
    """
    companies = set()
    for exp in master_resume.get("work_experience", []):
        company = exp.get("company", "")
        if company:
            companies.add(company)
    return companies


def _extract_selected_projects(selected_content: dict) -> set:
    """Extract project titles from selected_content projects_and_research sections.

    Args:
        selected_content: Resume dict.

    Returns:
        Set of project title strings.
    """
    titles = set()
    for section in selected_content.get("sections", []):
        if section.get("type") == "projects_and_research":
            for entry in section.get("entries", []):
                title = entry.get("title", "")
                if title:
                    titles.add(title)
    return titles


def _extract_master_projects(master_resume: dict) -> set:
    """Extract all project titles from master_resume.

    Checks both 'projects' and 'projects_and_research' keys.

    Args:
        master_resume: Full master resume dict.

    Returns:
        Set of project title strings.
    """
    titles = set()
    projects = master_resume.get("projects", master_resume.get("projects_and_research", []))
    for proj in projects:
        title = proj.get("title", "")
        if title:
            titles.add(title)
    return titles


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_content(selected_content: dict, master_resume: dict) -> ValidationResult:
    """Validate selected_content against master_resume via structured field diff.

    Checks three categories:
      1. Skills: each skill in selected_content must match a master_resume skill
         (case-insensitive, version-stripped substring match).
      2. Companies: each company in selected_content work_experience must match
         a master_resume company (case-insensitive exact match).
      3. Projects: each project title in selected_content must match a
         master_resume project title (case-insensitive exact match).

    Never raises an exception — any failure is captured as a violation string.
    Always returns ValidationResult(success=True). Violations produce
    validation_warning=True.

    Args:
        selected_content: Resume dict (resume_json_template.json compatible)
                          produced by select_resume_content().
        master_resume:    Full master resume dict loaded from master_resume.json.

    Returns:
        ValidationResult with success=True always, validation_warning=True and
        populated violations list if any mismatches were found.
    """
    violations: List[str] = []

    # --- 1. Validate skills ---
    try:
        selected_skills = _extract_selected_skills(selected_content)
        master_skills_lower = _extract_master_skills(master_resume)

        if selected_skills and master_skills_lower:
            for skill in selected_skills:
                if not _skill_in_master(skill, master_skills_lower):
                    violations.append(
                        f"Skill not found in master resume: '{skill}'"
                    )
        elif selected_skills and not master_skills_lower:
            logger.warning(
                "validate_content: master_resume has no technical_skills — skipping skill check"
            )
    except Exception as exc:
        logger.warning("validate_content: skill check failed (skipped): %s", exc)

    # --- 2. Validate companies ---
    try:
        selected_companies = _extract_selected_companies(selected_content)
        master_companies = _extract_master_companies(master_resume)

        if selected_companies and master_companies:
            master_companies_lower = {c.lower() for c in master_companies}
            for company in selected_companies:
                if company.lower() not in master_companies_lower:
                    violations.append(
                        f"Company not found in master resume: '{company}'"
                    )
        elif selected_companies and not master_companies:
            logger.warning(
                "validate_content: master_resume has no work_experience — skipping company check"
            )
    except Exception as exc:
        logger.warning("validate_content: company check failed (skipped): %s", exc)

    # --- 3. Validate projects ---
    try:
        selected_projects = _extract_selected_projects(selected_content)
        master_projects = _extract_master_projects(master_resume)

        if selected_projects and master_projects:
            master_projects_lower = {t.lower() for t in master_projects}
            for title in selected_projects:
                if title.lower() not in master_projects_lower:
                    violations.append(
                        f"Project not found in master resume: '{title}'"
                    )
        elif selected_projects and not master_projects:
            logger.warning(
                "validate_content: master_resume has no projects — skipping project check"
            )
    except Exception as exc:
        logger.warning("validate_content: project check failed (skipped): %s", exc)

    # --- 4. Aggregate and return ---
    if violations:
        logger.warning("validate_content: validation violations found: %s", violations)
        return ValidationResult(success=True, validation_warning=True, violations=violations)

    return ValidationResult(success=True, validation_warning=False)
