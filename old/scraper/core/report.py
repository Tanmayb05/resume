"""
Markdown report generator.

`show_match_score` adds a resume keyword-match % column, and a visa-note
column is shown automatically whenever any listed company is cap-exempt.
"""

import json
import re
from datetime import datetime
from pathlib import Path

MASTER_RESUME_PATH = Path(__file__).parent.parent.parent / "templates" / "master_resume.json"


def _load_resume_skills() -> set[str]:
    if not MASTER_RESUME_PATH.exists():
        return set()
    data = json.loads(MASTER_RESUME_PATH.read_text())
    skills: set[str] = set()
    for group in data.get("technical_skills", {}).values():
        for s in group:
            skills.add(s.lower())
    return skills


def _match_score(title: str, skills: set[str]) -> int:
    """Keyword-overlap score: % of resume skills mentioned in the job title."""
    if not skills:
        return 0
    text = title.lower()
    hits = sum(1 for s in skills if re.search(re.escape(s.lower()), text))
    return round(100 * hits / len(skills)) if hits else 0


def generate(
    by_company: dict,
    blocked: list[tuple[str, str]],
    errors: list[tuple[str, str]],
    days: int,
    companies: list,
    report_path: Path,
    show_match_score: bool = False,
) -> Path:
    has_cap_exempt = any(c.cap_exempt for c in companies)
    visa_notes = {c.name: c.visa_note for c in companies} if has_cap_exempt else {}
    skills = _load_resume_skills() if show_match_score else set()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_jobs = sum(len(jobs) for jobs in by_company.values())

    lines: list[str] = []
    lines.append("# Job Listings Report" if not has_cap_exempt else "# Cap-Exempt Job Listings Report")
    lines.append("")
    lines.append(f"**Generated:** {now}  ")
    lines.append(f"**Lookback:** {days} days  ")
    lines.append(f"**New jobs:** {total_jobs}")
    lines.append("")
    lines.append("**Filters:** US/Remote · Internship, New Grad, Mid-level · SWE / ML / AI / Backend / Frontend / DevOps roles")
    if has_cap_exempt:
        lines.append("**Scope:** Nonprofit research orgs, universities, FFRDCs, teaching hospitals, large nonprofits")
    lines.append("")

    if by_company:
        for company_name in sorted(by_company.keys()):
            jobs = by_company[company_name]
            lines.append(f"## {company_name} ({len(jobs)})")
            if has_cap_exempt:
                visa_note = visa_notes.get(company_name, "—")
                lines.append(f"*Visa note: {visa_note}*")
            lines.append("")
            if show_match_score:
                lines.append("| Role | Level | Location | Posted | Match % | Link |")
                lines.append("|------|-------|----------|--------|---------|------|")
            else:
                lines.append("| Role | Level | Location | Posted | Link |")
                lines.append("|------|-------|----------|--------|------|")
            for job in sorted(jobs, key=lambda j: j.get("posted", ""), reverse=True):
                title = job["title"]
                level = job.get("level", "—")
                location = job.get("location", "—")
                posted = job.get("posted", "—")
                url = job["url"]
                if show_match_score:
                    match = _match_score(title, skills)
                    lines.append(f"| {title} | {level} | {location} | {posted} | {match}% | [Apply]({url}) |")
                else:
                    lines.append(f"| {title} | {level} | {location} | {posted} | [Apply]({url}) |")
            lines.append("")
    else:
        lines.append("*No new jobs found this run.*")
        lines.append("")

    if errors:
        lines.append("## Errors")
        lines.append("")
        label = "orgs" if has_cap_exempt else "companies"
        lines.append(f"These {label} returned errors during this run:")
        lines.append("")
        header = "Organization" if has_cap_exempt else "Company"
        lines.append(f"| {header} | Error | Careers URL |")
        lines.append(f"|{'-' * len(header)}--|-------|-------------|")
        for name, err in errors:
            url = next((c.careers_url for c in companies if c.name == name), "")
            lines.append(f"| {name} | {err} | [{url}]({url}) |")
        lines.append("")

    if blocked:
        lines.append("## Manual Check Required")
        lines.append("")
        if has_cap_exempt:
            lines.append("These orgs have bot protection or no public ATS — check their careers pages directly:")
        else:
            lines.append("These companies have bot protection — check their careers pages directly:")
        lines.append("")
        if has_cap_exempt:
            lines.append("| Organization | Careers URL | Visa Note |")
            lines.append("|--------------|-------------|-----------|")
            for name, url in blocked:
                lines.append(f"| {name} | [{url}]({url}) | {visa_notes.get(name, '—')} |")
        else:
            lines.append("| Company | Careers URL |")
            lines.append("|---------|-------------|")
            for name, url in blocked:
                lines.append(f"| {name} | [{url}]({url}) |")
        lines.append("")

    suffix = "cap-exempt job-scraper" if has_cap_exempt else "job-scraper"
    lines.append(f"*Generated by {suffix} · {now}*")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines))
    return report_path
