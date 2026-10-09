"""
Unit tests for explainable matching engine and score weights.
"""

import pytest
from matching.score import calculate_job_match
from ingestion.validate import JobRecordSchema


def test_matching_score_calculation():
    user_prof = {
        "user_id": "u-123",
        "years_of_experience": 4.0,
        "preferred_roles": ["Software Development"],
        "preferred_locations": ["Remote"],
        "workplace_preference": "remote",
        "min_salary": 90000.0
    }
    user_skills = [
        {"skill_name": "Python", "proficiency_level": 3, "skill_source": "assessed"},
        {"skill_name": "FastAPI", "proficiency_level": 3, "skill_source": "assessed"},
        {"skill_name": "SQL", "proficiency_level": 2, "skill_source": "declared"}
    ]

    job = JobRecordSchema(
        job_id="job-99",
        source="test",
        job_title="Senior Python Backend Developer",
        company_name="FinTech Corp",
        job_description="Develop backend APIs in Python and FastAPI with SQL. AWS preferred.",
        workplace_type="remote",
        location="Remote",
        experience_level="mid",
        category="Software Development",
        salary_min=110000.0,
        salary_max=140000.0,
        required_skills=["Python", "FastAPI", "SQL"],
        preferred_skills=["AWS"],
        content_hash="dummyhash111222333444555"
    )

    res = calculate_job_match(user_prof, user_skills, job)
    
    assert res["overall_score"] >= 80.0
    assert res["match_category"] == "Strong Match"
    assert "Python" in res["matched_skills"]
    assert "FastAPI" in res["matched_skills"]
    assert "SQL" in res["matched_skills"]
    assert "AWS" in res["missing_preferred_skills"]
    assert res["role_score"] == 100.0
    assert "Explanation" in res or len(res["explanation"]) > 20


def test_missing_skills_identification():
    user_prof = {"user_id": "u-1", "years_of_experience": 1.0, "preferred_roles": []}
    user_skills = [{"skill_name": "Python", "proficiency_level": 1, "skill_source": "declared"}]

    job = JobRecordSchema(
        job_id="job-1",
        source="test",
        job_title="Data Engineer",
        company_name="Big Data Co",
        job_description="Need Spark, Airflow, and Kafka.",
        category="Data Engineering",
        required_skills=["Apache Spark", "Airflow", "Kafka"],
        preferred_skills=["Snowflake"],
        content_hash="dummyhash222333444555"
    )

    res = calculate_job_match(user_prof, user_skills, job)
    assert "Apache Spark" in res["missing_required_skills"]
    assert "Airflow" in res["missing_required_skills"]
    assert "Kafka" in res["missing_required_skills"]
    assert res["overall_score"] < 55.0
    assert res["match_category"] == "Explore"
