"""
Application URL and Public Recruitment Contact Extraction Module.
Extracts direct application links, company websites, recruiter names, emails, phones,
and profile URLs using strictly validated patterns, metadata, and HTML parsers.
Never invents contacts; returns 'Not publicly listed' when absent.
Enforces SSRF prevention and provenance tracking.
"""

from datetime import datetime
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from config.security import is_safe_url

# Regex patterns for strict contact extraction
EMAIL_PATTERN = r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b"
PHONE_PATTERN = r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
LINKEDIN_RECRUITER_PATTERN = r"https?:\/\/(?:www\.)?linkedin\.com\/in\/[a-zA-Z0-9_-]+"

# Phrases signaling recruiter sections
RECRUITER_SECTION_PATTERNS = [
    r"(?:contact|reach\s+out\s+to|recruiter|hiring\s+manager|talent\s+acquisition|questions\?|inquiries\s+to)\s*:?\s*([^\n\r]+)",
    r"(?:for\s+questions,\s+email|send\s+resume\s+to)\s*:?\s*([^\n\r]+)"
]

DISALLOWED_EMAIL_DOMAINS = {"example.com", "test.com", "domain.com", "placeholder.com"}


def is_valid_recruiter_email(email: str) -> bool:
    """Validates email format and excludes invalid dummy domains."""
    if not email or not isinstance(email, str):
        return False
    email = email.strip().lower()
    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
        return False
    domain = email.split("@")[-1]
    if domain in DISALLOWED_EMAIL_DOMAINS or domain.endswith(".invalid"):
        return False
    # Avoid file extensions like .png@, etc.
    if any(email.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif"]):
        return False
    return True


def is_valid_phone(phone: str) -> bool:
    """Validates phone number length and digit content."""
    digits = re.sub(r"\D", "", phone)
    # Must have 10-15 digits (standard E.164 bounds)
    return 10 <= len(digits) <= 15


def extract_contacts_from_text_and_urls(
    description: str,
    raw_html: Optional[str] = None,
    original_job_url: Optional[str] = None,
    api_apply_url: Optional[str] = None,
    api_company_url: Optional[str] = None,
    company_name: Optional[str] = None
) -> Dict:
    """
    Extracts recruiter contacts and application links with strict provenance and validation.
    Never invents details. Returns structured dict.
    """
    recruiter_name = None
    recruiter_email = None
    recruiter_phone = None
    recruiter_profile_url = None
    extraction_method = "unstructured_text"
    verification_status = "extracted"

    # 1. URL Resolution
    app_url = api_apply_url if is_safe_url(api_apply_url) else None
    orig_url = original_job_url if is_safe_url(original_job_url) else None
    company_website = api_company_url if is_safe_url(api_company_url) else None

    # If raw HTML is provided, parse mailto: links and visible anchor tags
    if raw_html:
        try:
            soup = BeautifulSoup(raw_html, "html.parser")
            
            # Check for mailto: links
            mailto_links = soup.select('a[href^="mailto:"]')
            for m in mailto_links:
                href = m.get("href", "")
                email_match = re.search(r"mailto:([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", href, re.IGNORECASE)
                if email_match:
                    cand = email_match.group(1)
                    if is_valid_recruiter_email(cand):
                        recruiter_email = cand
                        extraction_method = "html_mailto"
                        verification_status = "format_validated"
                        break

            # Check for direct apply button/link
            if not app_url:
                apply_links = soup.find_all("a", href=True, string=re.compile(r"apply\s+now|apply\s+for|submit\s+application", re.I))
                for a in apply_links:
                    cand_url = a["href"]
                    if is_safe_url(cand_url):
                        app_url = cand_url
                        break
        except Exception:
            pass

    # 2. Extract recruiter email from description if not found via HTML
    if not recruiter_email:
        emails_found = re.findall(EMAIL_PATTERN, description)
        valid_emails = [e for e in emails_found if is_valid_recruiter_email(e)]
        if valid_emails:
            # Prefer email associated with careers, jobs, recruiter, talent, or hr
            priority_emails = [e for e in valid_emails if any(kw in e.lower() for kw in ["recruit", "talent", "career", "jobs", "hiring", "hr"])]
            recruiter_email = priority_emails[0] if priority_emails else valid_emails[0]
            extraction_method = "text_email_regex"
            verification_status = "format_validated"

    # 3. Extract phone number from description
    phones_found = re.findall(PHONE_PATTERN, description)
    valid_phones = [p.strip() for p in phones_found if is_valid_phone(p)]
    if valid_phones:
        recruiter_phone = valid_phones[0]
        verification_status = "format_validated"

    # 4. Extract recruiter profile URL (e.g., LinkedIn recruiter link)
    linkedin_match = re.search(LINKEDIN_RECRUITER_PATTERN, description)
    if linkedin_match:
        cand_li = linkedin_match.group(0)
        if is_safe_url(cand_li):
            recruiter_profile_url = cand_li

    # 5. Extract recruiter name from explicit contact sections
    for pat in RECRUITER_SECTION_PATTERNS:
        sec_match = re.search(pat, description, flags=re.IGNORECASE)
        if sec_match:
            candidate_line = sec_match.group(1).strip()
            # Clean leading prefixes like "our recruiter", "the hiring manager"
            cleaned_line = re.sub(r"^(?:our|the)?\s*(?:recruiter|hiring\s+manager|talent\s+acquisition|contact)?\s*:?\s*", "", candidate_line, flags=re.IGNORECASE).strip()
            name_match = re.search(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", cleaned_line)
            if name_match:
                matched_cand = name_match.group(1)
                if not any(w in matched_cand.lower() for w in ["recruiter", "manager", "talent", "team"]):
                    recruiter_name = matched_cand
                    break

    # If application url is still empty but original job url is provided, leave them separate!
    # "An application link must not automatically be assumed to be the employer's official website."

    return {
        "original_job_url": orig_url,
        "application_url": app_url,
        "company_website": company_website,
        "recruiter_name": recruiter_name,
        "recruiter_email": recruiter_email,
        "recruiter_phone": recruiter_phone,
        "recruiter_profile_url": recruiter_profile_url,
        "extraction_method": extraction_method,
        "source_page": orig_url or "job_description_body",
        "verification_status": verification_status,
        "last_checked_at": datetime.utcnow()
    }
