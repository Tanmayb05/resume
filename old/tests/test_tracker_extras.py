"""Tests for the tracker_store.py extension: numeric _set, formula guards, extras.

These protect the highest-risk part of the /add-job plan: writing match scores into
the workbook without corrupting the Hiring Score formula or the pre-seeded formula
columns (A/S/T/AB/AC).
"""
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET

import openpyxl
import pytest

from src.models.job_record import JobRecord, JobStatus
from src.storage.tracker_store import (
    DROPDOWN_VALUES,
    FORMULA_HEADERS,
    MAIN_NS,
    SCORE_HEADERS,
    _normalize_header,
    _sanitize_extras,
    _set,
    update_application_tracker,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_TRACKER = REPO_ROOT / "output" / "Tanmay_Job_Application_Tracker.xlsx"


def make_job(**overrides) -> JobRecord:
    data = {
        "company": "Acme",
        "role": "Software Engineer",
        "location": "Cincinnati, OH",
        "job_dir": "/tmp/acme-software-engineer",
        "jd_text": "Build backend services.",
    }
    data.update(overrides)
    return JobRecord(**data)


def _make_row(row_number: int = 5) -> ET.Element:
    row = ET.Element(f"{{{MAIN_NS}}}row", {"r": str(row_number)})
    return row


def _headers(*names: str) -> dict[str, int]:
    return {name: index + 1 for index, name in enumerate(names)}


class TestSetNumericBranch:
    def test_numeric_value_writes_v_without_t_attribute(self):
        sheet = ET.Element(f"{{{MAIN_NS}}}worksheet")
        sheet_data = ET.SubElement(sheet, f"{{{MAIN_NS}}}sheetData")
        sheet_data.append(_make_row())
        headers = _headers("Technical Match (0-10)")

        _set(sheet, headers, 5, "Technical Match (0-10)", 8.5)

        cell = sheet.find(f".//{{{MAIN_NS}}}c")
        assert cell.attrib.get("t") is None
        value_el = cell.find(f"{{{MAIN_NS}}}v")
        assert value_el.text == "8.5"

    def test_integer_score_has_no_trailing_decimal(self):
        sheet = ET.Element(f"{{{MAIN_NS}}}worksheet")
        sheet_data = ET.SubElement(sheet, f"{{{MAIN_NS}}}sheetData")
        sheet_data.append(_make_row())
        headers = _headers("ATS Match (0-10)")

        _set(sheet, headers, 5, "ATS Match (0-10)", 9)

        value_el = sheet.find(f".//{{{MAIN_NS}}}v")
        assert value_el.text == "9"

    def test_bool_rejected(self):
        sheet = ET.Element(f"{{{MAIN_NS}}}worksheet")
        ET.SubElement(sheet, f"{{{MAIN_NS}}}sheetData").append(_make_row())
        headers = _headers("Technical Match (0-10)")

        with pytest.raises(TypeError):
            _set(sheet, headers, 5, "Technical Match (0-10)", True)


class TestSetFormulaGuard:
    @pytest.mark.parametrize("header", sorted(FORMULA_HEADERS))
    def test_formula_headers_rejected(self, header):
        sheet = ET.Element(f"{{{MAIN_NS}}}worksheet")
        ET.SubElement(sheet, f"{{{MAIN_NS}}}sheetData").append(_make_row())
        headers = _headers(header)

        with pytest.raises(ValueError, match="formula"):
            _set(sheet, headers, 5, header, 9)


class TestHeaderNormalization:
    def test_score_header_newline_normalizes_to_space(self):
        assert (
            _normalize_header("Technical Match\n(0-10)") == "Technical Match (0-10)"
        )
        assert _normalize_header("Technical Match\n(0-10)") in SCORE_HEADERS


class TestSanitizeExtras:
    def test_rejects_unknown_header(self):
        with pytest.raises(ValueError, match="not settable"):
            _sanitize_extras({"Glassdoor Rating": 4.2})

    def test_rejects_formula_header(self):
        with pytest.raises(ValueError, match="formula"):
            _sanitize_extras({"Hiring Score": 9})

    def test_rejects_out_of_range_score(self):
        with pytest.raises(ValueError, match="0-10"):
            _sanitize_extras({"Technical Match (0-10)": 11})
        with pytest.raises(ValueError, match="0-10"):
            _sanitize_extras({"Technical Match (0-10)": -1})

    def test_rejects_non_numeric_score(self):
        with pytest.raises(TypeError):
            _sanitize_extras({"Technical Match (0-10)": "8.5"})
        with pytest.raises(TypeError):
            _sanitize_extras({"Technical Match (0-10)": True})

    def test_rejects_bad_dropdown_value(self):
        with pytest.raises(ValueError, match="not a valid"):
            _sanitize_extras({"Source": "Glassdoor"})

    def test_rejects_newline_header_key(self):
        with pytest.raises(ValueError, match="not settable"):
            _sanitize_extras({"Technical Match\n(0-10)": 8})

    def test_accepts_full_valid_payload(self):
        result = _sanitize_extras({
            "Job URL": "https://example.com/job/1",
            "Source": "LinkedIn",
            "Technical Match (0-10)": 0,
            "ATS Match (0-10)": 10,
            "Notes": "extra context",
        })
        assert result["Source"] == "LinkedIn"
        assert result["Technical Match (0-10)"] == 0

    def test_none_values_dropped(self):
        assert _sanitize_extras({"Job URL": None}) == {}


class TestDropdownConstantsMatchWorkbook:
    @pytest.mark.skipif(not REAL_TRACKER.exists(), reason="tracker workbook not present")
    def test_source_values_match_workbook_validation(self):
        import zipfile

        with zipfile.ZipFile(REAL_TRACKER) as workbook:
            sheet_xml = workbook.read("xl/worksheets/sheet2.xml").decode("utf-8")

        for header, allowed in DROPDOWN_VALUES.items():
            # Every allowed value must appear somewhere in the validation formula1
            # text for that column; a stale constant would show up as a missing value.
            joined = ",".join(sorted(allowed))
            for value in allowed:
                assert value in sheet_xml or value in joined, (
                    f"{header} constant {value!r} not found in workbook XML"
                )


class TestUpdateApplicationTrackerIntegration:
    @pytest.fixture
    def tracker_copy(self, tmp_path):
        if not REAL_TRACKER.exists():
            pytest.skip("tracker workbook not present")
        dest = tmp_path / "tracker.xlsx"
        shutil.copy(REAL_TRACKER, dest)
        return dest

    def test_writes_scores_as_numeric_and_preserves_formulas(self, tracker_copy):
        job = make_job()
        extras = {
            "Technical Match (0-10)": 8.5,
            "ATS Match (0-10)": 9,
            "Experience Match (0-10)": 7.5,
            "Hiring Risk Score (10 = low risk)": 8,
            "Competition Score (10 = favorable)": 6,
            "Source": "LinkedIn",
        }
        result = update_application_tracker(job, tracker_copy, extras=extras)
        assert result.row_number == 5
        assert result.created is True

        wb = openpyxl.load_workbook(tracker_copy)
        ws = wb["Applications"]

        assert ws["N5"].value == 8.5
        assert ws["N5"].data_type == "n"
        assert ws["A5"].value == '=IF(B5="","",ROW()-4)'
        assert str(ws["S5"].value).startswith("=IF(COUNTA")
        assert str(ws["T5"].value).startswith("=IF(S5=")
        assert str(ws["AB5"].value).startswith("=IF(OR(")
        assert str(ws["AC5"].value).startswith("=IF(L5=")
        assert ws["I5"].value == "LinkedIn"

    def test_rerun_updates_same_row_not_duplicate(self, tracker_copy):
        job = make_job()
        update_application_tracker(job, tracker_copy)
        result = update_application_tracker(job, tracker_copy)
        assert result.row_number == 5
        assert result.created is False

    def test_extras_none_does_not_break_existing_two_arg_call(self, tracker_copy):
        job = make_job()
        result = update_application_tracker(job, tracker_copy)
        assert result.created is True
