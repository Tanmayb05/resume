"""Tests for src/cover_letter/docx_writer.py and the mechanical checks in
scripts/add_job.py that gate cover-letter text before rendering.

split_paragraphs() is shared by the docx and pdf renderers — the test on it is what
guarantees the two outputs cannot silently diverge.
"""
import sys
from pathlib import Path

import pytest
from docx import Document

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.cover_letter.docx_writer import split_paragraphs, write_cover_letter_docx
from scripts.add_job import (
    PLACEHOLDER_TOKENS,
    REQUIRED_SALUTATION,
    WORD_COUNT_MAX,
    WORD_COUNT_MIN,
    WRONG_GRADUATION,
    StepError,
    _check_cover_letter_text,
)

SIGNATURE_BLOCK = (
    "Regards,\n"
    "Tanmay Bhuskute,\n"
    "bhuskutv@mail.uc.edu | tanmay.v.bhuskute@gmail.com | +1 (732) 858-3027,\n"
    "259 Hosea Ave, Apt D, Cincinnati, OH 45220"
)


def make_letter(word_count: int = 250) -> str:
    filler = " ".join(["word"] * (word_count - 40))
    return (
        f"{REQUIRED_SALUTATION}\n\n"
        "I saw the job post on LinkedIn and thought I'd be a good fit for it. "
        f"{filler}\n\n"
        "Here are reasons that make me a great fit for the role:\n\n"
        "1. Reason one with a metric.\n\n"
        f"{SIGNATURE_BLOCK}"
    )


class TestSplitParagraphs:
    def test_splits_on_blank_lines(self):
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        assert split_paragraphs(text) == [
            "Paragraph one.",
            "Paragraph two.",
            "Paragraph three.",
        ]

    def test_preserves_single_newlines_within_a_paragraph(self):
        text = "Line one\nLine two\n\nNext paragraph."
        result = split_paragraphs(text)
        assert result[0] == "Line one\nLine two"
        assert result[1] == "Next paragraph."

    def test_strips_leading_trailing_whitespace(self):
        text = "\n\n  Paragraph.  \n\n"
        assert split_paragraphs(text) == ["Paragraph."]

    def test_signature_block_survives_as_one_paragraph(self):
        result = split_paragraphs(SIGNATURE_BLOCK)
        assert len(result) == 1
        assert "Tanmay Bhuskute" in result[0]
        assert "259 Hosea Ave" in result[0]


class TestWriteCoverLetterDocx:
    def test_paragraph_count_matches_source(self, tmp_path):
        text = make_letter()
        out = write_cover_letter_docx(text, tmp_path / "cover_letter.docx")
        doc = Document(str(out))
        assert len([p for p in doc.paragraphs if p.text.strip()]) == len(
            split_paragraphs(text)
        )

    def test_signature_lines_preserved_as_line_breaks(self, tmp_path):
        out = write_cover_letter_docx(SIGNATURE_BLOCK, tmp_path / "sig.docx")
        doc = Document(str(out))
        full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        assert "Tanmay Bhuskute" in full_text
        assert "bhuskutv@mail.uc.edu" in full_text
        assert "259 Hosea Ave, Apt D, Cincinnati, OH 45220" in full_text

    def test_empty_text_raises(self, tmp_path):
        with pytest.raises(ValueError, match="zero paragraphs"):
            write_cover_letter_docx("   \n\n  ", tmp_path / "empty.docx")


class TestCheckCoverLetterText:
    def test_valid_letter_passes(self):
        _check_cover_letter_text(make_letter(250), 250)

    def test_missing_salutation_rejected(self):
        text = make_letter(250).replace(REQUIRED_SALUTATION, "Hello,")
        with pytest.raises(StepError, match="salutation"):
            _check_cover_letter_text(text, len(text.split()))

    @pytest.mark.parametrize("word_count", [WORD_COUNT_MIN - 1, WORD_COUNT_MAX + 1])
    def test_word_count_out_of_bounds_rejected(self, word_count):
        with pytest.raises(StepError, match="Word count"):
            _check_cover_letter_text(make_letter(word_count), word_count)

    @pytest.mark.parametrize("word_count", [WORD_COUNT_MIN, WORD_COUNT_MAX])
    def test_word_count_at_boundary_accepted(self, word_count):
        _check_cover_letter_text(make_letter(word_count), word_count)

    def test_em_dash_rejected(self):
        text = make_letter(250).replace("great fit", "great—fit")
        with pytest.raises(StepError, match="dash"):
            _check_cover_letter_text(text, len(text.split()))

    def test_en_dash_rejected(self):
        text = make_letter(250).replace("great fit", "great–fit")
        with pytest.raises(StepError, match="dash"):
            _check_cover_letter_text(text, len(text.split()))

    @pytest.mark.parametrize("token", PLACEHOLDER_TOKENS)
    def test_leftover_placeholder_rejected(self, token):
        text = make_letter(250) + f"\n\n{token}"
        with pytest.raises(StepError, match="[Pp]laceholder"):
            _check_cover_letter_text(text, len(text.split()))

    def test_wrong_graduation_date_rejected(self):
        text = make_letter(250) + f"\n\navailable after {WRONG_GRADUATION}"
        with pytest.raises(StepError, match="May 2026"):
            _check_cover_letter_text(text, len(text.split()))

    def test_correct_graduation_date_accepted(self):
        text = make_letter(250) + "\n\navailable after December 2026"
        _check_cover_letter_text(text, len(text.split()))
