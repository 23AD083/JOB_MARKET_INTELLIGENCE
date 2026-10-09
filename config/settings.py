"""
Application Configuration and Settings.
Supports local SQLite, external PostgreSQL via DATABASE_URL, and safe SSRF network settings.
"""

import os
from typing import Optional
from pydantic import BaseModel, Field


class Settings(BaseModel):
    # App Information
    app_name: str = "Job Intelligence Pipeline"
    app_version: str = "1.0.0"
    debug: bool = Field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")

    # Database
    database_url: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./data/jobs.db")
    )

    # Ingestion & Connectors
    request_timeout_seconds: int = 15
    max_retries: int = 3
    retry_backoff_factor: float = 0.5
    user_agent: str = "JobIntelligencePipeline/1.0 (+https://huggingface.co/spaces)"
    
    # Adzuna API
    adzuna_app_id: Optional[str] = Field(default_factory=lambda: os.getenv("ADZUNA_APP_ID"))
    adzuna_app_key: Optional[str] = Field(default_factory=lambda: os.getenv("ADZUNA_APP_KEY"))
    adzuna_country: str = Field(default_factory=lambda: os.getenv("ADZUNA_COUNTRY", "us"))

    # Server & Port for Gradio / HF Spaces
    server_name: str = Field(default_factory=lambda: os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"))
    server_port: int = Field(default_factory=lambda: int(os.getenv("GRADIO_SERVER_PORT", "7860")))

    # Security & SSRF Protection
    blocked_hosts: list[str] = [
        "localhost", "127.0.0.1", "0.0.0.0", "::1",
        "169.254.169.254", # AWS metadata
        "metadata.google.internal" # GCP metadata
    ]

    # Matching Weights (default heuristics, configurable in UI/Settings)
    weight_skill: float = 0.60
    weight_role: float = 0.20
    weight_eligibility: float = 0.10
    weight_preference: float = 0.10

    # Matching Thresholds
    threshold_strong: float = 80.0
    threshold_potential: float = 55.0

    def get_masked_adzuna_key(self) -> str:
        if not self.adzuna_app_key:
            return "Not configured"
        if len(self.adzuna_app_key) <= 4:
            return "****"
        return f"****{self.adzuna_app_key[-4:]}"

    def get_masked_db_url(self) -> str:
        if not self.database_url:
            return ""
        if "@" in self.database_url:
            # Mask password in URI
            prefix, rest = self.database_url.split("@", 1)
            scheme_user = prefix.split(":", 2)
            if len(scheme_user) >= 3:
                return f"{scheme_user[0]}:{scheme_user[1]}:****@{rest}"
        return self.database_url


# Global settings instance
settings = Settings()
