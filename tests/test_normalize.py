"""
Unit tests for data normalization and schema validation.
"""

import pytest
from datetime import datetime
from ingestion.normalize import (
    clean_html_text,
    parse_salary_string,
    normalize_workplace_type,
    normalize_experience_level,
    compute_content_hash,
    normalize_job_dict
)
from ingestion.validate import is_safe_url, validate_raw_job_dict


def test_clean_html_text():
    html_input = "<p>Join our team!<br>We need a <b>Python</b> engineer.</p><ul><li>Build APIs</li><li>Deploy Docker</li></ul>"
    cleaned = clean_html_text(html_input)
    assert "Join our team!" in cleaned
    assert "Build APIs" in cleaned
    assert "<p>" not in cleaned
    assert "<ul>" not in cleaned


def test_parse_salary_string():
    # Range with commas
    s_min, s_max, curr = parse_salary_string("$120,000 - $160,000 / year")
    assert s_min == 120000.0
    assert s_max == 160000.0
    assert curr == "USD"

    # Single number with 'k'
    s_min, s_max, curr = parse_salary_string("£75k")
    assert s_min == 75000.0
    assert s_max == 75000.0
    assert curr == "GBP"

    # None / empty
    assert parse_salary_string(None) == (None, None, None)
    assert parse_salary_string("") == (None, None, None)


def test_normalize_workplace_type():
    assert normalize_workplace_type("Remote") == "remote"
    assert normalize_workplace_type("Hybrid work") == "hybrid"
    assert normalize_workplace_type("On-site in office") == "onsite"
    assert normalize_workplace_type(None, "This role is 100% remote") == "remote"


def test_normalize_experience_level():
    assert normalize_experience_level("Senior", "Software Engineer", "") == "senior"
    assert normalize_experience_level(None, "Junior Data Analyst", "") == "entry"
    assert normalize_experience_level(None, "Lead Architect", "") == "lead"


def test_compute_content_hash_consistency():
    h1 = compute_content_hash("Google", "Software Engineer", "Mountain View", "Building search infrastructure.")
    h2 = compute_content_hash("google", "software engineer", "mountain view", "building search infrastructure.")
    assert h1 == h2
    assert len(h1) == 64


def test_normalize_job_dict_valid():
    raw = {
        "job_title": "Backend Python Developer",
        "company_name": "Tech Corp",
        "job_description": "We are seeking a Python developer to build REST APIs using FastAPI and PostgreSQL. 3+ years experience required.",
        "location": "Austin, TX",
        "salary": "$110,000 - $130,000"
    }
    norm = normalize_job_dict(raw, source="test_source")
    assert norm is not None
    assert norm.job_title == "Backend Python Developer"
    assert norm.company_name == "Tech Corp"
    assert "Python" in norm.required_skills
    assert "FastAPI" in norm.required_skills
    assert norm.salary_min == 110000.0
    assert norm.salary_max == 130000.0


def test_normalize_job_dict_reject_missing_fields():
    # Missing description
    raw = {"job_title": "Developer", "company_name": "Tech Corp", "job_description": ""}
    assert normalize_job_dict(raw, source="test") is None

    # Missing title
    raw = {"job_title": "", "company_name": "Tech Corp", "job_description": "A long job description with enough characters."}
    assert normalize_job_dict(raw, source="test") is None
