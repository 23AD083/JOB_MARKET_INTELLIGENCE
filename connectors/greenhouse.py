"""
Greenhouse Public Job Board API Connector.
Fetches public postings for configured participating employers via Greenhouse API.
Endpoint: https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
"""

from typing import Any, Dict, List, Optional, Tuple
import requests
import logging

from connectors.base import BaseJobConnector
from config.settings import settings

logger = logging.getLogger(__name__)


class GreenhouseConnector(BaseJobConnector):
    """
    Connects to public Greenhouse endpoints for configured employers.
    """
    def __init__(self, board_tokens: Optional[List[str]] = None, is_enabled: bool = True):
        super().__init__(name="greenhouse", is_enabled=is_enabled)
        # Default active tech employers with hundreds of live public Greenhouse postings
        self.board_tokens = board_tokens or ["canonical", "cloudflare", "gitlab", "stripe", "figma", "discord", "reddit"]

    def set_board_tokens(self, tokens: List[str]):
        self.board_tokens = [t.strip().lower() for t in tokens if t.strip()]

    def test_connection(self) -> Tuple[bool, str]:
        if not self.board_tokens:
            return (False, "No Greenhouse board tokens configured.")
        
        token = self.board_tokens[0]
        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
        try:
            resp = requests.get(url, timeout=settings.request_timeout_seconds, headers={"User-Agent": settings.user_agent})
            if resp.status_code == 200:
                data = resp.json()
                count = len(data.get("jobs", []))
                return (True, f"Connected to Greenhouse board '{token}'. Found {count} public postings.")
            return (False, f"Greenhouse responded with HTTP {resp.status_code} for board '{token}'.")
        except Exception as e:
            return (False, f"Failed to connect to Greenhouse: {str(e)}")

    def fetch_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.is_enabled or not self.board_tokens:
            return []

        all_records: List[Dict[str, Any]] = []
        headers = {"User-Agent": settings.user_agent}

        for token in self.board_tokens:
            if len(all_records) >= limit:
                break
            url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
            try:
                resp = requests.get(url, headers=headers, timeout=settings.request_timeout_seconds)
                if resp.status_code != 200:
                    logger.warning(f"Greenhouse board '{token}' returned HTTP {resp.status_code}")
                    continue

                data = resp.json()
                jobs_list = data.get("jobs", [])

                for item in jobs_list:
                    if len(all_records) >= limit:
                        break

                    job_id = str(item.get("id"))
                    title = item.get("title", "")
                    content = item.get("content", "")
                    abs_url = item.get("absolute_url")
                    loc = item.get("location", {}).get("name") if isinstance(item.get("location"), dict) else None
                    
                    # Company name from token or employer
                    company_names = {
                        "canonical": "Canonical",
                        "cloudflare": "Cloudflare",
                        "gitlab": "GitLab",
                        "stripe": "Stripe",
                        "figma": "Figma",
                        "discord": "Discord",
                        "reddit": "Reddit",
                        "airtable": "Airtable"
                    }
                    company = company_names.get(token, token.capitalize())

                    rec = {
                        "source": "greenhouse",
                        "source_job_id": job_id,
                        "job_title": title,
                        "company_name": company,
                        "job_description": content,
                        "location": loc,
                        "original_job_url": abs_url,
                        "application_url": f"{abs_url}#app" if abs_url else None,
                        "company_website": f"https://{token}.com",
                        "posted_at": item.get("updated_at")
                    }
                    all_records.append(rec)

            except Exception as e:
                logger.error(f"Error fetching from Greenhouse board '{token}': {e}")
                continue

        return all_records
