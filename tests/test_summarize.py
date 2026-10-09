"""
Unit tests for rule-based non-LLM job summarization.
"""

import pytest
from processing.summarize import generate_job_summary, extract_role_overview, extract_responsibilities


def test_extractive_summary_generation():
    desc = """
    About Us: Acme Corp powers real-time enterprise supply chains.

    Role Overview:
    We are seeking a Lead Data Engineer to design high-throughput ETL data pipelines. You will collaborate closely with machine learning teams to structure analytical datasets.

    Key Responsibilities:
    • Architect scalable streaming pipelines using Apache Kafka.
    • Design data models in Snowflake data warehouse.
    • Lead daily data quality monitoring and query optimization.

    Qualifications:
    • Bachelor's degree in Computer Science or related technical discipline.
    • 5+ years of professional data engineering experience.
    • Remote eligible across the United States.
    • Application deadline: December 31, 2026.
    """

    summary = generate_job_summary(
        title="Lead Data Engineer",
        description=desc,
        required_skills=["Python", "SQL", "Apache Spark"],
        preferred_skills=["Snowflake"],
        location="Remote",
        workplace_type="remote"
    )

    assert "Lead Data Engineer" in summary["role_overview"] or "high-throughput" in summary["role_overview"]
    assert len(summary["key_responsibilities"]) >= 2
    assert "Bachelor" in summary["education_requirements"]
    assert "5+" in summary["experience_requirements"]
    assert "December 31, 2026" in summary["application_deadline"]
    assert "Remote" in summary["location_work_mode"]


def test_not_specified_fallback_without_guessing():
    # Sparse description with missing fields
    desc = "We have an open position for a developer. Build features for our app."
    summary = generate_job_summary(
        title="Developer",
        description=desc,
        required_skills=[],
        preferred_skills=[]
    )

    assert summary["education_requirements"] == "Not specified"
    assert summary["experience_requirements"] == "Not specified"
    assert summary["application_deadline"] == "Not specified"
