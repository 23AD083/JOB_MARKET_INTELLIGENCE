"""
Data Validation and Job Schema Definitions.
Ensures strict validation of required fields, URL format and safety (SSRF prevention),
and provides validation error tracking.
"""

from datetime import datetime
import ipaddress
import re
from typing import List, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator
from config.security import is_safe_url


class JobRecordSchema(BaseModel):
    """
    Pydantic schema representing the standardized job record.
    All optional fields are nullable.
    """
    job_id: str = Field(..., description="Unique deterministic identifier")
    source: str = Field(..., min_length=1, description="Origin connector name")
    source_job_id: Optional[str] = None
    job_title: str = Field(..., min_length=1, description="Job title")
    company_name: str = Field(..., min_length=1, description="Company name")
    job_description: str = Field(..., min_length=10, description="Full job description text")
    location: Optional[str] = None
    country: Optional[str] = None
    employment_type: Optional[str] = None
    workplace_type: Optional[str] = Field(None, description="remote, hybrid, or onsite")
    experience_level: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    education_requirements: Optional[str] = None
    original_job_url: Optional[str] = None
    application_url: Optional[str] = None
    company_website: Optional[str] = None
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    recruiter_phone: Optional[str] = None
    recruiter_profile_url: Optional[str] = None
    posted_at: Optional[datetime] = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    last_verified_at: Optional[datetime] = None
    extraction_source: Optional[str] = None
    verification_status: str = Field(default="unverified")
    content_hash: str = Field(..., min_length=16, description="SHA-256 content hash")
    category: Optional[str] = "Other"
    category_confidence: Optional[float] = 0.0

    @field_validator("workplace_type")
    @classmethod
    def validate_workplace_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_norm = v.strip().lower()
        if v_norm in ("remote", "hybrid", "onsite"):
            return v_norm
        if "remote" in v_norm:
            return "remote"
        if "hybrid" in v_norm:
            return "hybrid"
        if "onsite" in v_norm or "on-site" in v_norm or "in-office" in v_norm:
            return "onsite"
        return "onsite"

    @field_validator("original_job_url", "application_url", "company_website", "recruiter_profile_url")
    @classmethod
    def validate_urls(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v = v.strip()
        if not v:
            return None
        if not (v.startswith("http://") or v.startswith("https://")):
            # If plain domain provided e.g. company.com
            if re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", v):
                v = "https://" + v
            else:
                return None
        if not is_safe_url(v):
            return None
        return v

    @field_validator("recruiter_email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v = v.strip().lower()
        # Strict email regex to prevent malformed addresses
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if re.match(email_regex, v) and not any(v.endswith(b) for b in [".example", ".test", ".invalid", "localhost"]):
            return v
        return None

    @model_validator(mode="after")
    def validate_salaries(self) -> "JobRecordSchema":
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min > self.salary_max:
                # Swap if min > max
                self.salary_min, self.salary_max = self.salary_max, self.salary_min
        return self


class ValidationResult(BaseModel):
    is_valid: bool
    record: Optional[JobRecordSchema] = None
    errors: List[str] = Field(default_factory=list)


def validate_raw_job_dict(raw: dict) -> ValidationResult:
    """
    Validates a dictionary against the JobRecordSchema and captures detailed reasons for rejection.
    """
    try:
        validated = JobRecordSchema(**raw)
        return ValidationResult(is_valid=True, record=validated, errors=[])
    except Exception as e:
        return ValidationResult(is_valid=False, record=None, errors=[str(e)])
