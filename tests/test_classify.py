"""
Unit tests for deterministic role classification.
"""

import pytest
from processing.classify import classify_job


def test_classify_data_engineering():
    cat, conf, ev = classify_job(
        title="Senior Data Pipeline Engineer",
        description="Build ETL pipelines using Apache Spark and Airflow with Snowflake warehouse.",
        detected_skills=["ETL", "Apache Spark", "Airflow", "Snowflake"]
    )
    assert cat == "Data Engineering"
    assert conf > 0.5
    assert "ETL" in ev["skill_matches"]


def test_classify_ai_ml():
    cat, conf, ev = classify_job(
        title="Machine Learning Scientist",
        description="Train NLP models and feature engineering pipelines with scikit-learn and PyTorch.",
        detected_skills=["scikit-learn", "PyTorch", "NLP", "feature engineering"]
    )
    assert cat == "Data Science and AI/ML"
    assert conf > 0.5


def test_classify_cloud_devops():
    cat, conf, ev = classify_job(
        title="Cloud DevOps Engineer",
        description="Manage Kubernetes clusters and AWS infrastructure using Terraform.",
        detected_skills=["AWS", "Kubernetes", "Docker", "Terraform"]
    )
    assert cat == "Cloud and DevOps"
    assert conf > 0.5


def test_classify_other_sparse():
    cat, conf, _ = classify_job(
        title="General Operations Associate",
        description="Coordinate office inventory and logistics schedules.",
        detected_skills=[]
    )
    assert cat == "Other"
