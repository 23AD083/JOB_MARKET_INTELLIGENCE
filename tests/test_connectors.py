"""
Unit tests for connector error handling and resilience.
"""

import pytest
from connectors.kaggle_csv import KaggleCSVConnector
from connectors.manual import ManualImportConnector
from connectors.greenhouse import GreenhouseConnector
from connectors.lever import LeverConnector
from connectors.adzuna import AdzunaConnector
from ingestion.runner import IngestionRunner


def test_kaggle_csv_empty_file():
    conn = KaggleCSVConnector(file_path_or_bytes="")
    ok, msg = conn.test_connection()
    assert not ok
    assert "No CSV" in msg
    assert conn.fetch_jobs() == []


def test_manual_connector_text_import():
    conn = ManualImportConnector()
    rec = conn.import_from_text(
        title="Solutions Architect",
        company="Cloud Solutions",
        description="Design cloud systems in AWS with Terraform and Kubernetes.",
        location="Remote",
        workplace_type="remote",
        job_url="https://cloudsolutions.example.com/job/1"
    )
    assert rec["job_title"] == "Solutions Architect"
    assert rec["source"] == "manual"
    assert rec["original_job_url"] == "https://cloudsolutions.example.com/job/1"


def test_adzuna_unconfigured_credentials():
    conn = AdzunaConnector(app_id=None, app_key=None)
    ok, msg = conn.test_connection()
    assert not ok
    assert "not configured" in msg
    # fetch_jobs should return empty list gracefully without throwing exception
    assert conn.fetch_jobs() == []


def test_ingestion_runner_fault_isolation():
    runner = IngestionRunner()
    # Running a non-existent connector returns failure dict rather than raising exception
    res = runner.run_connector("invalid_connector_name")
    assert res["status"] == "failed"
    assert res["errors"] == 1
