"""Resume content selection, trimming, and validation package."""
from src.resume.selection import select_resume_content
from src.resume.validator import validate_content, ValidationResult

__all__ = ["select_resume_content", "validate_content", "ValidationResult"]
