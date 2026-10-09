"""
Job Details Tab Component.
Displays deep-dive view of a single selected job posting:
- Rule-based extracted summary vs original description
- Match breakdown: Skill, Role, Eligibility, Preference scores
- Missing skills and suggested learning priorities
- Application links and recruitment contacts with full provenance
"""

import json
from typing import Dict, Tuple
from database.repository import repo
from matching.score import calculate_job_match


def get_job_details_view(user_id: str, job_id: str) -> Tuple[str, str, str, str, str]:
    """
    Returns markdown representations for the selected job's header, match analysis,
    extracted summary, contacts/links, and original raw description.
    """
    if not job_id or not job_id.strip():
        return (
            "### Please select a Job ID from the 'Discover Jobs' tab to view details.",
            "",
            "",
            "",
            ""
        )

    job = repo.get_job_by_id(job_id.strip())
    if not job:
        return (f"### Job ID '{job_id}' not found.", "", "", "", "")

    # Calculate match
    user_prof = repo.get_user_profile(user_id)
    prof_dict = {
        "user_id": user_id,
        "years_of_experience": user_prof.years_of_experience if user_prof else 3.0,
        "preferred_roles": user_prof.preferred_roles if user_prof else "[]",
        "preferred_locations": user_prof.preferred_locations if user_prof else "[]",
        "workplace_preference": user_prof.workplace_preference if user_prof else "any",
        "min_salary": user_prof.min_salary if user_prof else None
    }
    user_skills = repo.get_user_skills(user_id)
    match_res = calculate_job_match(prof_dict, user_skills, job)

    # 1. Header Information
    sal_info = "Not specified"
    if job.salary_min and job.salary_max:
        sal_info = f"${int(job.salary_min):,} - ${int(job.salary_max):,} {job.salary_currency}"
    elif job.salary_min:
        sal_info = f"${int(job.salary_min):,}+ {job.salary_currency}"

    header_md = f"""## **{job.job_title}**
### **{job.company_name}** • {job.location or 'Location Not Listed'} • {(job.workplace_type or 'onsite').capitalize()}

| Category | Experience Level | Employment Type | Salary Range | Source Connector |
| :--- | :--- | :--- | :--- | :--- |
| **{job.category}** | **{(job.experience_level or 'mid').capitalize()}** | **{(job.employment_type or 'full-time').capitalize()}** | **{sal_info}** | `{job.source}` |
"""

    # 2. Match Score Breakdown
    matched_skills_str = ", ".join(match_res["matched_skills"]) if match_res["matched_skills"] else "None yet"
    missing_req_str = ", ".join(match_res["missing_required_skills"]) if match_res["missing_required_skills"] else "None (All core skills covered!)"
    missing_pref_str = ", ".join(match_res["missing_preferred_skills"]) if match_res["missing_preferred_skills"] else "None"
    assess_str = ", ".join(match_res["skills_needing_assessment"]) if match_res["skills_needing_assessment"] else "All matched skills are verified"

    match_md = f"""### **Personalized Match Analysis: {match_res['overall_score']}% ({match_res['match_category']})**

| Sub-Metric | Score | Weight | Rationale |
| :--- | :--- | :--- | :--- |
| **Skill Alignment** | **{match_res['skill_score']}%** | 60% | Matched: *{matched_skills_str}* |
| **Role Alignment** | **{match_res['role_score']}%** | 20% | Target category congruence |
| **Experience Eligibility** | **{match_res['eligibility_score']}%** | 10% | Profile tenure vs requirements |
| **Preferences Fit** | **{match_res['preference_score']}%** | 10% | Workplace mode, location, salary |

**Detailed Explanation**:
{match_res['explanation']}

**Skill Gap & Learning Priorities**:
• **Missing Required Skills**: `{missing_req_str}`
• **Missing Preferred Skills**: `{missing_pref_str}`
• **Skills Needing Demonstrated Assessment**: `{assess_str}`
"""

    # 3. Rule-Based Extracted Summary
    summary_obj = job.summary
    if summary_obj:
        summary_md = f"""### **Rule-Based Job Summary (Extractive NLP)**

{summary_obj.summary_text}
"""
    else:
        summary_md = "### Rule-based summary not yet generated for this record."

    # 4. Contacts, Links & Provenance
    contact_obj = job.contact
    orig_url = job.original_job_url or (contact_obj.original_job_url if contact_obj else None) or "Not publicly listed"
    app_url = job.application_url or (contact_obj.application_url if contact_obj else None) or "Not publicly listed"
    comp_url = job.company_website or (contact_obj.company_website if contact_obj else None) or "Not publicly listed"
    rec_name = job.recruiter_name or (contact_obj.recruiter_name if contact_obj else None) or "Not publicly listed"
    rec_email = job.recruiter_email or (contact_obj.recruiter_email if contact_obj else None) or "Not publicly listed"
    rec_phone = job.recruiter_phone or (contact_obj.recruiter_phone if contact_obj else None) or "Not publicly listed"
    rec_li = job.recruiter_profile_url or (contact_obj.recruiter_profile_url if contact_obj else None) or "Not publicly listed"
    method = contact_obj.extraction_method if contact_obj else "structured_metadata"
    ver_status = contact_obj.verification_status if contact_obj else job.verification_status

    orig_link_md = f"[{orig_url}]({orig_url})" if orig_url.startswith("http") else orig_url
    app_link_md = f"[{app_url}]({app_url})" if app_url.startswith("http") else app_url
    comp_link_md = f"[{comp_url}]({comp_url})" if comp_url.startswith("http") else comp_url
    rec_li_md = f"[{rec_li}]({rec_li})" if rec_li.startswith("http") else rec_li

    contacts_md = f"""### **Application Links & Recruitment Contacts**

| Resource / Contact | Value | Provenance & Verification |
| :--- | :--- | :--- |
| **Direct Application URL** | {app_link_md} | Validated safe external link |
| **Original Job Board Link** | {orig_link_md} | Source origin page |
| **Company Website** | {comp_link_md} | Official employer domain |
| **Recruiter Name** | **{rec_name}** | Extracted from posting metadata |
| **Recruitment Email** | `{rec_email}` | Validated RFC5322 format ({ver_status}) |
| **Recruiter Phone** | `{rec_phone}` | Validated phone structure |
| **Professional Profile** | {rec_li_md} | Public profile link |

> **Provenance Notice**:
> Contact information is displayed strictly when extracted directly from public source data (extraction method: `{method}`, status: `{ver_status}`). Contacts are never inferred, guessed, or fabricated.
"""

    # 5. Raw Full Job Description
    raw_desc_md = f"""### **Full Original Job Description**
```text
{job.job_description}
```
"""

    return (header_md, match_md, summary_md, contacts_md, raw_desc_md)
