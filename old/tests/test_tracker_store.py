"""Tests for tracker workbook mapping helpers.

These tests avoid opening a real .xlsx file; they verify the deterministic
JobRecord -> tracker dropdown/value mapping used by update_application_tracker().
"""
from src.models.job_record import JobRecord, JobStatus
from src.storage.tracker_store import (
    _cover_letter_status,
    _employment_type,
    _next_action,
    _tracker_status,
    _visa_status,
    _work_arrangement,
)


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


class TestTrackerMappings:
    def test_status_ready_when_artifacts_exist(self):
        job = make_job(resume_pdf_path="/tmp/resume.pdf")
        assert _tracker_status(job) == "Ready to Apply"

    def test_status_applied_maps_to_applied(self):
        job = make_job(status=JobStatus.APPLIED)
        assert _tracker_status(job) == "Applied"

    def test_status_default_researching(self):
        assert _tracker_status(make_job()) == "Researching"

    def test_visa_status_values_match_dropdown(self):
        assert _visa_status(make_job(f1_sponsorship_available=True)) == "Sponsorship Likely"
        assert _visa_status(make_job(f1_sponsorship_available=False)) == "No Sponsorship"
        assert _visa_status(make_job(f1_sponsorship_available=None)) == "Unknown"

    def test_employment_type_internship_from_role(self):
        job = make_job(role="Software Engineer Intern")
        assert _employment_type(job) == "Internship"

    def test_employment_type_contract(self):
        job = make_job(employment_type="contract")
        assert _employment_type(job) == "Contract"

    def test_work_arrangement_remote(self):
        job = make_job(location="Remote, United States")
        assert _work_arrangement(job) == "Remote"

    def test_cover_letter_status(self):
        assert _cover_letter_status(make_job()) == "No"
        assert _cover_letter_status(make_job(cover_letter_path="/tmp/cover.txt")) == "Yes"

    def test_next_action_with_both_artifacts(self):
        job = make_job(
            resume_pdf_path="/tmp/resume.pdf",
            cover_letter_path="/tmp/cover.txt",
        )
        assert _next_action(job) == "Apply with tailored resume and cover letter"
