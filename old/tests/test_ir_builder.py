"""Tests for src/resume/ir_builder.py — the master_resume -> render-IR assembly.

Covers: the golden-output regression protecting the selection.py refactor, schema
compliance of the id-based path, and the fabrication guards (dates/companies cannot
be overridden, unknown ids/skills/indices raise).
"""
import json
from pathlib import Path

import jsonschema
import pytest

from src.resume.ir_builder import (
    _assemble_payload,
    available_ids,
    build_resume_payload,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
MASTER_RESUME = json.loads((REPO_ROOT / "templates" / "master_resume.json").read_text())
RESUME_SCHEMA = json.loads(
    (REPO_ROOT / "templates" / "resume_json_template.json").read_text()
)
GOLDEN_PAYLOAD = json.loads(
    (REPO_ROOT / "tests" / "fixtures" / "golden_resume_payload.json").read_text()
)


def minimal_content(**overrides) -> dict:
    ids = available_ids(MASTER_RESUME)
    data = {
        "experience_ids": ids["experience_ids"][:1],
        "project_ids": ids["project_ids"][:1],
        # resume_json_template.json requires >=2 skills lines, each with >=2 items.
        "skills": {
            "programming": MASTER_RESUME["technical_skills"]["programming"][:2],
            "developer_tools": MASTER_RESUME["technical_skills"]["developer_tools"][:2],
        },
    }
    data.update(overrides)
    return data


class TestGoldenRegression:
    """Protects the selection.py -> ir_builder.py move: output must not change."""

    def test_assemble_payload_matches_pre_refactor_golden(self):
        payload = _assemble_payload(
            master_resume=MASTER_RESUME,
            selected_experiences=MASTER_RESUME["work_experience"][:2],
            selected_projects=MASTER_RESUME["projects_and_research"][:2],
            selected_skills={
                "programming": MASTER_RESUME["technical_skills"]["programming"][:3],
                "developer_tools": MASTER_RESUME["technical_skills"]["developer_tools"][:4],
            },
        )
        assert payload == GOLDEN_PAYLOAD


class TestBuildResumePayloadSchema:
    def test_payload_validates_against_render_schema(self):
        payload = build_resume_payload(MASTER_RESUME, minimal_content())
        jsonschema.validate(payload, RESUME_SCHEMA)

    def test_exactly_five_sections_in_fixed_order(self):
        payload = build_resume_payload(MASTER_RESUME, minimal_content())
        assert [s["type"] for s in payload["sections"]] == [
            "education",
            "technical_skills",
            "work_experience",
            "projects_and_research",
            "extracurricular",
        ]

    def test_summary_key_rejected(self):
        with pytest.raises(ValueError, match="summary"):
            build_resume_payload(MASTER_RESUME, minimal_content(summary="I am great."))


class TestFabricationGuards:
    def test_dates_and_company_come_from_master_only(self):
        ids = available_ids(MASTER_RESUME)
        exp_id = ids["experience_ids"][0]
        with pytest.raises(ValueError, match="disallowed keys"):
            build_resume_payload(
                MASTER_RESUME,
                minimal_content(
                    experience_overrides={
                        exp_id: {"bullets": ["ok"], "dates": "Jan 2030 - Now"}
                    }
                ),
            )

    def test_experience_override_cannot_change_company(self):
        ids = available_ids(MASTER_RESUME)
        exp_id = ids["experience_ids"][0]
        with pytest.raises(ValueError, match="disallowed keys"):
            build_resume_payload(
                MASTER_RESUME,
                minimal_content(
                    experience_overrides={exp_id: {"company": "Fake Corp"}}
                ),
            )

    def test_unknown_experience_id_raises(self):
        with pytest.raises(ValueError, match="Unknown experience_id"):
            build_resume_payload(
                MASTER_RESUME, minimal_content(experience_ids=["not-a-real-id"])
            )

    def test_unknown_project_id_raises(self):
        with pytest.raises(ValueError, match="Unknown project_id"):
            build_resume_payload(
                MASTER_RESUME, minimal_content(project_ids=["not-a-real-project"])
            )

    def test_skill_not_in_master_raises(self):
        with pytest.raises(ValueError, match="not in master_resume"):
            build_resume_payload(
                MASTER_RESUME,
                minimal_content(skills={"programming": ["COBOL"]}),
            )

    def test_unknown_skill_category_raises(self):
        with pytest.raises(ValueError, match="Unknown skill category"):
            build_resume_payload(
                MASTER_RESUME,
                minimal_content(skills={"quantum_computing": ["Qiskit"]}),
            )

    def test_extracurricular_index_out_of_range_raises(self):
        with pytest.raises(ValueError, match="out of range"):
            build_resume_payload(
                MASTER_RESUME, minimal_content(extracurricular_indices=[99])
            )

    def test_empty_override_bullets_rejected(self):
        ids = available_ids(MASTER_RESUME)
        exp_id = ids["experience_ids"][0]
        with pytest.raises(ValueError, match="must not be empty"):
            build_resume_payload(
                MASTER_RESUME,
                minimal_content(experience_overrides={exp_id: {"bullets": []}}),
            )

    def test_valid_bullet_override_applied(self):
        ids = available_ids(MASTER_RESUME)
        exp_id = ids["experience_ids"][0]
        payload = build_resume_payload(
            MASTER_RESUME,
            minimal_content(
                experience_overrides={exp_id: {"bullets": ["Custom bullet text."]}}
            ),
        )
        entry = payload["sections"][2]["entries"][0]
        assert entry["bullets"] == ["Custom bullet text."]
        # Company/dates must still come from master, not from the override.
        master_exp = next(
            e for e in MASTER_RESUME["work_experience"]
            if e["company"] == entry["company"]
        )
        assert entry["dates"].startswith(master_exp["start_date"])


class TestAvailableIds:
    def test_ids_are_full_length_not_truncated(self):
        ids = available_ids(MASTER_RESUME)
        # sanitize_slug caps at 50 chars; ir_builder ids must not collide because of it.
        assert len(set(ids["experience_ids"])) == len(ids["experience_ids"])
        assert len(set(ids["project_ids"])) == len(ids["project_ids"])
