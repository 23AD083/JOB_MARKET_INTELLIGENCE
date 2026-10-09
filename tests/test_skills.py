"""
Unit tests for skill taxonomy, alias normalization, and false-positive prevention.
"""

import pytest
from processing.skills_taxonomy import (
    get_canonical_skill_name,
    SKILLS_TAXONOMY,
    get_skills_by_category
)
from processing.extract_skills import extract_skills_from_job, match_skills_in_text


def test_alias_normalization():
    assert get_canonical_skill_name("postgres") == "PostgreSQL"
    assert get_canonical_skill_name("pgsql") == "PostgreSQL"
    assert get_canonical_skill_name("k8s") == "Kubernetes"
    assert get_canonical_skill_name("sklearn") == "scikit-learn"
    assert get_canonical_skill_name("powerbi") == "Power BI"
    assert get_canonical_skill_name("pyspark") == "Apache Spark"


def test_avoid_false_positive_single_letter_r():
    # Ordinary English sentences containing 'r' or 'R' should NOT trigger R programming
    text_unrelated = "Our company values our employees and their respective career growth in R&D."
    skills = match_skills_in_text(text_unrelated)
    assert "R" not in skills

    # Explicit R programming mention should match
    text_r_prog = "Must have 3 years of experience in R programming and statistical modeling."
    skills_prog = match_skills_in_text(text_r_prog)
    assert "R" in skills_prog


def test_avoid_false_positive_go():
    # Ordinary verb 'go'
    text_unrelated = "We want candidates who will go above and beyond."
    skills = match_skills_in_text(text_unrelated)
    assert "Golang" not in skills

    # Golang programming
    text_golang = "Building microservices in Golang with Docker."
    skills_go = match_skills_in_text(text_golang)
    assert "Golang" in skills_go


def test_required_vs_preferred_skills_separation():
    desc = """
    Role Overview: Backend engineer building platform services.
    
    Required Skills:
    • 3+ years experience with Python and SQL.
    • Solid foundation in Docker and REST APIs.
    
    Nice to Have:
    • Familiarity with Kubernetes and Terraform.
    • Experience with Apache Spark.
    """
    res = extract_skills_from_job("Software Engineer", desc)
    
    assert "Python" in res["required_skills"]
    assert "SQL" in res["required_skills"]
    assert "Docker" in res["required_skills"]
    assert "Kubernetes" in res["preferred_skills"]
    assert "Terraform" in res["preferred_skills"]
    assert "Kubernetes" not in res["required_skills"]
