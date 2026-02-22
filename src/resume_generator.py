
import os
import subprocess
import shutil
from logger import get_logger

logger = get_logger(__name__)

def read_latex_template(template_path: str) -> str:
    """
    Reads the content of a LaTeX template file.

    Args:
        template_path: The path to the LaTeX template.

    Returns:
        The content of the template file.
    """
    logger.debug(f"Reading LaTeX template from: {template_path}")
    try:
        with open(template_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"LaTeX template not found at: {template_path}")
        raise

def compile_latex_to_pdf(latex_file_path: str):
    """
    Compiles a LaTeX file to PDF using tectonic.

    Tectonic is a modernized, self-contained TeX/LaTeX engine that automatically
    downloads required packages. Install with: cargo install tectonic
    or via package manager (brew install tectonic, apt install tectonic, etc.)

    Args:
        latex_file_path: The path to the LaTeX file.
    """
    if not latex_file_path.endswith(".tex"):
        raise ValueError("The input file must be a .tex file")

    output_directory = os.path.dirname(latex_file_path)
    if not output_directory:
        output_directory = '.'

    # Use tectonic for LaTeX to PDF compilation
    # tectonic is easier to install and self-contained compared to full TeX Live
    command = [
        "tectonic",
        "-o", output_directory,
        latex_file_path
    ]

    logger.info(f"Compiling {latex_file_path} to PDF using tectonic...")
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        logger.info(f"Successfully compiled {latex_file_path} to PDF.")
    except FileNotFoundError:
        logger.critical("tectonic command not found. Please install tectonic:")
        logger.critical("  - macOS: brew install tectonic")
        logger.critical("  - Linux: cargo install tectonic (or use package manager)")
        logger.critical("  - Windows: cargo install tectonic")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Error compiling LaTeX file: {latex_file_path}")
        logger.error(f"tectonic stdout:\n{e.stdout}")
        logger.error(f"tectonic stderr:\n{e.stderr}")
        raise
