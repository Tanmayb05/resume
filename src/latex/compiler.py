"""LaTeX compiler module — wraps tectonic CLI via subprocess.

compile_tex() compiles a .tex file to PDF using tectonic with structured error
returns. Never raises raw subprocess exceptions — all failures are returned as
structured dicts with an error_type discriminator.

check_ats_parsability() verifies PDF text extractability using pdftotext (poppler).
"""
import subprocess
from pathlib import Path


def compile_tex(tex_path: Path, output_dir: Path) -> dict:
    """Compile a .tex file to PDF via tectonic CLI.

    Args:
        tex_path:   Absolute path to the .tex file to compile.
        output_dir: Directory where tectonic writes the output PDF.
                    Must exist before calling (caller's responsibility).

    Returns:
        On success:
            {"success": True, "pdf_path": Path, "stderr": str | None}
        On failure:
            {"success": False, "error_type": str, "stderr": str, "return_code": int | None}
        error_type values: "compilation_failed" | "timeout" | "tectonic_not_found"

    Note on iter_N naming (RES-05):
        The caller is responsible for naming the .tex file with _iter_N suffix
        before calling compile_tex. tectonic derives the PDF name from the .tex
        stem, so resume_iter_0.tex produces resume_iter_0.pdf. This keeps the
        compiler as a thin subprocess wrapper with no iteration logic.
    """
    try:
        result = subprocess.run(
            ["tectonic", "--outdir", str(output_dir), str(tex_path)],
            capture_output=True,
            text=True,
            timeout=60,   # 60s — accounts for first-run package download
            check=True,   # Raises CalledProcessError if return code != 0
        )
        # tectonic names output PDF after the stem of the input .tex file
        pdf_path = output_dir / (tex_path.stem + ".pdf")
        return {
            "success": True,
            "pdf_path": pdf_path,
            "stderr": result.stderr if result.stderr else None,
        }
    except subprocess.CalledProcessError as exc:
        return {
            "success": False,
            "error_type": "compilation_failed",
            "stderr": (exc.stderr[:500] if exc.stderr else "No error output"),
            "return_code": exc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error_type": "timeout",
            "stderr": "tectonic compilation exceeded 60 second timeout",
            "return_code": None,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error_type": "tectonic_not_found",
            "stderr": "tectonic CLI not found in PATH. Install: brew install tectonic",
            "return_code": None,
        }


def check_ats_parsability(pdf_path: Path) -> bool:
    """Verify PDF contains extractable text via pdftotext (ATS parsability).

    Uses pdftotext (poppler) to extract text from the PDF and checks whether
    non-empty text is present. This confirms ATS systems can parse the resume.

    Args:
        pdf_path: Path to the PDF file to check.

    Returns:
        True if pdftotext extracts non-empty text (ATS-parsable).
        False if pdftotext runs but extracts no text (image-only PDF).
        True if pdftotext is not installed (tool unavailable — assume OK).
        False if pdftotext times out.
    """
    try:
        result = subprocess.run(
            ["pdftotext", str(pdf_path), "-"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,  # Non-zero return code is not always a failure
        )
        return len(result.stdout.strip()) > 0
    except FileNotFoundError:
        # pdftotext (poppler) not installed — cannot verify, assume OK
        return True
    except subprocess.TimeoutExpired:
        return False
