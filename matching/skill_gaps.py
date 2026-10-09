"""
Skill Gap Analysis and Learning Prioritization Engine.
Ranks missing skills based on empirical market demand frequency across relevant jobs,
highlights unassessed declared skills, and provides evidence-backed learning paths.
"""

from collections import Counter
import json
from typing import Any, Dict, List, Optional
from database.repository import repo
from database.models import Job
from processing.skills_taxonomy import SKILLS_TAXONOMY, get_canonical_skill_name


def analyze_skill_gaps(
    user_id: str,
    target_category: Optional[str] = None,
    specific_job_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Performs comprehensive skill gap analysis for a user:
    - Analyzes gaps for a specific job OR across all jobs in a target category
    - Identifies market demand frequencies
    - Identifies declared skills that lack assessed verification
    - Outputs suggested learning order with rationale
    """
    user_skills_list = repo.get_user_skills(user_id)
    user_skill_map = {us["skill_name"]: us for us in user_skills_list}

    # Identify declared skills that have not been assessed
    skills_needing_assessment = []
    for s_name, info in user_skill_map.items():
        if info.get("skill_source") == "declared":
            skills_needing_assessment.append({
                "skill": s_name,
                "current_level": info.get("proficiency_level", 0),
                "reason": "Declared by user, pending demonstrated assessment verification."
            })

    session = repo.get_session()
    try:
        # Collect relevant jobs
        if specific_job_id:
            relevant_jobs = session.query(Job).filter(Job.job_id == specific_job_id).all()
        elif target_category and target_category != "All":
            relevant_jobs = session.query(Job).filter(Job.category == target_category).all()
        else:
            relevant_jobs = session.query(Job).all()

        if not relevant_jobs:
            return {
                "high_priority_gaps": [],
                "skills_needing_assessment": skills_needing_assessment,
                "learning_path": [],
                "explanation": "No relevant job postings found in the dataset to calculate skill demand."
            }

        # Count skill frequency in relevant jobs
        req_counter = Counter()
        pref_counter = Counter()

        for j in relevant_jobs:
            reqs = json.loads(j.required_skills) if isinstance(j.required_skills, str) else (j.required_skills or [])
            prefs = json.loads(j.preferred_skills) if isinstance(j.preferred_skills, str) else (j.preferred_skills or [])
            for r in reqs:
                c = get_canonical_skill_name(r) or r
                req_counter[c] += 1
            for p in prefs:
                c = get_canonical_skill_name(p) or p
                pref_counter[c] += 1

        total_jobs = len(relevant_jobs)
        
        # Identify missing skills and rank by market demand frequency
        missing_skills = []
        all_demanded_skills = set(req_counter.keys()) | set(pref_counter.keys())

        for skill in all_demanded_skills:
            if skill not in user_skill_map:
                req_freq = req_counter[skill]
                pref_freq = pref_counter[skill]
                # Priority score: required counts for 2x preferred
                demand_score = (req_freq * 2.0) + (pref_freq * 1.0)
                market_pct = round(((req_freq + pref_freq) / total_jobs) * 100, 1)

                tax_info = SKILLS_TAXONOMY.get(skill, {})
                related = tax_info.get("related", [])
                category = tax_info.get("category", "General")

                missing_skills.append({
                    "skill": skill,
                    "category": category,
                    "demand_score": demand_score,
                    "required_in_jobs": req_freq,
                    "preferred_in_jobs": pref_freq,
                    "market_penetration_pct": market_pct,
                    "related_skills": related
                })

        # Sort missing skills descending by demand score
        missing_skills.sort(key=lambda x: x["demand_score"], reverse=True)
        high_priority = missing_skills[:6]

        # Learning order recommendation
        learning_path = []
        for rank, item in enumerate(high_priority, 1):
            learning_path.append({
                "step": rank,
                "skill": item["skill"],
                "category": item["category"],
                "rationale": f"Requested in {item['market_penetration_pct']}% of analyzed job postings ({item['required_in_jobs']} as required, {item['preferred_in_jobs']} as preferred)."
            })

        explanation = (
            f"Calculated across {total_jobs} job postings in the database. "
            f"Skills are prioritized by required frequency (weighted 2x) and preferred frequency (1x). "
            f"Focusing on the top 3 high-priority skills will unlock the highest proportion of opportunities."
        )

        return {
            "total_jobs_analyzed": total_jobs,
            "high_priority_gaps": high_priority,
            "skills_needing_assessment": skills_needing_assessment,
            "learning_path": learning_path,
            "explanation": explanation
        }

    finally:
        session.close()
