
import os
from docx import Document
from docx2pdf import convert
from logger import get_logger

logger = get_logger(__name__)

def save_as_docx(text: str, path: str):
    """
    Saves a string of text as a .docx file.

    Args:
        text: The text to save.
        path: The path to save the .docx file to.
    """
    logger.info(f"Saving cover letter to {path}")
    try:
        document = Document()
        document.add_paragraph(text)
        document.save(path)
        logger.info("Successfully saved cover letter as .docx")
    except Exception as e:
        logger.error(f"Failed to save cover letter as .docx: {e}", exc_info=True)
        raise

def convert_docx_to_pdf(docx_path: str):
    """
    Converts a .docx file to .pdf using the docx2pdf Python library.

    This library uses:
    - macOS: Microsoft Word (if installed) or LibreOffice
    - Windows: Microsoft Word
    - Linux: LibreOffice

    Install with: pip install docx2pdf

    Args:
        docx_path: The path to the .docx file.
    """
    if not docx_path.endswith(".docx"):
        raise ValueError("The input file must be a .docx file")

    output_dir = os.path.dirname(docx_path)
    if not output_dir:
        output_dir = '.'

    pdf_path = docx_path.replace(".docx", ".pdf")

    logger.info(f"Converting {docx_path} to PDF using docx2pdf...")
    try:
        convert(docx_path, pdf_path)
        logger.info(f"Successfully converted {docx_path} to PDF.")
    except Exception as e:
        logger.error(f"Error converting .docx to .pdf: {docx_path}")
        logger.error(f"Error details: {e}")
        logger.critical("docx2pdf requires Microsoft Word (macOS/Windows) or LibreOffice (Linux).")
        logger.critical("  - macOS: Install Microsoft Word or LibreOffice")
        logger.critical("  - Windows: Install Microsoft Word")
        logger.critical("  - Linux: Install LibreOffice (apt install libreoffice)")
        raise
