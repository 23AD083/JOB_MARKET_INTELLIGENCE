"""
Unit tests for duplicate detection and deduplication.
"""

import pytest
from ingestion.deduplicate import DeduplicationIndex, filter_duplicates
from ingestion.validate import JobRecordSchema


def create_dummy_job(job_id: str, source: str, source_job_id: str, company: str, title: str, content_hash: str) -> JobRecordSchema:
    return JobRecordSchema(
        job_id=job_id,
        source=source,
        source_job_id=source_job_id,
        job_title=title,
        company_name=company,
        job_description="Sample job description with plenty of characters to pass validation.",
        content_hash=content_hash
    )


def test_primary_deduplication():
    idx = DeduplicationIndex()
    j1 = create_dummy_job("job_1", "greenhouse", "gh-100", "Acme", "Data Engineer", "hash_aaa111222333444555")
    
    is_dup, _ = idx.is_duplicate(j1)
    assert not is_dup
    idx.register(j1)

    # Same source and source_job_id
    j2 = create_dummy_job("job_2", "greenhouse", "gh-100", "Acme", "Data Engineer Different Title", "hash_different_12345")
    is_dup, reason = idx.is_duplicate(j2)
    assert is_dup
    assert "Primary duplicate" in reason


def test_secondary_hash_deduplication():
    idx = DeduplicationIndex()
    j1 = create_dummy_job("job_1", "source_a", "id_1", "Acme", "Data Engineer", "hash_identical111222333")
    idx.register(j1)

    # Different source and source_job_id, but identical content hash
    j2 = create_dummy_job("job_2", "source_b", "id_99", "Acme", "Data Engineer", "hash_identical111222333")
    is_dup, reason = idx.is_duplicate(j2)
    assert is_dup
    assert "Secondary duplicate" in reason


def test_distinct_jobs_not_deduplicated():
    idx = DeduplicationIndex()
    j1 = create_dummy_job("job_1", "greenhouse", "gh-1", "Company A", "Software Engineer", "hash_1111111111111111")
    j2 = create_dummy_job("job_2", "greenhouse", "gh-2", "Company B", "Software Engineer", "hash_2222222222222222")

    idx.register(j1)
    is_dup, _ = idx.is_duplicate(j2)
    assert not is_dup
