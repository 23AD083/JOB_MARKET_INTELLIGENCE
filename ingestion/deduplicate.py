"""
Deduplication and Duplicate Detection Engine.
Performs primary deduplication on (source, source_job_id) and secondary deduplication
on normalized SHA-256 content hashes (company, title, location, description).
Preserves distinct jobs with similar titles.
"""

from typing import Dict, List, Set, Tuple
from ingestion.validate import JobRecordSchema


class DeduplicationIndex:
    """
    In-memory tracking index for existing jobs in database or current batch.
    """
    def __init__(self, existing_source_ids: Set[Tuple[str, str]] = None, existing_hashes: Set[str] = None):
        # Set of (source, source_job_id)
        self.seen_source_ids: Set[Tuple[str, str]] = existing_source_ids or set()
        # Set of content_hash strings
        self.seen_hashes: Set[str] = existing_hashes or set()

    def is_duplicate(self, job: JobRecordSchema) -> Tuple[bool, str]:
        """
        Checks if a job record is a duplicate.
        Returns (is_duplicate: bool, reason: str).
        """
        # Primary check: (source, source_job_id)
        if job.source_job_id:
            key = (job.source, job.source_job_id)
            if key in self.seen_source_ids:
                return (True, f"Primary duplicate: Source '{job.source}' with ID '{job.source_job_id}' already exists.")

        # Secondary check: Normalized content hash (company, title, location, description snippet)
        if job.content_hash in self.seen_hashes:
            return (True, f"Secondary duplicate: Exact content hash match for '{job.company_name} - {job.job_title}'.")

        return (False, "")

    def register(self, job: JobRecordSchema):
        """Registers a non-duplicate job into the index."""
        if job.source_job_id:
            self.seen_source_ids.add((job.source, job.source_job_id))
        self.seen_hashes.add(job.content_hash)


def filter_duplicates(
    jobs: List[JobRecordSchema],
    existing_index: DeduplicationIndex
) -> Tuple[List[JobRecordSchema], List[Tuple[JobRecordSchema, str]]]:
    """
    Filters a list of jobs, separating accepted jobs from duplicates.
    Returns (accepted_jobs, duplicate_jobs_with_reason).
    """
    accepted: List[JobRecordSchema] = []
    duplicates: List[Tuple[JobRecordSchema, str]] = []

    for job in jobs:
        is_dup, reason = existing_index.is_duplicate(job)
        if is_dup:
            duplicates.append((job, reason))
        else:
            existing_index.register(job)
            accepted.append(job)

    return accepted, duplicates
