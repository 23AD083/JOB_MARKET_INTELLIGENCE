"""
Unit tests for URL safety (SSRF prevention) and recruitment contact extraction without fabrications.
"""

import pytest
from config.security import is_safe_url
from processing.extract_contacts import (
    extract_contacts_from_text_and_urls,
    is_valid_recruiter_email,
    is_valid_phone
)


def test_ssrf_url_blocking():
    # Localhost and loopback
    assert not is_safe_url("http://localhost:8080/internal")
    assert not is_safe_url("http://127.0.0.1:5000/api")
    assert not is_safe_url("http://0.0.0.0/")
    assert not is_safe_url("http://[::1]/")

    # Private IP ranges (RFC 1918)
    assert not is_safe_url("http://10.0.0.1/admin")
    assert not is_safe_url("http://192.168.1.100/status")
    assert not is_safe_url("http://172.16.0.5/")

    # Cloud metadata services
    assert not is_safe_url("http://169.254.169.254/latest/meta-data/")
    assert not is_safe_url("http://metadata.google.internal/computeMetadata/v1/")

    # Valid external public URLs
    assert is_safe_url("https://www.google.com/careers")
    assert is_safe_url("https://boards-api.greenhouse.io/v1/boards/canonical/jobs")
    assert is_safe_url("https://company.example.com/jobs/123")


def test_contact_extraction_valid_email_and_phone():
    desc = """
    About the role: Software engineer position.
    For questions, reach out to our recruiter Jane Doe at jane.doe@techfirm.com or call +1-415-555-0199.
    LinkedIn: https://linkedin.com/in/janedoe-talent
    """
    contacts = extract_contacts_from_text_and_urls(
        description=desc,
        original_job_url="https://techfirm.com/careers/123",
        api_apply_url="https://techfirm.com/apply/123"
    )

    assert contacts["recruiter_email"] == "jane.doe@techfirm.com"
    assert contacts["recruiter_phone"] == "+1-415-555-0199"
    assert contacts["recruiter_profile_url"] == "https://linkedin.com/in/janedoe-talent"
    assert contacts["recruiter_name"] == "Jane Doe"
    assert contacts["verification_status"] == "format_validated"


def test_contact_extraction_no_hallucinations():
    # Description without contact details should NOT invent any
    desc = "We are seeking a developer. Apply on our website. Competitive salary and benefits."
    contacts = extract_contacts_from_text_and_urls(description=desc)

    assert contacts["recruiter_name"] is None
    assert contacts["recruiter_email"] is None
    assert contacts["recruiter_phone"] is None
    assert contacts["recruiter_profile_url"] is None
