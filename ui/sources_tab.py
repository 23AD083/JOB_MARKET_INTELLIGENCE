"""
Data Sources Tab Component.
Supports CSV file upload, Greenhouse / Lever board configuration,
Adzuna API credential management, manual test triggers, and telemetry logs.
"""

from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import gradio as gr

from database.repository import repo
from ingestion.runner import runner
from connectors.kaggle_csv import KaggleCSVConnector
from connectors.greenhouse import GreenhouseConnector
from connectors.lever import LeverConnector
from connectors.adzuna import AdzunaConnector
from connectors.manual import ManualImportConnector


def handle_csv_upload_and_ingest(file_obj) -> Tuple[str, pd.DataFrame]:
    """Ingests uploaded Kaggle or custom CSV file."""
    if not file_obj:
        return ("Please upload a CSV file first.", pd.DataFrame())

    try:
        file_path = file_obj.name if hasattr(file_obj, "name") else file_obj
        csv_connector = KaggleCSVConnector(file_path_or_bytes=file_path)
        res = runner.run_connector("kaggle_csv", limit=200, custom_connector=csv_connector)

        status_msg = f"""### **CSV Ingestion Result: {res['status'].upper()}**
• **Records Fetched**: {res['fetched']}
• **Records Accepted**: {res['accepted']}
• **Duplicates Filtered**: {res['duplicates']}
• **Errors**: {res['errors']}
• **Duration**: {res['duration']}s
"""
        recent = repo.get_recent_ingestion_runs(limit=8)
        table_rows = [{
            "Source": r.source_name,
            "Status": r.status,
            "Accepted": r.records_accepted,
            "Duplicates": r.duplicates_found,
            "Errors": r.errors_count,
            "Duration (s)": f"{r.duration_seconds}s",
            "Time": r.started_at.strftime("%H:%M:%S")
        } for r in recent]

        return (status_msg, pd.DataFrame(table_rows))
    except Exception as e:
        return (f"Error uploading CSV: {str(e)}", pd.DataFrame())


def run_manual_source_sync(source_name: str, gh_tokens: str, lever_slugs: str, adzuna_id: str, adzuna_key: str, adzuna_country: str) -> Tuple[str, pd.DataFrame]:
    """Configures connectors and executes manual sync."""
    # Update connectors configurations
    gh_conn: GreenhouseConnector = runner.get_connector("greenhouse")
    if gh_conn and gh_tokens:
        tokens = [t.strip() for t in gh_tokens.split(",") if t.strip()]
        gh_conn.set_board_tokens(tokens)

    lever_conn: LeverConnector = runner.get_connector("lever")
    if lever_conn and lever_slugs:
        slugs = [s.strip() for s in lever_slugs.split(",") if s.strip()]
        lever_conn.set_company_slugs(slugs)

    adzuna_conn: AdzunaConnector = runner.get_connector("adzuna")
    if adzuna_conn and adzuna_id and adzuna_key:
        adzuna_conn.set_credentials(adzuna_id, adzuna_key, adzuna_country)

    if source_name == "All Enabled Sources":
        results = runner.run_all_enabled(limit_per_source=25)
        accepted_total = sum(r["accepted"] for r in results)
        fetched_total = sum(r["fetched"] for r in results)
        msg = f"Synced all enabled sources! Fetched {fetched_total} records, accepted {accepted_total} normalized jobs."
    else:
        res = runner.run_connector(source_name.lower(), limit=30)
        msg = f"Sync for {source_name}: {res['status'].upper()}! Accepted {res['accepted']} records (Duration: {res['duration']}s)."

    recent = repo.get_recent_ingestion_runs(limit=8)
    table_rows = [{
        "Source": r.source_name,
        "Status": r.status,
        "Accepted": r.records_accepted,
        "Duplicates": r.duplicates_found,
        "Errors": r.errors_count,
        "Duration (s)": f"{r.duration_seconds}s",
        "Time": r.started_at.strftime("%H:%M:%S")
    } for r in recent]

    return (msg, pd.DataFrame(table_rows))


def test_source_connection(source_name: str, gh_tokens: str, lever_slugs: str, adzuna_id: str, adzuna_key: str, adzuna_country: str) -> str:
    """Tests connectivity to a specific source without saving jobs."""
    s = source_name.lower()
    if s == "greenhouse":
        conn = GreenhouseConnector(board_tokens=[t.strip() for t in gh_tokens.split(",") if t.strip()])
    elif s == "lever":
        conn = LeverConnector(company_slugs=[s.strip() for s in lever_slugs.split(",") if s.strip()])
    elif s == "adzuna":
        conn = AdzunaConnector(app_id=adzuna_id, app_key=adzuna_key, country=adzuna_country)
    else:
        conn = ManualImportConnector()

    ok, message = conn.test_connection()
    status_icon = "SUCCESS" if ok else "FAILED"
    return f"[{status_icon}] {message}"
