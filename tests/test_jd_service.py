"""Tests for detect_f1_sponsorship() in src/jd/service.py.

Covers:
- Positive indicators: H-1B/H1B/H1-B variants, OPT, will sponsor, visa sponsorship
- Negative indicators: no sponsorship, must be citizen, cannot sponsor
- Ambiguous / None: no sponsorship keywords, conflicting signals
- False-positive avoidance: optional, opt-in, opt-out must NOT trigger OPT match
"""
import pytest

from src.jd.service import detect_f1_sponsorship


class TestF1Detection:
    """Tests for detect_f1_sponsorship(jd_text: str) -> Optional[bool]."""

    # ------------------------------------------------------------------
    # Positive indicators — return True
    # ------------------------------------------------------------------

    def test_will_sponsor_h1b(self):
        """'will sponsor H-1B visas' -> True."""
        assert detect_f1_sponsorship("We will sponsor H-1B visas for qualified candidates") is True

    def test_h1b_no_hyphens_sponsorship(self):
        """'H1B sponsorship available' -> True."""
        assert detect_f1_sponsorship("H1B sponsorship available") is True

    def test_h1_dash_b_welcome(self):
        """'H1-B welcome' -> True."""
        assert detect_f1_sponsorship("H1-B welcome") is True

    def test_opt_eligible(self):
        """'OPT eligible candidates welcome' -> True."""
        assert detect_f1_sponsorship("OPT eligible candidates welcome") is True

    def test_work_authorization_supported(self):
        """'Work authorization supported' -> True."""
        assert detect_f1_sponsorship("Work authorization supported") is True

    def test_visa_sponsorship_provided(self):
        """'Visa sponsorship provided' -> True."""
        assert detect_f1_sponsorship("Visa sponsorship provided") is True

    def test_open_to_sponsoring(self):
        """'We are open to sponsoring work visas' -> True."""
        assert detect_f1_sponsorship("We are open to sponsoring work visas") is True

    def test_sponsorship_available(self):
        """'sponsorship available' -> True."""
        assert detect_f1_sponsorship("Sponsorship available for the right candidate") is True

    def test_sponsorship_offered(self):
        """'sponsorship offered' -> True."""
        assert detect_f1_sponsorship("Visa sponsorship offered to all candidates") is True

    def test_h1b_uppercase(self):
        """'H-1B' uppercase variant -> True."""
        assert detect_f1_sponsorship("H-1B sponsorship is available") is True

    # ------------------------------------------------------------------
    # Negative indicators — return False
    # ------------------------------------------------------------------

    def test_must_be_citizen_or_permanent_resident(self):
        """'Must be a US citizen or permanent resident only' -> False."""
        assert detect_f1_sponsorship("Must be a US citizen or permanent resident only") is False

    def test_no_visa_sponsorship(self):
        """'No visa sponsorship available' -> False."""
        assert detect_f1_sponsorship("No visa sponsorship available") is False

    def test_cannot_sponsor(self):
        """'Cannot sponsor work authorization' -> False."""
        assert detect_f1_sponsorship("Cannot sponsor work authorization") is False

    def test_do_not_sponsor_h1b(self):
        """'Do not sponsor H-1B' -> False."""
        assert detect_f1_sponsorship("Do not sponsor H-1B") is False

    def test_authorized_without_sponsorship(self):
        """'Authorized to work in the US without sponsorship' -> False."""
        assert detect_f1_sponsorship("Authorized to work in the US without sponsorship") is False

    def test_no_sponsorship_bare(self):
        """'No sponsorship' -> False."""
        assert detect_f1_sponsorship("No sponsorship for this position") is False

    def test_citizens_only(self):
        """'citizens only' -> False."""
        assert detect_f1_sponsorship("US citizens only need apply") is False

    # ------------------------------------------------------------------
    # Ambiguous / not mentioned — return None
    # ------------------------------------------------------------------

    def test_no_sponsorship_keywords(self):
        """Generic JD text with no sponsorship keywords -> None."""
        assert detect_f1_sponsorship("We are looking for a Python engineer") is None

    def test_optional_requirement_no_false_positive(self):
        """'optional requirement' must NOT trigger OPT match -> None."""
        assert detect_f1_sponsorship("optional requirement") is None

    def test_opt_in_no_false_positive(self):
        """'opt-in to our newsletter' must NOT trigger OPT match -> None."""
        assert detect_f1_sponsorship("opt-in to our newsletter") is None

    def test_optional_skills_no_false_positive(self):
        """'optional skills include Docker' must NOT trigger OPT match -> None."""
        assert detect_f1_sponsorship("optional skills include Docker") is None

    def test_opt_out_no_false_positive(self):
        """'opt-out of email' must NOT trigger OPT match -> None."""
        assert detect_f1_sponsorship("opt-out of email") is None

    def test_conflicting_signals_ambiguous(self):
        """Conflicting positive + negative signals -> None (ambiguous)."""
        assert detect_f1_sponsorship("We sponsor H-1B but must already be authorized") is None

    def test_empty_string(self):
        """Empty string -> None."""
        assert detect_f1_sponsorship("") is None

    def test_unrelated_tech_text(self):
        """Unrelated technical job description -> None."""
        assert detect_f1_sponsorship(
            "5+ years Python experience. Must know Docker, Kubernetes, AWS."
        ) is None

    # ------------------------------------------------------------------
    # H-1B variant normalization
    # ------------------------------------------------------------------

    def test_h1b_no_separators(self):
        """'H1B' (no hyphens/spaces) -> True."""
        assert detect_f1_sponsorship("H1B candidates are welcome to apply") is True

    def test_h_dash_1_dash_b_with_spaces(self):
        """'H 1 B' (spaces) variant -> True."""
        assert detect_f1_sponsorship("We support H 1 B visa applications") is True
