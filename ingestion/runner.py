"""
Ingestion Runner and Source Orchestrator.
Executes ingestion across enabled connectors, tracks run telemetry,
handles connector failures independently, and persists results.
"""

from datetime import datetime
import time
from typing import Any, Dict, List, Optional
import logging

from database.repository import repo
from connectors.base import BaseJobConnector
from connectors.kaggle_csv import KaggleCSVConnector
from connectors.greenhouse import GreenhouseConnector
from connectors.lever import LeverConnector
from connectors.adzuna import AdzunaConnector
from connectors.manual import ManualImportConnector
from ingestion.normalize import normalize_job_dict
from ingestion.deduplicate import DeduplicationIndex, filter_duplicates
from processing.summarize import generate_job_summary
from processing.extract_contacts import extract_contacts_from_text_and_urls

logger = logging.getLogger(__name__)


class IngestionRunner:
    def __init__(self):
        self.connectors: Dict[str, BaseJobConnector] = {
            "greenhouse": GreenhouseConnector(),
            "lever": LeverConnector(),
            "adzuna": AdzunaConnector(),
            "manual": ManualImportConnector(),
            "kaggle_csv": KaggleCSVConnector()
        }

    def get_connector(self, name: str) -> Optional[BaseJobConnector]:
        return self.connectors.get(name)

    def run_connector(self, source_name: str, limit: int = 50, custom_connector: Optional[BaseJobConnector] = None) -> Dict[str, Any]:
        """
        Executes a single connector ingestion run with detailed telemetry and error isolation.
        """
        start_time = time.time()
        connector = custom_connector or self.connectors.get(source_name)

        if not connector:
            return {
                "source": source_name,
                "status": "failed",
                "fetched": 0,
                "accepted": 0,
                "duplicates": 0,
                "errors": 1,
                "duration": 0.0,
                "message": f"Connector '{source_name}' not found."
            }

        logs: List[str] = [f"Starting ingestion run for {source_name} at {datetime.utcnow().isoformat()}"]
        fetched_count = 0
        accepted_count = 0
        dup_count = 0
        error_count = 0

        try:
            # Fetch raw records
            raw_records = connector.fetch_jobs(limit=limit)
            fetched_count = len(raw_records)
            logs.append(f"Fetched {fetched_count} raw records from {source_name}.")

            if fetched_count == 0:
                logs.append("No records returned from source.")
                status = "completed"
            else:
                existing_ids, existing_hashes = repo.get_existing_hashes_and_ids()
                dedup_index = DeduplicationIndex(existing_ids, existing_hashes)

                for raw in raw_records:
                    try:
                        norm = normalize_job_dict(raw, source=source_name)
                        if not norm:
                            error_count += 1
                            logs.append(f"Rejected malformed record from {source_name}: missing required title/company/description.")
                            continue

                        is_dup, reason = dedup_index.is_duplicate(norm)
                        if is_dup:
                            dup_count += 1
                            logs.append(f"Duplicate detected: {reason}")
                            continue

                        dedup_index.register(norm)

                        # Summarize and extract contacts
                        summary_dict = generate_job_summary(
                            title=norm.job_title,
                            description=norm.job_description,
                            required_skills=norm.required_skills,
                            preferred_skills=norm.preferred_skills,
                            location=norm.location,
                            workplace_type=norm.workplace_type
                        )
                        contacts_dict = extract_contacts_from_text_and_urls(
                            description=norm.job_description,
                            original_job_url=norm.original_job_url,
                            api_apply_url=norm.application_url,
                            api_company_url=norm.company_website,
                            company_name=norm.company_name
                        )

                        repo.save_job_record(
                            job_data=norm.model_dump(),
                            summary_data=summary_dict,
                            contact_data=contacts_dict
                        )
                        accepted_count += 1

                    except Exception as inner_e:
                        error_count += 1
                        logs.append(f"Error processing record: {str(inner_e)}")

                status = "completed" if error_count == 0 else "partial"

        except Exception as e:
            error_count += 1
            status = "failed"
            logs.append(f"Fatal error running connector {source_name}: {str(e)}")

        duration = time.time() - start_time
        log_text = "\n".join(logs)

        # Record ingestion run in database
        repo.record_ingestion_run(
            source_name=source_name,
            status=status,
            records_fetched=fetched_count,
            records_accepted=accepted_count,
            duplicates_found=dup_count,
            errors_count=error_count,
            duration_seconds=duration,
            log_messages=log_text
        )

        return {
            "source": source_name,
            "status": status,
            "fetched": fetched_count,
            "accepted": accepted_count,
            "duplicates": dup_count,
            "errors": error_count,
            "duration": round(duration, 2),
            "log": log_text
        }

    def run_all_enabled(self, limit_per_source: int = 25) -> List[Dict[str, Any]]:
        """
        Runs all enabled connectors sequentially. Failure in one does not halt the others.
        """
        results = []
        for name, conn in self.connectors.items():
            if name == "manual":
                continue  # Manual is on-demand
            if conn.is_enabled:
                res = self.run_connector(name, limit=limit_per_source)
                results.append(res)
        return results


# Global ingestion runner instance
runner = IngestionRunner()
