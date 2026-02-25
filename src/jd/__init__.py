"""JD intake package — parse, F1 detect, persist."""
from src.jd.service import JDService, JDParseResult, detect_f1_sponsorship

__all__ = ["JDService", "JDParseResult", "detect_f1_sponsorship"]
