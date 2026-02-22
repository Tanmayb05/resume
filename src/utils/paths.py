import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def sanitize_slug(text: str) -> str:
    """Convert arbitrary user input into a filesystem-safe slug component.

    Rules (applied in order):
    1. Strip leading/trailing whitespace
    2. Convert to lowercase
    3. Pre-check for path traversal sequences before character stripping
    4. Replace whitespace runs and non-alphanumeric characters (except dash)
       with a single dash
    5. Strip leading and trailing dashes
    6. Raise ValueError if result is empty
    7. Truncate to 50 characters
    8. Final safety check — reject if result contains '..', '/', or '\\'

    Args:
        text: Company name or role title from user input.

    Returns:
        A lowercase, dash-separated slug safe for use in directory names.

    Raises:
        ValueError: If the input contains path traversal sequences, or if
                    the sanitized result is empty or contains unsafe characters.
    """
    # Step 1: Strip whitespace
    text = text.strip()

    # Step 2: Lowercase
    text = text.lower()

    # Step 3 (pre-check): Reject path traversal sequences before character
    # stripping would make them appear safe (e.g., "../../../etc" -> "etc")
    if ".." in text or text.startswith("/") or text.startswith("\\"):
        raise ValueError(
            f"Input contains path traversal sequence: {text!r}"
        )

    # Step 4: Replace non-alphanumeric runs (except dash) with a single dash
    slug = re.sub(r"[^a-z0-9]+", "-", text)

    # Step 5: Strip leading and trailing dashes
    slug = slug.strip("-")

    # Step 6: Raise if empty
    if not slug:
        raise ValueError(
            "Slug is empty after sanitization — provide a non-empty company or role name"
        )

    # Step 7: Truncate to 50 characters
    slug = slug[:50]

    # Step 8: Final safety check
    if ".." in slug or "/" in slug or "\\" in slug:
        raise ValueError(f"Sanitized slug contains unsafe characters: {slug}")

    return slug


def get_job_dir(data_dir: Path, company: str, role: str) -> Path:
    """Build the absolute directory path for a new job record.

    Implements collision detection with silent auto-increment: if the base
    directory already exists, appends -2, -3, etc. until a free name is found.

    Args:
        data_dir: Root data directory. Will be resolved to absolute path.
        company: Company name (will be sanitized to a slug).
        role: Job role title (will be sanitized to a slug).

    Returns:
        An absolute Path that does not yet exist on disk. The caller is
        responsible for creating the directory via mkdir().

    Raises:
        ValueError: If company or role cannot be sanitized (empty, traversal).
    """
    company_slug = sanitize_slug(company)
    role_slug = sanitize_slug(role)
    base_slug = f"{company_slug}-{role_slug}"

    candidate = (data_dir / base_slug).resolve()
    if not candidate.exists():
        return candidate

    counter = 2
    while True:
        candidate = (data_dir / f"{base_slug}-{counter}").resolve()
        if not candidate.exists():
            return candidate
        if counter > 10:
            logger.warning(
                "Counter for '%s' has reached %d — unusual duplication detected",
                base_slug,
                counter,
            )
        counter += 1
