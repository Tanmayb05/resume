"""Tests for pure helper functions in src/cover_letter/service.py.

Tests cover:
- _clean_cover_letter_output(): preamble strip, em-dash, [Job Source] replacement
- _resolve_graduation_date(): internship vs full-time date and application_type
- WORD_COUNT_MIN / WORD_COUNT_MAX constant values

No async tests or LLM mocking — these test deterministic synchronous helpers.
"""
import pytest

from src.cover_letter.service import (
    _clean_cover_letter_output,
    _resolve_graduation_date,
    WORD_COUNT_MIN,
    WORD_COUNT_MAX,
)


class TestCleanCoverLetterOutput:
    """Tests for _clean_cover_letter_output() — preamble strip, em-dash, placeholder."""

    def test_strips_preamble(self):
        """Text with 'Here is the cover letter:' preamble is stripped before 'Dear'."""
        text = "Here is the cover letter:\n\nDear Hiring,\nI am excited to apply."
        result = _clean_cover_letter_output(text)
        assert result.startswith("Dear Hiring,")
        assert "Here is the cover letter" not in result

    def test_strips_em_dash_unicode(self):
        """U+2014 em-dash is replaced with a comma."""
        text = "Dear Hiring,\nI am excited\u2014very excited to join."
        result = _clean_cover_letter_output(text)
        assert "\u2014" not in result
        assert "excited,very" in result

    def test_strips_double_hyphen(self):
        """Double-hyphen (--) with surrounding whitespace is replaced with comma."""
        text = "Dear Hiring,\nRole -- responsibilities align with my background."
        result = _clean_cover_letter_output(text)
        assert " -- " not in result
        assert "--" not in result
        assert "Role, responsibilities" in result

    def test_replaces_job_source_placeholder(self):
        """[Job Source] placeholder is replaced with 'your website'."""
        text = "Dear Hiring,\nI saw the job on [Job Source] and was excited."
        result = _clean_cover_letter_output(text)
        assert "[Job Source]" not in result
        assert "your website" in result

    def test_no_preamble_passthrough(self):
        """Text that already starts with 'Dear' is returned unchanged (modulo strip)."""
        text = "Dear Hiring Committee,\nI am applying for the role."
        result = _clean_cover_letter_output(text)
        assert result.startswith("Dear Hiring Committee,")
        assert "I am applying for the role." in result

    def test_strips_preamble_case_insensitive(self):
        """Preamble strip is case-insensitive — 'dear' (lowercase) is found."""
        text = "Certainly! dear hiring manager,\nI am thrilled to apply."
        result = _clean_cover_letter_output(text)
        # Should strip everything before 'dear' (case-insensitive match)
        assert result.lower().startswith("dear")

    def test_strips_multiple_issues(self):
        """Preamble + em-dash + [Job Source] all fixed in one call."""
        text = (
            "Here is your letter:\n\n"
            "Dear Team,\nI found this role on [Job Source]\u2014exciting opportunity!"
        )
        result = _clean_cover_letter_output(text)
        assert result.startswith("Dear Team,")
        assert "[Job Source]" not in result
        assert "\u2014" not in result
        assert "your website" in result

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace is removed from result."""
        text = "   Dear Hiring,\n\nThank you.   "
        result = _clean_cover_letter_output(text)
        assert result == result.strip()


class TestResolveGraduationDate:
    """Tests for _resolve_graduation_date() — internship vs full-time detection."""

    def test_internship_employment_type(self):
        """'internship' maps to Dec 2026 and application_type='internship'."""
        result = _resolve_graduation_date("internship")
        assert result == ("Dec 2026", "internship")

    def test_intern_substring(self):
        """'Software Intern' contains 'intern' and maps to Dec 2026."""
        result = _resolve_graduation_date("Software Intern")
        assert result == ("Dec 2026", "internship")

    def test_intern_case_insensitive(self):
        """'INTERNSHIP' (uppercase) maps to Dec 2026 via case-insensitive match."""
        result = _resolve_graduation_date("INTERNSHIP")
        assert result == ("Dec 2026", "internship")

    def test_full_time(self):
        """'full-time' maps to May 2026 and application_type='full-time'."""
        result = _resolve_graduation_date("full-time")
        assert result == ("May 2026", "full-time")

    def test_none_employment_type(self):
        """None maps to May 2026 (default) and application_type='full-time'."""
        result = _resolve_graduation_date(None)
        assert result == ("May 2026", "full-time")

    def test_empty_employment_type(self):
        """Empty string maps to May 2026 (default) and application_type='full-time'."""
        result = _resolve_graduation_date("")
        assert result == ("May 2026", "full-time")

    def test_contract(self):
        """'contract' (no 'intern' substring) maps to May 2026 full-time."""
        result = _resolve_graduation_date("contract")
        assert result == ("May 2026", "full-time")

    def test_part_time(self):
        """'part-time' (no 'intern' substring) maps to May 2026 full-time."""
        result = _resolve_graduation_date("part-time")
        assert result == ("May 2026", "full-time")


class TestWordCountBoundary:
    """Tests for WORD_COUNT_MIN and WORD_COUNT_MAX constant values."""

    def test_word_count_min_value(self):
        """WORD_COUNT_MIN must be exactly 300."""
        assert WORD_COUNT_MIN == 300

    def test_word_count_max_value(self):
        """WORD_COUNT_MAX must be exactly 400."""
        assert WORD_COUNT_MAX == 400

    def test_min_boundary_passes(self):
        """A 300-word text is within the allowed range [WORD_COUNT_MIN, WORD_COUNT_MAX]."""
        text = " ".join(["word"] * 300)
        word_count = len(text.split())
        assert WORD_COUNT_MIN <= word_count <= WORD_COUNT_MAX

    def test_max_boundary_passes(self):
        """A 400-word text is within the allowed range [WORD_COUNT_MIN, WORD_COUNT_MAX]."""
        text = " ".join(["word"] * 400)
        word_count = len(text.split())
        assert WORD_COUNT_MIN <= word_count <= WORD_COUNT_MAX

    def test_below_min_fails(self):
        """A 299-word text is below WORD_COUNT_MIN."""
        text = " ".join(["word"] * 299)
        word_count = len(text.split())
        assert word_count < WORD_COUNT_MIN

    def test_above_max_fails(self):
        """A 401-word text is above WORD_COUNT_MAX."""
        text = " ".join(["word"] * 401)
        word_count = len(text.split())
        assert word_count > WORD_COUNT_MAX
