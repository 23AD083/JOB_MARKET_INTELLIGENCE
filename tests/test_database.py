"""
Unit tests for database repository CRUD, profile updates, and assessment storage.
"""

import pytest
import uuid
from database.repository import DatabaseRepository
from database.models import User, Skill, Job


@pytest.fixture
def test_repo(tmp_path):
    db_file = tmp_path / "test_jobs.db"
    repo = DatabaseRepository(db_url=f"sqlite:///{db_file}")
    repo.init_db()
    return repo


def test_user_creation_and_profile_update(test_repo):
    user = test_repo.get_or_create_user(username="test_candidate", email="test@candidate.com")
    assert user.id is not None
    assert user.username == "test_candidate"

    # Update profile
    prof = test_repo.update_user_profile(user.id, {
        "education_degree": "Master's",
        "years_of_experience": 5.0,
        "workplace_preference": "remote"
    })
    assert prof.education_degree == "Master's"
    assert prof.years_of_experience == 5.0
    assert prof.workplace_preference == "remote"


def test_save_and_query_job(test_repo):
    job_data = {
        "job_id": "test_job_100",
        "source": "kaggle_csv",
        "job_title": "Full Stack Developer",
        "company_name": "Test Ventures",
        "job_description": "Building full stack apps with React and FastAPI.",
        "location": "Seattle, WA",
        "category": "Software Development",
        "content_hash": "testhash111222333444555"
    }
    summary_data = {
        "role_overview": "Building full stack apps.",
        "key_responsibilities": ["Develop UI in React", "Build APIs in FastAPI"],
        "summary_text": "Extracted summary."
    }
    contact_data = {
        "original_job_url": "https://testventures.com/jobs/1",
        "application_url": "https://testventures.com/apply/1",
        "verification_status": "format_validated"
    }

    job = test_repo.save_job_record(job_data, summary_data, contact_data)
    assert job.job_id == "test_job_100"

    fetched = test_repo.get_job_by_id("test_job_100")
    assert fetched is not None
    assert fetched.company_name == "Test Ventures"
    assert fetched.summary is not None
    assert fetched.contact is not None
    assert fetched.contact.application_url == "https://testventures.com/apply/1"


def test_record_assessment_attempt_updates_user_skill(test_repo):
    user = test_repo.get_or_create_user(username="candidate_assessment")
    attempt = test_repo.record_assessment_attempt(
        user_id=user.id,
        skill_name="Python",
        score=100.0,
        max_score=100.0,
        passed=True,
        proficiency_level=4,
        feedback="Perfect score on concurrency and memory models."
    )
    assert attempt.passed is True
    assert attempt.proficiency_awarded == 4

    # Verify user skill updated to assessed
    skills = test_repo.get_user_skills(user.id)
    python_skill = next((s for s in skills if s["skill_name"] == "Python"), None)
    assert python_skill is not None
    assert python_skill["skill_source"] == "assessed"
    assert python_skill["proficiency_level"] == 4
