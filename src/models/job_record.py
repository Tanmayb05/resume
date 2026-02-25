from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class JobStatus(str, Enum):
    """Lifecycle states of a job application."""

    DISCOVERED = "discovered"   # initial state when JD is pasted
    PROCESSING = "processing"   # generation in progress
    READY = "ready"             # artifacts generated, not yet submitted
    APPLIED = "applied"         # user has submitted the application


class JobRecord(BaseModel):
    """Represents a single job application and all associated artifacts.

    Intended to be serialized to/from JSON via model_dump_json() and
    model_validate_json() — no custom to_json / from_json wrappers.

    All path fields (job_dir, resume_pdf_path, cover_letter_path) hold
    absolute path strings. job_store.py is responsible for ensuring
    absolute paths before constructing this record.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="UUID4 identifier for the job application",
    )
    company: str = Field(..., min_length=1, description="Company name")
    role: str = Field(..., min_length=1, description="Job role / title")
    location: str = Field(..., min_length=1, description="Job location")
    status: JobStatus = Field(
        default=JobStatus.DISCOVERED,
        description="Current lifecycle state",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when record was created (UTC)",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of last modification (UTC)",
    )
    job_dir: str = Field(
        ...,
        description="Absolute path to the job-specific artifact directory",
    )
    jd_text: Optional[str] = Field(
        default=None,
        description="Raw pasted job-description text, stored for reference",
    )

    # --- Parsed JD fields ---
    employment_type: Optional[str] = Field(
        default=None,
        description="full-time | internship | contract",
    )
    department: Optional[str] = Field(
        default=None,
        description="Department or team name from the JD",
    )
    description: Optional[str] = Field(
        default=None,
        description="Role summary / overview paragraph from the JD",
    )
    responsibilities: List[str] = Field(
        default_factory=list,
        description="Bullet-point responsibilities from the JD",
    )
    requirements: List[str] = Field(
        default_factory=list,
        description="Must-have requirements from the JD",
    )
    qualifications: List[str] = Field(
        default_factory=list,
        description="Nice-to-have / preferred qualifications from the JD",
    )
    skills_technical: List[str] = Field(
        default_factory=list,
        description="Technical skills extracted from the JD",
    )
    skills_soft: List[str] = Field(
        default_factory=list,
        description="Soft skills extracted from the JD",
    )
    education: List[str] = Field(
        default_factory=list,
        description="Education requirements from the JD",
    )
    experience_required: Optional[str] = Field(
        default=None,
        description="Experience level required (e.g. '2+ years', 'internship-level')",
    )
    benefits: List[str] = Field(
        default_factory=list,
        description="Benefits listed in the JD",
    )
    salary_range: Optional[str] = Field(
        default=None,
        description="Salary range from the JD, or 'Not disclosed'",
    )
    date_posted: Optional[str] = Field(
        default=None,
        description="Date the job was posted, if mentioned",
    )
    application_deadline: Optional[str] = Field(
        default=None,
        description="Application deadline, if mentioned",
    )
    visa_keywords: List[str] = Field(
        default_factory=list,
        description="Raw visa/sponsorship keyword phrases found in the JD",
    )

    # --- F1 detection ---
    f1_sponsorship_available: Optional[bool] = Field(
        default=None,
        description="Whether the role offers F-1 visa sponsorship (None = not yet detected)",
    )
    resume_pdf_path: Optional[str] = Field(
        default=None,
        description="Absolute path to the generated resume PDF once produced",
    )
    cover_letter_path: Optional[str] = Field(
        default=None,
        description="Absolute path to the generated cover letter once produced",
    )
    generation_iterations: int = Field(
        default=0,
        description="Number of TRIM iterations that have run for this application",
    )

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        use_enum_values=True,
    )

    def mark_updated(self) -> None:
        """Update the updated_at timestamp to the current UTC time."""
        self.updated_at = datetime.utcnow()
