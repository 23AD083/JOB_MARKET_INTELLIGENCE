"""
Job Normalization Pipeline.
Transforms heterogeneous job records from varied connectors into standardized, validated models.
Calculates SHA-256 content hashes, cleans HTML, normalizes salaries, workplace types, and dates.
"""

from datetime import datetime
import hashlib
import re
from typing import Any, Dict, Optional, Tuple
from bs4 import BeautifulSoup

from ingestion.validate import JobRecordSchema, validate_raw_job_dict
from processing.extract_skills import extract_skills_from_job
from processing.classify import classify_job
from processing.summarize import generate_job_summary
from processing.extract_contacts import extract_contacts_from_text_and_urls


def clean_html_text(text: Optional[str]) -> str:
    """Cleans HTML tags and entities from job descriptions while preserving structure."""
    if not text or not isinstance(text, str):
        return ""
    
    # Check if string contains HTML
    if "<" in text and ">" in text:
        try:
            soup = BeautifulSoup(text, "html.parser")
            # Convert breaks and list items to newlines
            for br in soup.find_all("br"):
                br.replace_with("\n")
            for li in soup.find_all("li"):
                li.insert_before("\n• ")
            for p in soup.find_all(["p", "div", "h1", "h2", "h3", "h4"]):
                p.insert_before("\n")
            text = soup.get_text()
        except Exception:
            text = re.sub(r"<[^>]+>", " ", text)

    # Normalize multiple newlines and spaces
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    cleaned = "\n".join([line for line in lines if line])
    return cleaned


def parse_salary_string(salary_str: Optional[str]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Extracts min salary, max salary, and currency code from varied salary strings.
    Example: '$120,000 - $160,000 / year', '£65k - 80k', '€90000'
    """
    if not salary_str or not isinstance(salary_str, str):
        return (None, None, None)

    salary_str = salary_str.strip()
    currency = None
    if "$" in salary_str or "USD" in salary_str:
        currency = "USD"
    elif "£" in salary_str or "GBP" in salary_str:
        currency = "GBP"
    elif "€" in salary_str or "EUR" in salary_str:
        currency = "EUR"
    elif "CAD" in salary_str:
        currency = "CAD"

    # Extract all numbers/k values
    cleaned = salary_str.replace(",", "")
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*(k|thousand)?", cleaned, flags=re.IGNORECASE)
    values = []
    for num_str, k_mult in matches:
        try:
            val = float(num_str)
            if k_mult:
                val *= 1000
            # If hourly rate (e.g. 50-80), convert to annual equivalent (2080 hours) for consistency if < 200
            if val < 200:
                val = val * 2080
            values.append(val)
        except ValueError:
            pass

    if not values:
        return (None, None, currency)
    if len(values) == 1:
        return (values[0], values[0], currency or "USD")
    return (min(values[0], values[1]), max(values[0], values[1]), currency or "USD")


def normalize_workplace_type(value: Optional[str], text_context: str = "") -> str:
    """Normalizes workplace type to 'remote', 'hybrid', or 'onsite'."""
    cand = (value or "").strip().lower()
    combined = f"{cand} {text_context.lower()}"
    
    if "remote" in cand:
        return "remote"
    if "hybrid" in cand:
        return "hybrid"
    if "onsite" in cand or "on-site" in cand or "in-office" in cand:
        return "onsite"
        
    # Check context
    if "fully remote" in combined or "100% remote" in combined or "work from home" in combined:
        return "remote"
    if "hybrid work" in combined or "flexible hybrid" in combined:
        return "hybrid"
    return "onsite"


def normalize_experience_level(value: Optional[str], title: str, text: str) -> str:
    """Normalizes experience level into entry, mid, senior, lead, executive."""
    cand = (value or "").strip().lower()
    combined = f"{cand} {title.lower()}"

    if any(w in combined for w in ["intern", "entry", "junior", "associate", "jr."]):
        return "entry"
    if any(w in combined for w in ["lead", "principal", "staff", "director", "head", "vp"]):
        return "lead"
    if any(w in combined for w in ["senior", "sr."]):
        return "senior"
    if any(w in combined for w in ["mid", "intermediate"]):
        return "mid"
    return "mid"


def compute_content_hash(company: str, title: str, location: Optional[str], description: str) -> str:
    """
    Computes a deterministic SHA-256 hash from normalized job content
    to detect duplicate listings across sources.
    """
    norm_comp = re.sub(r"[^a-z0-9]", "", company.lower())
    norm_title = re.sub(r"[^a-z0-9]", "", title.lower())
    norm_loc = re.sub(r"[^a-z0-9]", "", (location or "").lower())
    # First 300 non-whitespace characters of description captures core overview
    norm_desc = re.sub(r"[^a-z0-9]", "", description.lower())[:300]
    
    content_str = f"{norm_comp}::{norm_title}::{norm_loc}::{norm_desc}"
    return hashlib.sha256(content_str.encode("utf-8")).hexdigest()


def compute_job_id(source: str, source_job_id: Optional[str], content_hash: str) -> str:
    """Generates a unique deterministic job ID."""
    if source_job_id:
        clean_sid = re.sub(r"[^a-zA-Z0-9_-]", "", str(source_job_id))
        return f"{source}_{clean_sid}"[:64]
    return f"{source}_{content_hash[:16]}"


def normalize_job_dict(raw: Dict[str, Any], source: str) -> Optional[JobRecordSchema]:
    """
    Normalizes a dictionary from an external connector into a validated JobRecordSchema.
    Applies skill extraction, classification, summarization, and contact extraction.
    """
    title = str(raw.get("job_title") or raw.get("title") or raw.get("position") or "").strip()
    company = str(raw.get("company_name") or raw.get("company") or raw.get("employer") or "").strip()
    desc_raw = str(raw.get("job_description") or raw.get("description") or raw.get("text") or "").strip()

    if not title or not company or len(desc_raw) < 10:
        return None

    desc_cleaned = clean_html_text(desc_raw)
    location = str(raw.get("location") or raw.get("city") or "").strip() or None
    country = str(raw.get("country") or "").strip() or None
    source_job_id = str(raw.get("source_job_id") or raw.get("id") or "").strip() or None

    # Salary parsing
    sal_min = raw.get("salary_min")
    sal_max = raw.get("salary_max")
    currency = raw.get("salary_currency")
    if sal_min is None and sal_max is None and raw.get("salary"):
        p_min, p_max, p_curr = parse_salary_string(str(raw.get("salary")))
        sal_min, sal_max, currency = p_min, p_max, p_curr
    try:
        sal_min = float(sal_min) if sal_min is not None else None
    except (ValueError, TypeError):
        sal_min = None
    try:
        sal_max = float(sal_max) if sal_max is not None else None
    except (ValueError, TypeError):
        sal_max = None

    workplace_type = normalize_workplace_type(raw.get("workplace_type"), desc_cleaned)
    exp_level = normalize_experience_level(raw.get("experience_level"), title, desc_cleaned)
    content_hash = compute_content_hash(company, title, location, desc_cleaned)
    job_id = compute_job_id(source, source_job_id, content_hash)

    # 1. Skill Extraction
    extracted_skills_dict = extract_skills_from_job(title, desc_cleaned)
    req_skills = extracted_skills_dict["required_skills"]
    pref_skills = extracted_skills_dict["preferred_skills"]
    all_skills = extracted_skills_dict["all_skills"]

    # 2. Role Classification
    category, category_conf, _ = classify_job(title, desc_cleaned, all_skills)

    # 3. Contacts & Links Extraction
    contacts_dict = extract_contacts_from_text_and_urls(
        description=desc_cleaned,
        raw_html=desc_raw if "<" in desc_raw else None,
        original_job_url=raw.get("original_job_url") or raw.get("url"),
        api_apply_url=raw.get("application_url") or raw.get("apply_url"),
        api_company_url=raw.get("company_website") or raw.get("company_url"),
        company_name=company
    )

    # Date parsing
    posted_at = raw.get("posted_at")
    if isinstance(posted_at, str):
        try:
            # ISO 8601 or common date formats
            posted_at = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
        except Exception:
            posted_at = None

    job_data = {
        "job_id": job_id,
        "source": source,
        "source_job_id": source_job_id,
        "job_title": title,
        "company_name": company,
        "job_description": desc_cleaned,
        "location": location,
        "country": country,
        "employment_type": raw.get("employment_type") or "full-time",
        "workplace_type": workplace_type,
        "experience_level": exp_level,
        "salary_min": sal_min,
        "salary_max": sal_max,
        "salary_currency": currency or "USD",
        "required_skills": req_skills,
        "preferred_skills": pref_skills,
        "education_requirements": raw.get("education_requirements"),
        "original_job_url": contacts_dict["original_job_url"],
        "application_url": contacts_dict["application_url"],
        "company_website": contacts_dict["company_website"],
        "recruiter_name": contacts_dict["recruiter_name"],
        "recruiter_email": contacts_dict["recruiter_email"],
        "recruiter_phone": contacts_dict["recruiter_phone"],
        "recruiter_profile_url": contacts_dict["recruiter_profile_url"],
        "posted_at": posted_at,
        "fetched_at": datetime.utcnow(),
        "last_verified_at": datetime.utcnow(),
        "extraction_source": source,
        "verification_status": contacts_dict["verification_status"],
        "content_hash": content_hash,
        "category": category,
        "category_confidence": category_conf
    }

    res = validate_raw_job_dict(job_data)
    if res.is_valid and res.record:
        return res.record
    return None
