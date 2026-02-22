"""PDF analyzer module — page count, whitespace ratio, and overflow detection.

analyze_pdf() uses PyMuPDF (fitz) to extract structural metrics from a compiled
resume PDF. These metrics drive the Phase 4 enforcement loop:
  - page_count > 1 signals overflow (primary signal)
  - page_height_inches > 11.5 with page_count == 1 signals single-tall-page overflow
  - whitespace_ratio supports EXPAND decision (< 0.40 threshold, calibrate empirically)

All errors return a sentinel dict (success=False, page_count=-1, whitespace_ratio=-1.0)
rather than raising exceptions — callers check result["success"] before using values.
"""
import fitz  # PyMuPDF
from pathlib import Path


def analyze_pdf(pdf_path: "Path | str") -> dict:
    """Analyze a PDF for page count and whitespace ratio using PyMuPDF.

    Args:
        pdf_path: Path to the PDF file to analyze.

    Returns:
        On success:
            {
                "success": True,
                "page_count": int,           # Number of pages (>1 = overflow signal)
                "whitespace_ratio": float,   # 0.0 (full text) to 1.0 (all white)
                "page_height_inches": float, # Height of first page in inches
            }
        On error (missing / corrupt / unreadable PDF):
            {
                "success": False,
                "page_count": -1,
                "whitespace_ratio": -1.0,
                "error": str,               # Actionable error message
            }

    Notes:
        whitespace_ratio = 1.0 - (total_text_area / total_page_area)
        - total_page_area: sum of (width * height) across all pages
        - total_text_area: sum of bounding box areas from page.get_text("blocks")
        - Result is clamped to [0.0, 1.0] with max/min guards

        page_height_inches supports Phase 4 single-tall-page overflow detection
        (Research Pitfall 3): a tectonic-compiled page that overflows without
        breaking to page 2 will have page_count=1 but page_height_inches > 11.5.
        PDF points = 1/72 inch, so height_in_points / 72 = height_in_inches.
    """
    try:
        doc = fitz.open(str(pdf_path))
        page_count = doc.page_count

        total_page_area = 0.0
        total_text_area = 0.0

        for page_idx in range(page_count):
            page = doc[page_idx]
            page_area = float(page.rect.width) * float(page.rect.height)
            total_page_area += page_area

            blocks = page.get_text("blocks")
            for block in blocks:
                # block: (x0, y0, x1, y1, "text", block_no, block_type)
                block_w = float(block[2]) - float(block[0])
                block_h = float(block[3]) - float(block[1])
                # Only count positive-area text blocks (type==0 is text)
                if block_w > 0 and block_h > 0:
                    total_text_area += block_w * block_h

        # Page height in inches (for overflow detection in Phase 4)
        first_page_height_in = float(doc[0].rect.height) / 72.0 if page_count > 0 else 0.0

        doc.close()

        if total_page_area > 0:
            text_fill = total_text_area / total_page_area
            whitespace_ratio = max(0.0, min(1.0, 1.0 - text_fill))
        else:
            whitespace_ratio = 1.0

        return {
            "success": True,
            "page_count": page_count,
            "whitespace_ratio": float(whitespace_ratio),
            "page_height_inches": round(first_page_height_in, 4),
        }

    except FileNotFoundError:
        return {
            "success": False,
            "page_count": -1,
            "whitespace_ratio": -1.0,
            "error": f"PDF not found: {pdf_path}",
        }
    except Exception as exc:
        return {
            "success": False,
            "page_count": -1,
            "whitespace_ratio": -1.0,
            "error": f"Error analyzing PDF: {exc}",
        }
