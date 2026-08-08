from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Application configuration loaded from environment variables / .env file.

    All fields with defaults are optional — only required fields raise ValidationError
    at startup if missing.

    Environment variable names use the APP_ prefix (case-insensitive), e.g.:
      APP_DATA_DIR=data
      APP_LLM_HOST=http://localhost:11434
      APP_LLM_DEFAULT_MODEL=zephyr
    """

    # Deprecated — was Anthropic API key; Ollama used instead.
    # Kept optional so existing .env files with this var don't break.
    anthropic_api_key: str | None = Field(
        default=None,
        description="Deprecated: was Anthropic API key; Ollama used instead",
    )

    # Optional with sensible defaults
    data_dir: Path = Field(
        default=Path("data"),
        description="Root directory for job application artifacts",
    )
    tracker_path: Path = Field(
        default=Path("output/Tanmay_Job_Application_Tracker.xlsx"),
        description="Excel workbook used to track job applications",
    )
    max_iterations: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum resume TRIM iterations before giving up",
    )

    # Ollama LLM configuration
    llm_host: str = Field(
        default="http://localhost:11434",
        description="Ollama server host URL",
    )
    llm_default_model: str = Field(
        default="zephyr",
        description="Default Ollama model for generation tasks (zephyr recommended for writing quality)",
    )
    llm_timeout_seconds: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Seconds before an LLM request times out (local Ollama inference takes 10-60s)",
    )
    llm_max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts on transient LLM errors before raising LLMError",
    )

    # Resume pipeline settings (migrated from config.yaml resume: block)
    whitespace_threshold: float = Field(
        default=40.0,
        ge=0.0,
        le=100.0,
        description="Whitespace percentage above which resume expansion is triggered",
    )
    expand_sections_default: list[str] = Field(
        default=["WORK EXPERIENCE"],
        description="Section names passed to the LLM when whitespace expansion is needed",
    )

    # Cover letter post-processing (was hardcoded in _clean_cover_letter)
    cover_letter_bullet_char: str = Field(
        default="•",
        description="Character to use for bullet points in cover letters (replaces asterisks)",
    )
    cover_letter_preamble_patterns: list[str] = Field(
        default=[r"^.*?(?=Dear\s+Hiring)"],
        description="Regex patterns to strip LLM preamble text before the salutation",
    )

    # Path settings (migrated from config.yaml paths: block)
    templates_dir: str = Field(
        default="templates",
        description="Directory containing prompt templates and LaTeX templates",
    )

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("data_dir", "tracker_path", mode="after")
    @classmethod
    def resolve_path(cls, v: Path) -> Path:
        """Always store configured project paths as absolute paths."""
        return v.resolve()

    @property
    def data_dir_resolved(self) -> Path:
        """Absolute data directory, created if it does not yet exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir
