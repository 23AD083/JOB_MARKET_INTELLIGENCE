"""
Discover Jobs Tab Component.
Supports multi-field keyword search, structured filters (category, experience, work mode),
sorting by match score, and selection for detailed inspection.
"""

import json
from typing import List, Tuple
import pandas as pd

from database.repository import repo
from matching.score import calculate_job_match


def search_and_filter_jobs(
    user_id: str,
    search_query: str,
    category_filter: str,
    experience_filter: str,
    workplace_filter: str,
    min_match_score: float,
    sort_by: str = "Match Score (High to Low)"
) -> pd.DataFrame:
    """
    Filters and ranks jobs dynamically with user-specific personalized match scores.
    """
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

    # Fetch jobs from DB
    jobs = repo.get_all_jobs(
        query_str=search_query,
        category=category_filter,
        experience=experience_filter,
        workplace_type=workplace_filter,
        limit=150
    )

    rows = []
    for job in jobs:
        m = calculate_job_match(prof_dict, user_skills, job)
        score = m["overall_score"]

        if score < min_match_score:
            continue

        sal_str = "Not listed"
        if job.salary_min and job.salary_max:
            sal_str = f"${int(job.salary_min):,} - ${int(job.salary_max):,}"
        elif job.salary_min:
            sal_str = f"${int(job.salary_min):,}+"

        req_skills_list = json.loads(job.required_skills) if isinstance(job.required_skills, str) else (job.required_skills or [])

        rows.append({
            "Job ID": job.job_id,
            "Title": job.job_title,
            "Company": job.company_name,
            "Category": job.category,
            "Match %": score,
            "Match Type": m["match_category"],
            "Location": job.location or "Not specified",
            "Work Mode": (job.workplace_type or "onsite").capitalize(),
            "Experience": (job.experience_level or "mid").capitalize(),
            "Salary": sal_str,
            "Top Required Skills": ", ".join(req_skills_list[:4]) if req_skills_list else "None listed"
        })

    if not rows:
        return pd.DataFrame(columns=["Job ID", "Title", "Company", "Category", "Match %", "Match Type", "Location", "Work Mode", "Experience", "Salary", "Top Required Skills"])

    df = pd.DataFrame(rows)
    if sort_by == "Match Score (High to Low)":
        df = df.sort_values(by="Match %", ascending=False)
    elif sort_by == "Company (A-Z)":
        df = df.sort_values(by="Company", ascending=True)
    elif sort_by == "Title (A-Z)":
        df = df.sort_values(by="Title", ascending=True)

    return df
