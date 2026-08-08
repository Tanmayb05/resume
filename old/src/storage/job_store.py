import json
import logging
import os
import tempfile
from pathlib import Path
from typing import List

from src.models.job_record import JobRecord
from src.utils.paths import get_job_dir, sanitize_slug

logger = logging.getLogger(__name__)


class JobStore:
    """Filesystem-backed persistence for JobRecord objects.

    Layout:
        data/<company-slug>-<role-slug>/job.json
        data/<company-slug>-<role-slug>/  (artifacts live here flat)

    All paths stored in records are absolute.
    Writes are atomic: tempfile + os.replace() prevents corruption.
    """

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir.resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def new_job_dir(self, company: str, role: str) -> Path:
        """Allocate a new (non-existing) job directory path.

        Does NOT create the directory. Call .mkdir() on the result
        before writing to it.
        """
        return get_job_dir(self.data_dir, company, role)

    def write(self, record: JobRecord) -> None:
        """Atomically write a JobRecord to <job_dir>/job.json.

        Creates the directory if it does not exist.
        Uses tempfile + os.replace() for corruption-safe writes.

        Args:
            record: The JobRecord to persist.

        Raises:
            ValueError: If record.job_dir is not an absolute path.
        """
        job_dir = Path(record.job_dir)
        if not job_dir.is_absolute():
            raise ValueError(
                f"JobRecord.job_dir must be absolute, got: {record.job_dir}"
            )
        job_dir.mkdir(parents=True, exist_ok=True)
        job_file = job_dir / "job.json"

        json_bytes = record.model_dump_json(indent=2).encode("utf-8")

        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=job_dir,
            delete=False,
            suffix=".tmp",
        ) as tmp:
            tmp.write(json_bytes)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = Path(tmp.name)

        try:
            tmp_path.replace(job_file)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise

        logger.debug("Wrote job record to %s", job_file)

    def read(self, job_dir: Path) -> JobRecord:
        """Read and validate a JobRecord from <job_dir>/job.json.

        Args:
            job_dir: Path to the job-specific artifact directory.

        Returns:
            A validated JobRecord instance.

        Raises:
            FileNotFoundError: if job.json does not exist in the directory.
            ValueError: if job.json contains invalid or corrupted JSON.
        """
        job_file = job_dir.resolve() / "job.json"
        if not job_file.exists():
            raise FileNotFoundError(f"No job.json found in {job_dir}")

        try:
            raw = job_file.read_text(encoding="utf-8")
            return JobRecord.model_validate_json(raw)
        except Exception as exc:
            raise ValueError(
                f"Failed to parse job.json in {job_dir}: {exc}"
            ) from exc

    def list_all(self) -> List[JobRecord]:
        """Return all valid job records sorted most-recent-first by created_at.

        Directories without a valid job.json are silently skipped (logged at DEBUG).

        Returns:
            List of JobRecord objects sorted by created_at descending.
        """
        records: List[JobRecord] = []
        for entry in self.data_dir.iterdir():
            if not entry.is_dir():
                continue
            try:
                record = self.read(entry)
                records.append(record)
            except (FileNotFoundError, ValueError) as exc:
                logger.debug("Skipping %s: %s", entry.name, exc)

        records.sort(key=lambda r: r.created_at, reverse=True)
        return records
