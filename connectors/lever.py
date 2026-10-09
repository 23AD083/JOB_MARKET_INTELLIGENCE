"""
Lever Public Postings API Connector.
Fetches public postings for configured participating employers via Lever API.
Endpoint: https://api.lever.co/v0/postings/{company_name}?mode=json
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import requests
import logging

from connectors.base import BaseJobConnector
from config.settings import settings

logger = logging.getLogger(__name__)


class LeverConnector(BaseJobConnector):
    """
    Connects to public Lever job postings endpoints for configured employers.
    """
    def __init__(self, company_slugs: Optional[List[str]] = None, is_enabled: bool = True):
        super().__init__(name="lever", is_enabled=is_enabled)
        # Default employers with public Lever endpoints
        self.company_slugs = company_slugs or ["coursera", "atlassian"]

    def set_company_slugs(self, slugs: List[str]):
        self.company_slugs = [s.strip().lower() for s in slugs if s.strip()]

    def test_connection(self) -> Tuple[bool, str]:
        if not self.company_slugs:
            return (False, "No Lever company slugs configured.")
        slug = self.company_slugs[0]
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        try:
            resp = requests.get(url, timeout=settings.request_timeout_seconds, headers={"User-Agent": settings.user_agent})
            if resp.status_code == 200:
                data = resp.json()
                count = len(data) if isinstance(data, list) else 0
                return (True, f"Connected to Lever employer '{slug}'. Found {count} public postings.")
            return (False, f"Lever responded with HTTP {resp.status_code} for employer '{slug}'.")
        except Exception as e:
            return (False, f"Failed to connect to Lever: {str(e)}")

    def fetch_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.is_enabled or not self.company_slugs:
            return []

        all_records: List[Dict[str, Any]] = []
        headers = {"User-Agent": settings.user_agent}

        for slug in self.company_slugs:
            if len(all_records) >= limit:
                break
            url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
            try:
                resp = requests.get(url, headers=headers, timeout=settings.request_timeout_seconds)
                if resp.status_code != 200:
                    logger.warning(f"Lever endpoint for '{slug}' returned HTTP {resp.status_code}")
                    continue

                postings = resp.json()
                if not isinstance(postings, list):
                    continue

                for post in postings:
                    if len(all_records) >= limit:
                        break

                    job_id = str(post.get("id"))
                    title = post.get("text", "")
                    
                    # Full description components
                    desc_parts = []
                    if post.get("descriptionPlain"):
                        desc_parts.append(post.get("descriptionPlain"))
                    elif post.get("description"):
                        desc_parts.append(post.get("description"))

                    # Lists / requirements in Lever
                    lists = post.get("lists", [])
                    if isinstance(lists, list):
                        for lst in lists:
                            desc_parts.append(f"\n{lst.get('text', '')}:\n{lst.get('content', '')}")

                    full_desc = "\n".join(desc_parts)

                    cats = post.get("categories", {})
                    location = cats.get("location") if isinstance(cats, dict) else None
                    commitment = cats.get("commitment") if isinstance(cats, dict) else "full-time"
                    workplace_type = post.get("workplaceType")  # 'remote', 'hybrid', 'unspecified'

                    hosted_url = post.get("hostedUrl")
                    apply_url = post.get("applyUrl")

                    # Posted timestamp
                    created_at_ms = post.get("createdAt")
                    posted_dt = None
                    if created_at_ms:
                        try:
                            posted_dt = datetime.utcfromtimestamp(created_at_ms / 1000.0).isoformat()
                        except Exception:
                            pass

                    rec = {
                        "source": "lever",
                        "source_job_id": job_id,
                        "job_title": title,
                        "company_name": slug.capitalize(),
                        "job_description": full_desc,
                        "location": location,
                        "employment_type": commitment,
                        "workplace_type": workplace_type,
                        "original_job_url": hosted_url,
                        "application_url": apply_url,
                        "company_website": f"https://www.{slug}.com",
                        "posted_at": posted_dt
                    }
                    all_records.append(rec)

            except Exception as e:
                logger.error(f"Error fetching from Lever for '{slug}': {e}")
                continue

        return all_records
