"""DOCX rendering for cover letters.

The .txt file Claude writes is the single source of truth. Two renderers consume
it: this module produces the .docx, and cover_letter_template.tex.j2 + tectonic
produces the .pdf. There is no docx->pdf converter on this machine (no
LibreOffice, no pandoc), so the two outputs are generated independently.

split_paragraphs() lives here and is imported by the PDF path too, so both
renderers see byte-identical paragraph lists. That shared split is what keeps
the .docx and .pdf from drifting.
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt

# Body font, matching a conventional business letter.
_FONT_NAME = "Calibri"
_FONT_SIZE_PT = 11
_SPACE_AFTER_PT = 10

# Margins from cover_letter_template.tex.j2 so the docx and pdf frame alike.
_MARGIN_TOP_IN = 1.0
_MARGIN_BOTTOM_IN = 1.0
_MARGIN_LEFT_IN = 1.25
_MARGIN_RIGHT_IN = 1.25

_PARAGRAPH_BREAK = re.compile(r"\n{2,}")


def split_paragraphs(text: str) -> list[str]:
    """Split cover-letter text into paragraphs on blank-line boundaries.

    Shared by the docx and pdf renderers so both receive the same list.
    Single newlines are preserved inside a paragraph (the signature block relies
    on them); runs of two or more separate paragraphs.
    """
    blocks = _PARAGRAPH_BREAK.split(text.strip())
    return [block.strip() for block in blocks if block.strip()]


def write_cover_letter_docx(text: str, output_path: Path) -> Path:
    """Render cover-letter text to a .docx file.

    Args:
        text: The full cover letter, paragraphs separated by blank lines.
        output_path: Destination .docx path. Parent must exist.

    Returns:
        The path written.

    Raises:
        ValueError: If the text yields no paragraphs.
    """
    paragraphs = split_paragraphs(text)
    if not paragraphs:
        raise ValueError("Cover letter text produced zero paragraphs")

    document = Document()

    style = document.styles["Normal"]
    style.font.name = _FONT_NAME
    style.font.size = Pt(_FONT_SIZE_PT)

    for section in document.sections:
        section.top_margin = Inches(_MARGIN_TOP_IN)
        section.bottom_margin = Inches(_MARGIN_BOTTOM_IN)
        section.left_margin = Inches(_MARGIN_LEFT_IN)
        section.right_margin = Inches(_MARGIN_RIGHT_IN)

    for block in paragraphs:
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(_SPACE_AFTER_PT)
        paragraph.paragraph_format.first_line_indent = Inches(0)

        # A single newline inside a block is a hard line break, not a new
        # paragraph — the signature block depends on this.
        lines = block.split("\n")
        run = paragraph.add_run(lines[0])
        run.font.name = _FONT_NAME
        run.font.size = Pt(_FONT_SIZE_PT)
        for line in lines[1:]:
            run.add_break()
            run.add_text(line)

    output_path = Path(output_path)
    document.save(str(output_path))
    return output_path
