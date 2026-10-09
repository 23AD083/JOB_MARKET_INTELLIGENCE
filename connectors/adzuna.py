"""
Adzuna Job Search API Connector.
Fetches jobs when the user supplies valid API credentials (app_id and app_key).
Endpoint: https://api.adzuna.com/v1/api/jobs/{country}/search/1
"""

from typing import Any, Dict, List, Optional, Tuple
import requests
import logging

from connectors.base import BaseJobConnector
from config.settings import settings

logger = logging.getLogger(__name__)


class AdzunaConnector(BaseJobConnector):
    """
    Connects to Adzuna API when valid credentials are provided.
    """
    def __init__(
        self,
        app_id: Optional[str] = None,
        app_key: Optional[str] = None,
        country: str = "us",
        is_enabled: bool = True
    ):
        super().__init__(name="adzuna", is_enabled=is_enabled)
        self.app_id = app_id or settings.adzuna_app_id
        self.app_key = app_key or settings.adzuna_app_key
        self.country = country or settings.adzuna_country

    def set_credentials(self, app_id: str, app_key: str, country: str = "us"):
        self.app_id = app_id.strip() if app_id else None
        self.app_key = app_key.strip() if app_key else None
        self.country = country.strip().lower() if country else "us"

    def test_connection(self) -> Tuple[bool, str]:
        if not self.app_id or not self.app_key:
            return (False, "Adzuna credentials not configured. Please supply App ID and App Key.")

        url = f"https://api.adzuna.com/v1/api/jobs/{self.country}/search/1"
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": 1,
            "what": "developer"
        }
        try:
            resp = requests.get(url, params=params, headers={"User-Agent": settings.user_agent}, timeout=settings.request_timeout_seconds)
            if resp.status_code == 200:
                data = resp.json()
                total = data.get("count", 0)
                return (True, f"Connected to Adzuna. Over {total:,} listings available in country '{self.country}'.")
            elif resp.status_code in (401, 403):
                return (False, "Adzuna authentication failed. Please check App ID and App Key.")
            return (False, f"Adzuna returned HTTP {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            return (False, f"Adzuna connection failed: {str(e)}")

    def fetch_jobs(self, limit: int = 50, query: str = "software OR data OR engineer") -> List[Dict[str, Any]]:
        if not self.is_enabled or not self.app_id or not self.app_key:
            return []

        url = f"https://api.adzuna.com/v1/api/jobs/{self.country}/search/1"
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": min(limit, 50),
            "what": query,
            "content-type": "application/json"
        }
        headers = {"User-Agent": settings.user_agent}

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=settings.request_timeout_seconds)
            if resp.status_code != 200:
                logger.warning(f"Adzuna API returned HTTP {resp.status_code}")
                return []

            data = resp.json()
            results = data.get("results", [])
            records: List[Dict[str, Any]] = []

            for item in results:
                job_id = str(item.get("id"))
                title = item.get("title", "")
                company = item.get("company", {}).get("display_name", "Unknown Company")
                description = item.get("description", "")
                loc_name = item.get("location", {}).get("display_name")
                redirect_url = item.get("redirect_url")
                salary_min = item.get("salary_min")
                salary_max = item.get("salary_max")
                created = item.get("created")

                rec = {
                    "source": "adzuna",
                    "source_job_id": job_id,
                    "job_title": title,
                    "company_name": company,
                    "job_description": description,
                    "location": loc_name,
                    "country": self.country.upper(),
                    "salary_min": float(salary_min) if salary_min is not None else None,
                    "salary_max": float(salary_max) if salary_max is not None else None,
                    "original_job_url": redirect_url,
                    "application_url": redirect_url,
                    "posted_at": created
                }
                records.append(rec)

            return records
        except Exception as e:
            logger.error(f"Error fetching from Adzuna: {e}")
            return []
