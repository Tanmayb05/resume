
import fitz  # PyMuPDF
from logger import get_logger

logger = get_logger(__name__)

def analyze_whitespace(pdf_path: str) -> float:
    """
    Analyzes the whitespace in a PDF file.

    Args:
        pdf_path: The path to the PDF file.

    Returns:
        The percentage of whitespace in the PDF.
    """
    logger.info(f"Analyzing whitespace in {pdf_path}")
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logger.error(f"Error opening PDF file: {e}", exc_info=True)
        return 100.0 # Assume worst case

    total_page_area = 0
    total_text_area = 0

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        total_page_area += page.rect.width * page.rect.height
        
        text_blocks = page.get_text("blocks")
        for block in text_blocks:
            total_text_area += (block[2] - block[0]) * (block[3] - block[1])

    if total_page_area == 0:
        logger.warning("Total page area is zero. Cannot calculate whitespace.")
        return 100.0 # Avoid division by zero

    text_percentage = (total_text_area / total_page_area) * 100
    whitespace_percentage = 100 - text_percentage
    
    logger.info(f"Whitespace percentage: {whitespace_percentage:.2f}%")
    return whitespace_percentage
