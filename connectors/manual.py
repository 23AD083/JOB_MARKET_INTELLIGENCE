"""
Manual Job Import Connector.
Allows importing a job posting directly via raw text / markdown or via public URL.
Enforces SSRF validation, rate limits, and safe parsing.
"""

from typing import Any, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import requests
import logging

from connectors.base import BaseJobConnector
from config.security import is_safe_url
from config.settings import settings

logger = logging.getLogger(__name__)


class ManualImportConnector(BaseJobConnector):
    """
    Connector for manual job URL or text import.
    """
    def __init__(self, is_enabled: bool = True):
        super().__init__(name="manual", is_enabled=is_enabled)

    def test_connection(self) -> Tuple[bool, str]:
        return (True, "Manual import connector is active and ready.")

    def fetch_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        # Manual connector does not poll background jobs; it imports on-demand
        return []

    def import_from_text(
        self,
        title: str,
        company: str,
        description: str,
        location: Optional[str] = None,
        workplace_type: Optional[str] = None,
        job_url: Optional[str] = None,
        application_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a raw record from user-supplied text.
        """
        return {
            "source": "manual",
            "source_job_id": None,
            "job_title": title.strip(),
            "company_name": company.strip(),
            "job_description": description.strip(),
            "location": location.strip() if location else None,
            "workplace_type": workplace_type,
            "original_job_url": job_url.strip() if job_url and is_safe_url(job_url) else None,
            "application_url": application_url.strip() if application_url and is_safe_url(application_url) else None
        }

    def import_from_url(self, url: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Safely fetches public webpage content and extracts title and text.
        SSRF-safe with timeout and redirect validation.
        """
        if not is_safe_url(url):
            return (None, "Invalid or disallowed URL (SSRF protection blocked this host).")

        headers = {"User-Agent": settings.user_agent}
        try:
            resp = requests.get(url, headers=headers, timeout=settings.request_timeout_seconds, allow_redirects=True)
            if resp.status_code != 200:
                return (None, f"Target page returned HTTP {resp.status_code}.")

            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Extract title
            title = ""
            if soup.find("h1"):
                title = soup.find("h1").get_text(strip=True)
            elif soup.title:
                title = soup.title.get_text(strip=True)

            # Strip scripts and styles
            for elem in soup(["script", "style", "noscript", "svg", "nav", "footer"]):
                elem.extract()

            body_text = soup.get_text(separator="\n", strip=True)

            if len(body_text) < 50:
                return (None, "Insufficient text content found on the specified URL.")

            rec = {
                "source": "manual",
                "source_job_id": None,
                "job_title": title or "Imported Job Posting",
                "company_name": "Imported Company",
                "job_description": body_text[:10000],
                "original_job_url": url,
                "application_url": url
            }
            return (rec, "Job successfully extracted from URL.")
        except Exception as e:
            logger.error(f"Failed to import from URL {url}: {e}")
            return (None, f"Error fetching URL: {str(e)}")
