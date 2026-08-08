"""Excel-backed application tracker updates.

The workbook is treated as a reporting artifact, not the source of truth.
JobRecord remains the canonical persisted record under data/<job>/job.json.
"""
from __future__ import annotations

import os
import re
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Optional
from xml.etree import ElementTree as ET

from src.models.job_record import JobRecord, JobStatus


APPLICATIONS_SHEET = "Applications"
HEADER_ROW = 4
FIRST_DATA_ROW = 5

# Columns computed by workbook formulas. Writing a value into any of these
# destroys the formula, so _set refuses them outright.
FORMULA_HEADERS = frozenset({
    "App ID",
    "Hiring Score",
    "Suggested Priority",
    "Follow-up Status",
    "Days Since Applied",
})

# Score columns carry decimal 0-10 validation and feed the Hiring Score formula,
# so they must be written as numbers, never as inline strings.
# Header keys are post-_normalize_header: the workbook stores a literal newline
# before "(0-10)", which collapses to a single space.
SCORE_HEADERS = frozenset({
    "Technical Match (0-10)",
    "ATS Match (0-10)",
    "Experience Match (0-10)",
    "Hiring Risk Score (10 = low risk)",
    "Competition Score (10 = favorable)",
})

# Dropdown allowed values, mirroring the sheet's dataValidation lists exactly.
# An off-list value makes Excel flag the cell when the workbook is opened.
DROPDOWN_VALUES = {
    "Work Arrangement": frozenset({
        "Remote", "Hybrid", "On-site", "Flexible", "Unknown",
    }),
    "Employment Type": frozenset({
        "Full-time", "Internship", "Contract", "Part-time", "Temporary",
    }),
    "Source": frozenset({
        "Company Careers", "LinkedIn", "Referral", "Recruiter",
        "Handshake", "Indeed", "Other",
    }),
    "Status": frozenset({
        "Researching", "Ready to Apply", "Applied", "Recruiter Screen",
        "Assessment", "Technical Interview", "Onsite / Final", "Offer",
        "Rejected", "Withdrawn", "Closed",
    }),
    "User Priority": frozenset({"High", "Medium", "Low", "Skip"}),
    "Visa / Sponsorship": frozenset({
        "Sponsorship Confirmed", "Sponsorship Likely", "Unknown",
        "No Sponsorship", "Not Needed",
    }),
    "Referral Status": frozenset({
        "Not Started", "Contacted", "Requested", "Referred",
        "Declined", "Not Applicable",
    }),
    "Resume Version": frozenset({
        "Cloud / Infrastructure", "Backend / Distributed Systems",
        "AI / ML Systems", "General SWE", "Custom",
    }),
    "Cover Letter": frozenset({"Yes", "No", "Not Needed"}),
}

# Headers an `extras` payload may set. Free-text and dropdown columns the caller
# legitimately knows better than the defaults, plus the five score columns.
EXTRAS_ALLOWED_HEADERS = frozenset({
    "Job ID",
    "Job URL",
    "Source",
    "Work Arrangement",
    "Employment Type",
    "Status",
    "Visa / Sponsorship",
    "Resume Version",
    "User Priority",
    "Notes",
}) | SCORE_HEADERS
MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

ET.register_namespace("", MAIN_NS)
ET.register_namespace("r", REL_NS)


@dataclass(frozen=True)
class TrackerUpdateResult:
    """Result from writing one job to the tracker workbook."""

    workbook_path: Path
    row_number: int
    created: bool


def update_application_tracker(
    job_record: JobRecord,
    tracker_path: Path,
    extras: Optional[dict] = None,
) -> TrackerUpdateResult:
    """Create or update a job row in the Excel application tracker.

    Matching uses company, role, and location so rerunning the pipeline for the
    same JD updates the existing tracker row instead of creating duplicates.
    Formula-driven columns are intentionally left untouched.

    Args:
        job_record: The job to write.
        tracker_path: Path to the .xlsx workbook (must already exist).
        extras: Optional {header: value} overrides applied after the derived
            defaults, so a caller with better information (match scores, the
            real source, a job URL) wins. Validated by _sanitize_extras.
    """
    tracker_path = Path(tracker_path).resolve()
    sanitized_extras = _sanitize_extras(extras or {})
    if not tracker_path.exists():
        raise FileNotFoundError(f"Tracker workbook not found: {tracker_path}")

    with zipfile.ZipFile(tracker_path, "r") as workbook:
        sheet_path = _applications_sheet_path(workbook)
        shared_strings = _load_shared_strings(workbook)
        sheet_root = ET.fromstring(workbook.read(sheet_path))

        headers = _header_map(sheet_root, shared_strings)
        row_number, created = _find_or_allocate_row(
            sheet_root,
            headers,
            shared_strings,
            job_record,
        )

        _set(sheet_root, headers, row_number, "Company", job_record.company)
        _set(sheet_root, headers, row_number, "Job Title", job_record.role)
        _set(sheet_root, headers, row_number, "Location", job_record.location)
        _set(sheet_root, headers, row_number, "Work Arrangement", _work_arrangement(job_record))
        _set(sheet_root, headers, row_number, "Employment Type", _employment_type(job_record))
        _set(sheet_root, headers, row_number, "Source", "Other")
        _set(sheet_root, headers, row_number, "Date Posted", job_record.date_posted)
        _set(sheet_root, headers, row_number, "Date Found", date.today())
        _set(sheet_root, headers, row_number, "Status", _tracker_status(job_record))
        _set(sheet_root, headers, row_number, "Visa / Sponsorship", _visa_status(job_record))
        _set(sheet_root, headers, row_number, "Referral Status", "Not Started")
        _set(sheet_root, headers, row_number, "Resume Version", _resume_version(job_record))
        _set(sheet_root, headers, row_number, "Cover Letter", _cover_letter_status(job_record))
        _set(sheet_root, headers, row_number, "Next Action", _next_action(job_record))
        _set(sheet_root, headers, row_number, "Notes", _notes(job_record))

        # Applied last so caller-supplied values override the derived defaults.
        for header, value in sanitized_extras.items():
            _set(sheet_root, headers, row_number, header, value)

        updated_sheet = ET.tostring(
            sheet_root,
            encoding="utf-8",
            xml_declaration=True,
        )
        updated_entries = [
            (
                item,
                updated_sheet
                if item.filename == sheet_path
                else workbook.read(item.filename),
            )
            for item in workbook.infolist()
        ]

    _write_updated_workbook(updated_entries, tracker_path)
    return TrackerUpdateResult(
        workbook_path=tracker_path,
        row_number=row_number,
        created=created,
    )


def _applications_sheet_path(workbook: zipfile.ZipFile) -> str:
    workbook_root = ET.fromstring(workbook.read("xl/workbook.xml"))
    rel_root = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    rels = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rel_root.findall(f"{{{PKG_REL_NS}}}Relationship")
    }

    for sheet in workbook_root.findall(f".//{{{MAIN_NS}}}sheet"):
        if sheet.attrib.get("name") != APPLICATIONS_SHEET:
            continue
        rel_id = sheet.attrib.get(f"{{{REL_NS}}}id")
        target = rels.get(rel_id or "")
        if not target:
            break
        if target.startswith("/"):
            return target.lstrip("/")
        if target.startswith("xl/"):
            return target
        return f"xl/{target}"

    raise ValueError(
        f"Tracker workbook is missing the {APPLICATIONS_SHEET!r} sheet"
    )


def _load_shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []

    root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root.findall(f"{{{MAIN_NS}}}si"):
        text = "".join(
            node.text or ""
            for node in item.findall(f".//{{{MAIN_NS}}}t")
        )
        strings.append(text)
    return strings


def _header_map(sheet_root: ET.Element, shared_strings: list[str]) -> dict[str, int]:
    headers: dict[str, int] = {}
    row = _get_row(sheet_root, HEADER_ROW)
    if row is None:
        raise ValueError("Tracker Applications sheet is missing the header row")

    for cell in row.findall(f"{{{MAIN_NS}}}c"):
        value = _normalize_header(_cell_value(cell, shared_strings))
        if value:
            headers[value] = _cell_col_index(cell)

    required = {"Company", "Job Title", "Location", "Status"}
    missing = sorted(required - set(headers))
    if missing:
        raise ValueError(f"Tracker Applications sheet missing columns: {missing}")
    return headers


def _find_or_allocate_row(
    sheet_root: ET.Element,
    headers: dict[str, int],
    shared_strings: list[str],
    job_record: JobRecord,
) -> tuple[int, bool]:
    company_col = headers["Company"]
    title_col = headers["Job Title"]
    location_col = headers["Location"]
    max_row = _max_row(sheet_root)

    normalized_target = (
        _normalize_value(job_record.company),
        _normalize_value(job_record.role),
        _normalize_value(job_record.location),
    )

    for row in range(FIRST_DATA_ROW, max_row + 1):
        row_element = _get_row(sheet_root, row)
        normalized_row = (
            _normalize_value(_cell_at(row_element, company_col, shared_strings)),
            _normalize_value(_cell_at(row_element, title_col, shared_strings)),
            _normalize_value(_cell_at(row_element, location_col, shared_strings)),
        )
        if normalized_row == normalized_target:
            return row, False

    for row in range(FIRST_DATA_ROW, max_row + 1):
        row_element = _get_row(sheet_root, row)
        company = _cell_at(row_element, company_col, shared_strings)
        title = _cell_at(row_element, title_col, shared_strings)
        if _is_blank(company) and _is_blank(title):
            return row, True

    _ensure_row(sheet_root, max_row + 1)
    return max_row + 1, True


def _sanitize_extras(extras: dict) -> dict:
    """Validate caller-supplied tracker overrides before they reach the sheet.

    Enforces three things: the header is one we permit, score values are numbers
    in 0-10, and dropdown values are on the workbook's validation list.

    Raises:
        ValueError: unknown header, out-of-range score, or off-list dropdown value.
        TypeError: a score that is not numeric.
    """
    sanitized: dict[str, Any] = {}

    for header, value in extras.items():
        if value is None:
            continue

        if header in FORMULA_HEADERS:
            raise ValueError(
                f"{header!r} is computed by a workbook formula and cannot be set"
            )
        if header not in EXTRAS_ALLOWED_HEADERS:
            raise ValueError(
                f"Header {header!r} is not settable via extras. "
                f"Allowed: {sorted(EXTRAS_ALLOWED_HEADERS)}"
            )

        if header in SCORE_HEADERS:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(
                    f"{header!r} must be a number in 0-10, got {value!r}"
                )
            if not 0 <= value <= 10:
                raise ValueError(
                    f"{header!r} must be within 0-10, got {value!r}"
                )
            sanitized[header] = value
            continue

        allowed = DROPDOWN_VALUES.get(header)
        if allowed is not None and value not in allowed:
            raise ValueError(
                f"{value!r} is not a valid {header!r} value. "
                f"Allowed: {sorted(allowed)}"
            )

        sanitized[header] = value

    return sanitized


def _set(
    sheet_root: ET.Element,
    headers: dict[str, int],
    row: int,
    header: str,
    value: Optional[Any],
) -> None:
    if header in FORMULA_HEADERS:
        raise ValueError(
            f"Refusing to write {header!r}: it holds a workbook formula"
        )
    if value is None or header not in headers:
        return
    row_element = _ensure_row(sheet_root, row)
    cell = _ensure_cell(row_element, headers[header])
    _clear_cell_contents(cell)

    if isinstance(value, date):
        cell.attrib.pop("t", None)
        ET.SubElement(cell, f"{{{MAIN_NS}}}v").text = str(_excel_date_serial(value))
        return

    # bool is an int subclass, so it must be rejected before the numeric branch
    # or True would silently land in a score column as the number 1.
    if isinstance(value, bool):
        raise TypeError(f"Refusing to write bool {value!r} to {header!r}")

    if isinstance(value, (int, float)):
        # Numeric cells carry no t attribute; a t="inlineStr" score would make
        # the Hiring Score formula evaluate to #VALUE!.
        cell.attrib.pop("t", None)
        ET.SubElement(cell, f"{{{MAIN_NS}}}v").text = _format_number(value)
        return

    cell.attrib["t"] = "inlineStr"
    inline_string = ET.SubElement(cell, f"{{{MAIN_NS}}}is")
    text = ET.SubElement(inline_string, f"{{{MAIN_NS}}}t")
    text.text = str(value)


def _format_number(value: float) -> str:
    """Render a number for a spreadsheet cell without a trailing '.0'."""
    if isinstance(value, int):
        return str(value)
    if value == int(value):
        return str(int(value))
    return repr(float(value))


def _write_updated_workbook(
    entries: list[tuple[zipfile.ZipInfo, bytes]],
    tracker_path: Path,
) -> None:
    temp_fd, temp_name = tempfile.mkstemp(
        dir=tracker_path.parent,
        suffix=".xlsx",
    )
    os.close(temp_fd)

    try:
        with zipfile.ZipFile(temp_name, "w") as output:
            for item, data in entries:
                output.writestr(item, data)
        os.replace(temp_name, tracker_path)
    except Exception:
        try:
            os.unlink(temp_name)
        finally:
            raise


def _get_row(sheet_root: ET.Element, row_number: int) -> Optional[ET.Element]:
    sheet_data = sheet_root.find(f"{{{MAIN_NS}}}sheetData")
    if sheet_data is None:
        return None

    for row in sheet_data.findall(f"{{{MAIN_NS}}}row"):
        if int(row.attrib.get("r", "0")) == row_number:
            return row
    return None


def _ensure_row(sheet_root: ET.Element, row_number: int) -> ET.Element:
    row = _get_row(sheet_root, row_number)
    if row is not None:
        return row

    sheet_data = sheet_root.find(f"{{{MAIN_NS}}}sheetData")
    if sheet_data is None:
        sheet_data = ET.SubElement(sheet_root, f"{{{MAIN_NS}}}sheetData")

    row = ET.Element(f"{{{MAIN_NS}}}row", {"r": str(row_number)})
    inserted = False
    for index, existing in enumerate(list(sheet_data)):
        if int(existing.attrib.get("r", "0")) > row_number:
            sheet_data.insert(index, row)
            inserted = True
            break
    if not inserted:
        sheet_data.append(row)
    return row


def _ensure_cell(row: ET.Element, col_index: int) -> ET.Element:
    cell_ref = f"{_col_letter(col_index)}{row.attrib['r']}"
    for cell in row.findall(f"{{{MAIN_NS}}}c"):
        if cell.attrib.get("r") == cell_ref:
            return cell

    cell = ET.Element(f"{{{MAIN_NS}}}c", {"r": cell_ref})
    inserted = False
    for index, existing in enumerate(row.findall(f"{{{MAIN_NS}}}c")):
        if _cell_col_index(existing) > col_index:
            row.insert(index, cell)
            inserted = True
            break
    if not inserted:
        row.append(cell)
    return cell


def _cell_at(
    row: Optional[ET.Element],
    col_index: int,
    shared_strings: list[str],
) -> Optional[str]:
    if row is None:
        return None

    for cell in row.findall(f"{{{MAIN_NS}}}c"):
        if _cell_col_index(cell) == col_index:
            return _cell_value(cell, shared_strings)
    return None


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> Optional[str]:
    cell_type = cell.attrib.get("t")

    if cell_type == "inlineStr":
        return "".join(
            node.text or ""
            for node in cell.findall(f".//{{{MAIN_NS}}}t")
        )

    value = cell.find(f"{{{MAIN_NS}}}v")
    if value is None or value.text is None:
        return None

    if cell_type == "s":
        index = int(value.text)
        if index < len(shared_strings):
            return shared_strings[index]
        return None

    return value.text


def _clear_cell_contents(cell: ET.Element) -> None:
    for child in list(cell):
        if child.tag in {
            f"{{{MAIN_NS}}}f",
            f"{{{MAIN_NS}}}v",
            f"{{{MAIN_NS}}}is",
        }:
            cell.remove(child)


def _max_row(sheet_root: ET.Element) -> int:
    sheet_data = sheet_root.find(f"{{{MAIN_NS}}}sheetData")
    if sheet_data is None:
        return 0
    rows = [
        int(row.attrib.get("r", "0"))
        for row in sheet_data.findall(f"{{{MAIN_NS}}}row")
    ]
    return max(rows, default=0)


def _cell_col_index(cell: ET.Element) -> int:
    ref = cell.attrib.get("r", "")
    letters = re.match(r"[A-Z]+", ref)
    if not letters:
        raise ValueError(f"Cell is missing a valid reference: {ref!r}")

    col = 0
    for char in letters.group(0):
        col = col * 26 + ord(char) - ord("A") + 1
    return col


def _col_letter(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def _excel_date_serial(value: date) -> int:
    return (value - date(1899, 12, 30)).days


def _normalize_header(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\n", " ").split())


def _normalize_value(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def _work_arrangement(job_record: JobRecord) -> str:
    text = f"{job_record.location} {job_record.jd_text or ''}".lower()
    if "remote" in text:
        return "Remote"
    if "hybrid" in text:
        return "Hybrid"
    if "on-site" in text or "onsite" in text:
        return "On-site"
    return "Unknown"


def _employment_type(job_record: JobRecord) -> str:
    text = f"{job_record.employment_type or ''} {job_record.role}".lower()
    if "intern" in text:
        return "Internship"
    if "contract" in text:
        return "Contract"
    if "part" in text:
        return "Part-time"
    if "temporary" in text or "temp" in text:
        return "Temporary"
    return "Full-time"


def _tracker_status(job_record: JobRecord) -> str:
    if job_record.status == JobStatus.APPLIED:
        return "Applied"
    if (
        job_record.status == JobStatus.READY
        or job_record.resume_pdf_path
        or job_record.cover_letter_path
    ):
        return "Ready to Apply"
    return "Researching"


def _visa_status(job_record: JobRecord) -> str:
    if job_record.f1_sponsorship_available is True:
        return "Sponsorship Likely"
    if job_record.f1_sponsorship_available is False:
        return "No Sponsorship"
    return "Unknown"


def _resume_version(job_record: JobRecord) -> Optional[str]:
    if job_record.resume_pdf_path:
        return "Custom"
    return None


def _cover_letter_status(job_record: JobRecord) -> str:
    return "Yes" if job_record.cover_letter_path else "No"


def _next_action(job_record: JobRecord) -> str:
    if job_record.resume_pdf_path and job_record.cover_letter_path:
        return "Apply with tailored resume and cover letter"
    if job_record.resume_pdf_path:
        return "Generate cover letter"
    return "Tailor resume"


def _notes(job_record: JobRecord) -> str:
    parts = [f"Job artifacts: {job_record.job_dir}"]
    if job_record.resume_pdf_path:
        parts.append(f"Resume PDF: {job_record.resume_pdf_path}")
    if job_record.cover_letter_path:
        parts.append(f"Cover letter: {job_record.cover_letter_path}")
    if job_record.visa_keywords:
        parts.append(f"Visa keywords: {', '.join(job_record.visa_keywords)}")
    return "\n".join(parts)
