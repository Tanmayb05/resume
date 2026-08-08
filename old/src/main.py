
import argparse
import json
import os
import subprocess
import shutil
import requests
from llm import parse_jd_to_json, generate_latex_resume, generate_cover_letter, OllamaError, extract_company_name
from resume_generator import read_latex_template, compile_latex_to_pdf
from cover_letter_generator import save_as_docx, convert_docx_to_pdf
from pdf_analyzer import analyze_whitespace
from config import AppConfig
from logger import get_logger

config = AppConfig()
logger = get_logger(__name__)

def check_dependencies():
    """Checks for required external dependencies."""
    # Only check for ollama and tectonic (docx2pdf is a Python package)
    dependencies = ["ollama", "pdflatex", "libreoffice"]
    missing_deps = []
    for dep in dependencies:
        if not shutil.which(dep):
            missing_deps.append(dep)

    if missing_deps:
        logger.critical(f"The following dependencies are not installed or not in your PATH: {', '.join(missing_deps)}")
        if "tectonic" in missing_deps:
            logger.critical("Install tectonic with:")
            logger.critical("  - macOS: brew install tectonic")
            logger.critical("  - Linux: cargo install tectonic (or use package manager)")
            logger.critical("  - Windows: cargo install tectonic")
        exit(1)

    # Check if ollama is running
    try:
        requests.get(config.llm_host)
    except requests.exceptions.ConnectionError:
        logger.critical("Ollama is not running. Please start Ollama and try again.")
        exit(1)


def main():
    check_dependencies()

    parser = argparse.ArgumentParser(description="Intelligent Job Application Tailoring System")
    parser.add_argument("--jd", required=True, help="Path to the job description file")
    parser.add_argument("--no-optimization", action="store_true", help="Skip whitespace optimization")
    args = parser.parse_args()

    try:
        # Read the job description file
        with open(args.jd, 'r') as f:
            jd_content = f.read()

        # Extract company name
        logger.info("Extracting company name from job description...")
        company_name = extract_company_name(jd_content)
        if not company_name:
            logger.critical("Could not extract company name from the job description. Exiting.")
            exit(1)
        logger.info(f"Company name extracted: {company_name}")

        # Parse JD to JSON
        logger.info("Parsing job description to JSON...")
        jd_json = parse_jd_to_json(jd_content)
        if not jd_json:
            logger.critical("Could not parse the job description to JSON. Exiting.")
            exit(1)
        logger.info("Successfully parsed job description to JSON.")


        # Read the resume template
        latex_template_path = os.path.join(config.templates_dir, "resume_template.tex")
        logger.debug(f"Reading resume template from: {latex_template_path}")
        resume_template_content = read_latex_template(latex_template_path)

        # Create the output directory
        output_dir = os.path.join(str(config.data_dir), company_name)
        os.makedirs(output_dir, exist_ok=True)
        logger.debug(f"Output directory created at: {output_dir}")

        # Save the parsed JD JSON
        jd_json_path = os.path.join(output_dir, f"{company_name}_jd.json")
        with open(jd_json_path, "w") as f:
            json.dump(jd_json, f, indent=2)
        logger.info(f"Parsed job description JSON saved to {jd_json_path}")

        # --- Resume Generation ---
        tailored_latex_resume = None
        if args.no_optimization:
            logger.info("Skipping whitespace optimization.")
            # Generate the tailored LaTeX resume once
            logger.info("Generating tailored resume...")
            tailored_latex_resume = generate_latex_resume(jd_json, resume_template_content)

            if tailored_latex_resume:
                # Save the LaTeX resume
                latex_output_path = os.path.join(output_dir, f"{company_name}_resume.tex")
                with open(latex_output_path, "w") as f:
                    f.write(tailored_latex_resume)
                logger.info(f"Tailored LaTeX resume saved to {latex_output_path}")

                # Compile the LaTeX file to PDF
                try:
                    compile_latex_to_pdf(latex_output_path)
                    pdf_output_path = latex_output_path.replace(".tex", ".pdf")
                    logger.info(f"Successfully created PDF: {pdf_output_path}")
                except (ValueError, FileNotFoundError, subprocess.CalledProcessError) as e:
                    logger.error("Failed to generate PDF. Please check the logs.", exc_info=True)
        else:
            # --- Whitespace Optimization Loop ---
            expand_sections = []
            for i in range(config.max_iterations):
                logger.info(f"--- Optimization Iteration {i+1}/{config.max_iterations} ---")

                # Generate the tailored LaTeX resume
                logger.info("Generating tailored resume...")
                tailored_latex_resume = generate_latex_resume(jd_json, resume_template_content, expand_sections)

                if not tailored_latex_resume:
                    logger.warning("Failed to generate tailored resume. The LLM returned an empty response.")
                    continue

                # Save the LaTeX resume
                latex_output_path = os.path.join(output_dir, f"{company_name}_resume_iter_{i+1}.tex")
                with open(latex_output_path, "w") as f:
                    f.write(tailored_latex_resume)
                logger.info(f"Tailored LaTeX resume (iter {i+1}) saved to {latex_output_path}")

                # Compile the LaTeX file to PDF
                try:
                    compile_latex_to_pdf(latex_output_path)
                    pdf_output_path = latex_output_path.replace(".tex", ".pdf")
                    logger.info(f"Successfully created PDF (iter {i+1}): {pdf_output_path}")
                except (ValueError, FileNotFoundError, subprocess.CalledProcessError) as e:
                    logger.error(f"Failed to generate PDF (iter {i+1}). Please check the logs.", exc_info=True)
                    continue  # Try next iteration

                # Analyze whitespace
                whitespace_percentage = analyze_whitespace(pdf_output_path)
                logger.info(f"Whitespace analysis (iter {i+1}): {whitespace_percentage:.2f}%")

                if whitespace_percentage <= config.whitespace_threshold:
                    logger.info("Whitespace is within the acceptable threshold. Optimization complete.")
                    break
                else:
                    logger.warning("Whitespace is too high. Will attempt to expand sections.")
                    expand_sections = config.expand_sections_default
            else:
                logger.warning("Max optimization iterations reached. The resume may still have too much whitespace.")


        # --- Cover Letter Generation ---
        if tailored_latex_resume:
            logger.info("--- Generating Cover Letter ---")
            cover_letter = generate_cover_letter(jd_json, tailored_latex_resume)

            if not cover_letter:
                logger.warning("Failed to generate cover letter. The LLM returned an empty response.")
                return

            # Save the cover letter as a .docx file
            docx_output_path = os.path.join(output_dir, f"{company_name}_cover_letter.docx")
            save_as_docx(cover_letter, docx_output_path)
            logger.info(f"Cover letter saved to {docx_output_path}")

            # Convert the .docx to .pdf
            try:
                convert_docx_to_pdf(docx_output_path)
                pdf_output_path = docx_output_path.replace(".docx", ".pdf")
                logger.info(f"Successfully created PDF: {pdf_output_path}")
            except (ValueError, Exception) as e:
                logger.error("Failed to generate PDF from .docx. Please check the logs.", exc_info=True)

    except OllamaError as e:
        logger.critical(f"An error occurred while communicating with the Ollama API: {e}", exc_info=True)
        logger.critical("Please ensure that Ollama is running and the model is available.")
    except FileNotFoundError as e:
        logger.critical(f"File not found: {e}", exc_info=True)
    except Exception as e:
        logger.critical(f"An unexpected error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    main()
