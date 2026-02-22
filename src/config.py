from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Application configuration loaded from environment variables / .env file.

    Required fields raise ValidationError at startup if missing — fail fast,
    never silently use wrong credentials.

    Environment variable names use the APP_ prefix (case-insensitive), e.g.:
      APP_ANTHROPIC_API_KEY=sk-ant-...
      APP_DATA_DIR=data
      APP_MAX_ITERATIONS=5
    """

    # Required — no default, will raise ValidationError if missing
    anthropic_api_key: str = Field(..., description="Anthropic Claude API key (required)")

    # Optional with sensible defaults
    data_dir: Path = Field(
        default=Path("data"),
        description="Root directory for job application artifacts",
    )
    max_iterations: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum resume TRIM iterations before giving up",
    )
    llm_model: str = Field(
        default="claude-opus-4-5",
        description="Anthropic model ID to use for generation",
    )
    llm_timeout_seconds: int = Field(
        default=120,
        ge=10,
        description="Seconds before an LLM request times out",
    )

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("data_dir", mode="after")
    @classmethod
    def resolve_data_dir(cls, v: Path) -> Path:
        """Always store data_dir as an absolute path."""
        return v.resolve()

    @property
    def data_dir_resolved(self) -> Path:
        """Absolute data directory, created if it does not yet exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir
