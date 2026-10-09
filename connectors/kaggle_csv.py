"""
Kaggle / Local CSV Job Ingestion Connector.
Supports uploaded CSV datasets with varied headers and encodings.
"""

import io
import os
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import logging

from connectors.base import BaseJobConnector

logger = logging.getLogger(__name__)


class KaggleCSVConnector(BaseJobConnector):
    """
    Connector for CSV datasets uploaded by the user or pre-seeded sample data.
    """
    def __init__(self, file_path_or_bytes: Optional[Any] = None, is_enabled: bool = True):
        super().__init__(name="kaggle_csv", is_enabled=is_enabled)
        self.file_source = file_path_or_bytes

    def set_file_source(self, file_source: Any):
        self.file_source = file_source

    def test_connection(self) -> Tuple[bool, str]:
        if not self.file_source:
            return (False, "No CSV file uploaded or configured.")
        try:
            df = self._read_df()
            if df.empty:
                return (False, "Uploaded CSV file is empty.")
            return (True, f"CSV parsed successfully: {len(df)} rows detected.")
        except Exception as e:
            return (False, f"CSV parsing error: {str(e)}")

    def _read_df(self) -> pd.DataFrame:
        """Reads CSV with fallback encodings."""
        if isinstance(self.file_source, pd.DataFrame):
            return self.file_source
        
        # If string path
        if isinstance(self.file_source, str):
            if not os.path.exists(self.file_source):
                raise FileNotFoundError(f"File not found: {self.file_source}")
            for enc in ["utf-8", "latin1", "cp1252"]:
                try:
                    return pd.read_csv(self.file_source, encoding=enc)
                except UnicodeDecodeError:
                    continue
            return pd.read_csv(self.file_source, errors="replace")

        # If bytes or buffer
        if hasattr(self.file_source, "read"):
            content = self.file_source.read()
            if isinstance(content, str):
                content = content.encode("utf-8")
            for enc in ["utf-8", "latin1", "cp1252"]:
                try:
                    return pd.read_csv(io.BytesIO(content), encoding=enc)
                except UnicodeDecodeError:
                    continue
            return pd.read_csv(io.BytesIO(content), errors="replace")

        return pd.DataFrame()

    def fetch_jobs(self, limit: int = 200) -> List[Dict[str, Any]]:
        if not self.is_enabled or not self.file_source:
            return []

        try:
            df = self._read_df()
            if df.empty:
                return []

            # Normalize column names to lowercase stripped
            col_map = {c: str(c).strip().lower().replace(" ", "_") for c in df.columns}
            df_norm = df.rename(columns=col_map)

            # Map common Kaggle / external CSV columns
            title_col = self._find_column(df_norm, ["job_title", "title", "position", "role_title"])
            company_col = self._find_column(df_norm, ["company_name", "company", "employer"])
            desc_col = self._find_column(df_norm, ["job_description", "description", "job_details", "summary", "text"])
            loc_col = self._find_column(df_norm, ["location", "city", "job_location"])
            url_col = self._find_column(df_norm, ["original_job_url", "url", "job_url", "link"])
            apply_col = self._find_column(df_norm, ["application_url", "apply_url", "apply_link"])
            salary_col = self._find_column(df_norm, ["salary", "salary_estimate", "compensation"])
            salary_min_col = self._find_column(df_norm, ["salary_min", "min_salary"])
            salary_max_col = self._find_column(df_norm, ["salary_max", "max_salary"])
            id_col = self._find_column(df_norm, ["source_job_id", "id", "job_id"])

            records: List[Dict[str, Any]] = []
            for _, row in df_norm.head(limit).iterrows():
                title = str(row.get(title_col, "")).strip() if title_col else ""
                company = str(row.get(company_col, "")).strip() if company_col else ""
                desc = str(row.get(desc_col, "")).strip() if desc_col else ""

                if not title or not company or len(desc) < 5:
                    continue

                rec = {
                    "source": "kaggle_csv",
                    "source_job_id": str(row.get(id_col, "")) if id_col and pd.notna(row.get(id_col)) else None,
                    "job_title": title,
                    "company_name": company,
                    "job_description": desc,
                    "location": str(row.get(loc_col, "")).strip() if loc_col and pd.notna(row.get(loc_col)) else None,
                    "original_job_url": str(row.get(url_col, "")).strip() if url_col and pd.notna(row.get(url_col)) else None,
                    "application_url": str(row.get(apply_col, "")).strip() if apply_col and pd.notna(row.get(apply_col)) else None,
                    "salary": str(row.get(salary_col, "")).strip() if salary_col and pd.notna(row.get(salary_col)) else None,
                    "salary_min": float(row.get(salary_min_col)) if salary_min_col and pd.notna(row.get(salary_min_col)) else None,
                    "salary_max": float(row.get(salary_max_col)) if salary_max_col and pd.notna(row.get(salary_max_col)) else None,
                }
                records.append(rec)

            return records
        except Exception as e:
            logger.error(f"Error fetching from Kaggle CSV: {e}")
            return []

    def _find_column(self, df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        for cand in candidates:
            if cand in df.columns:
                return cand
        return None
