
import json
import requests
from config import AppConfig
from logger import get_logger

config = AppConfig()
logger = get_logger(__name__)

class OllamaError(Exception):
    """Custom exception for Ollama API errors."""
    pass

def prompt_ollama(prompt: str) -> str:
    """
    Sends a prompt to the Ollama API and returns the response.

    Args:
        prompt: The prompt to send to the LLM.

    Returns:
        The response from the LLM.

    Raises:
        OllamaError: If there is an error communicating with the Ollama API.
    """
    ollama_url = f"{config.llm_host}/api/generate"
    logger.debug(f"Prompting Ollama with model {config.llm_default_model}")
    try:
        response = requests.post(
            ollama_url,
            json={"model": config.llm_default_model, "prompt": prompt, "stream": False},
            headers={"Content-Type": "application/json"},
            timeout=config.llm_timeout_seconds,
        )
        response.raise_for_status()
        logger.debug("Ollama request successful.")
        return response.json()["response"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Ollama API: {e}", exc_info=True)
        raise OllamaError(f"Error calling Ollama API: {e}") from e

def parse_jd_to_json(jd_text: str) -> dict:
    """
    Parses a job description text and returns a structured JSON object.

    Args:
        jd_text: The raw job description text.

    Returns:
        A dictionary representing the structured job description, or an empty dict on failure.
    """
    schema_path = "templates/job_description_schema.json"
    logger.debug(f"Reading job description schema from: {schema_path}")
    try:
        with open(schema_path) as f:
            schema = f.read()
    except FileNotFoundError:
        logger.error(f"Job description schema not found at: {schema_path}")
        raise

    template_path = "templates/jd_parser_prompt.md"
    with open(template_path) as f:
        system_instructions = f.read()

    prompt = f"""
{system_instructions}
{schema}

Job Description:
---
{jd_text}
---

Respond with ONLY the JSON object, without any additional text, comments, or explanations.
"""

    try:
        llm_response = prompt_ollama(prompt)
    except OllamaError as e:
        raise OllamaError(f"Failed to parse job description to JSON: {e}") from e

    if not llm_response:
        logger.warning("LLM returned an empty response for the JD to JSON parsing.")
        return {}

    try:
        # The LLM response might have markdown ```json ... ``` tags
        if llm_response.strip().startswith("```json"):
            llm_response = llm_response.strip()[7:-4]
        return json.loads(llm_response)
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from LLM response: {e}")
        logger.debug(f"LLM Response was:\n{llm_response}")
        return {}  # Return empty dict on failure

def generate_latex_resume(jd_json: dict, resume_template: str, expand_sections: list = None) -> str:
    """
    Generates a tailored resume in LaTeX format.

    Args:
        jd_json: A dictionary representing the structured job description.
        resume_template: The content of the resume template.
        expand_sections: A list of sections to expand.

    Returns:
        The tailored resume as a LaTeX string.
    """
    # Load resume generation config rules
    config_path = "templates/resume_generation_config.json"
    with open(config_path) as f:
        resume_config = json.load(f)
    rules_json = json.dumps(resume_config, indent=2)

    # Build expansion sub-prompt if needed
    expansion_prompt = ""
    if expand_sections:
        exp_template_path = "templates/resume_expansion_prompt.md"
        with open(exp_template_path) as f:
            exp_template = f.read()
        # Replace placeholder with actual section list
        sections_str = ', '.join(expand_sections)
        expansion_prompt = exp_template.replace("{{SECTIONS}}", sections_str)

    # Load main generation prompt
    template_path = "templates/resume_generation_prompt.md"
    with open(template_path) as f:
        system_instructions = f.read()

    prompt = f"""
{system_instructions}

Tailoring rules to apply:
<tailoring_rules>
{rules_json}
</tailoring_rules>

Here is the structured Job Description:
<job_description>
{json.dumps(jd_json, indent=2)}
</job_description>

Here is the Resume Template:
<resume_template>
{resume_template}
</resume_template>

{expansion_prompt}

Respond with ONLY the full LaTeX code for the tailored resume, without any additional text, comments, or explanations.
"""

    try:
        llm_response = prompt_ollama(prompt)
    except OllamaError as e:
        raise OllamaError(f"Failed to generate tailored resume: {e}") from e

    if not llm_response:
        logger.warning("LLM returned an empty response for the resume generation.")
        return ""

    # The LLM response might have markdown ```latex ... ``` tags
    if llm_response.strip().startswith("```latex"):
        llm_response = llm_response.strip()[8:-4]

    return llm_response

def extract_company_name(jd_text: str) -> str:
    """
    Extracts the company name from the job description.

    Args:
        jd_text: The raw job description text.

    Returns:
        The extracted company name.
    """
    template_path = "templates/company_name_extractor_prompt.md"
    with open(template_path) as f:
        system_instructions = f.read()

    prompt = f"""
{system_instructions}

Job Description:
---
{jd_text}
---
"""
    try:
        company_name = prompt_ollama(prompt)
    except OllamaError as e:
        raise OllamaError(f"Failed to extract company name: {e}") from e

    if not company_name:
        logger.warning("LLM returned an empty response for the company name extraction.")
        return ""

    return company_name.strip()

def generate_cover_letter(jd_json: dict, tailored_resume: str) -> str:
    """
    Generates a cover letter based on the job description and the tailored resume.

    Args:
        jd_json: A dictionary representing the structured job description.
        tailored_resume: The tailored resume content.

    Returns:
        The generated cover letter as a string.
    """
    template_path = "templates/cover_letter_prompt.md"
    logger.debug(f"Reading cover letter prompt from: {template_path}")
    try:
        with open(template_path) as f:
            prompt_template = f.read()
    except FileNotFoundError:
        logger.error(f"Cover letter prompt template not found at: {template_path}")
        raise

    prompt = f"""
    {prompt_template}

    Here is the structured Job Description:
    <job_description>
    {json.dumps(jd_json, indent=2)}
    </job_description>

    Here is the tailored resume:
    <resume>
    {tailored_resume}
    </resume>

    IMPORTANT INSTRUCTIONS:
    - Start the cover letter DIRECTLY with "Dear Hiring Committee," - do NOT include any preamble like "Here is a cover letter" or similar text.
    - Use bullet points with "•" (bullet character) or "-" (hyphen) for lists, NOT asterisks (*).
    - Do NOT escape special characters like %. Write them normally (e.g., "50%" not "50\\%").
    - The signature block with name, email, phone number, and address MUST be included at the end exactly as shown in the template.

    Now, please generate the cover letter.
    """

    try:
        llm_response = prompt_ollama(prompt)
    except OllamaError as e:
        raise OllamaError(f"Failed to generate cover letter: {e}") from e

    if not llm_response:
        logger.warning("LLM returned an empty response for the cover letter generation.")
        return ""

    # Clean the response
    llm_response = _clean_cover_letter(llm_response)

    return llm_response

def _clean_cover_letter(text: str) -> str:
    """
    Cleans the cover letter text by removing preambles and fixing formatting issues.

    Args:
        text: The raw cover letter text from the LLM.

    Returns:
        The cleaned cover letter text.
    """
    import re

    for pattern in config.cover_letter_preamble_patterns:
        text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)

    # Remove escape characters before %
    text = text.replace('\\%', '%')

    # Replace asterisk bullet points with configured bullet char
    text = re.sub(r'^\s*\*\s+', config.cover_letter_bullet_char + ' ', text, flags=re.MULTILINE)

    return text.strip()
