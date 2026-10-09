"""
Settings Tab Component.
Provides tuning for matching heuristic weights, viewing the canonical skill taxonomy,
monitoring database status (with credential masking), and exporting datasets.
"""

import json
import os
from typing import Dict, Tuple
import pandas as pd
import gradio as gr

from config.settings import settings
from database.repository import repo
from processing.skills_taxonomy import SKILLS_TAXONOMY, get_all_canonical_skills


def update_matching_weights(skill_w: float, role_w: float, elig_w: float, pref_w: float) -> str:
    """Updates matching engine heuristic weights."""
    total = skill_w + role_w + elig_w + pref_w
    if abs(total - 1.0) > 0.05 and abs(total - 100.0) > 1.0:
        return f"Warning: Weights sum to {round(total, 2)}. Recommended sum is 1.0 (or 100%)."

    # Normalize to 1.0 if entered as percentages
    if total > 50.0:
        skill_w /= 100.0
        role_w /= 100.0
        elig_w /= 100.0
        pref_w /= 100.0

    settings.weight_skill = skill_w
    settings.weight_role = role_w
    settings.weight_eligibility = elig_w
    settings.weight_preference = pref_w

    return f"Weights successfully updated: Skills ({round(skill_w*100)}%), Role ({round(role_w*100)}%), Eligibility ({round(elig_w*100)}%), Preferences ({round(pref_w*100)}%)."


def get_taxonomy_table() -> pd.DataFrame:
    """Returns the skills taxonomy as a readable dataframe."""
    rows = []
    for skill, data in sorted(SKILLS_TAXONOMY.items()):
        rows.append({
            "Canonical Skill": skill,
            "Category": data["category"],
            "Known Aliases": ", ".join(data.get("aliases", [])),
            "Related Skills": ", ".join(data.get("related", []))
        })
    return pd.DataFrame(rows)


def get_system_status() -> str:
    """Returns database and deployment environment diagnostics with masked credentials."""
    total_jobs = repo.get_total_jobs_count()
    masked_db = settings.get_masked_db_url()
    
    return f"""### **System & Deployment Status**
• **Application**: {settings.app_name} (v{settings.app_version})
• **Runtime Mode**: CPU Only (Zero generative LLM / AI API dependencies)
• **NLP Engine**: Extractive Rule-Based NLP, Curated Taxonomy, TF-IDF, scikit-learn
• **Database Connection**: `{masked_db}`
• **Total Jobs Stored**: **{total_jobs:,}**
• **Hugging Face Spaces Ready**: Yes (Gradio SDK, Port 7860)
"""


def export_jobs_csv() -> str:
    """Exports all stored jobs to a temporary CSV file for user download."""
    jobs = repo.get_all_jobs(limit=1000)
    rows = []
    for j in jobs:
        rows.append({
            "job_id": j.job_id,
            "source": j.source,
            "job_title": j.job_title,
            "company_name": j.company_name,
            "location": j.location,
            "category": j.category,
            "workplace_type": j.workplace_type,
            "experience_level": j.experience_level,
            "salary_min": j.salary_min,
            "salary_max": j.salary_max,
            "original_job_url": j.original_job_url,
            "application_url": j.application_url,
            "recruiter_email": j.recruiter_email,
            "verification_status": j.verification_status,
            "posted_at": j.posted_at
        })
    df = pd.DataFrame(rows)
    export_path = os.path.join(os.path.dirname(__file__), "..", "data", "exported_jobs.csv")
    df.to_csv(export_path, index=False)
    return export_path
