"""
Base Connector Interface for Job Postings Ingestion.
Defines common interface, error handling, rate limiting, and retry policies.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class BaseJobConnector(ABC):
    """
    Abstract base class for all job data sources.
    Enforces common interface and safe failure handling.
    """
    def __init__(self, name: str, is_enabled: bool = True):
        self.name = name
        self.is_enabled = is_enabled

    @abstractmethod
    def fetch_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetches job records from source.
        Returns a list of raw dictionaries prior to normalization.
        Must catch internal network/parsing errors and return partial list rather than crashing.
        """
        pass

    @abstractmethod
    def test_connection(self) -> Tuple[bool, str]:
        """
        Tests if the source endpoint or credentials are functional.
        Returns (is_connected: bool, message: str).
        """
        pass

    def enable(self):
        self.is_enabled = True

    def disable(self):
        self.is_enabled = False
