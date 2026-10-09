"""
Explainable Job Matching Engine.
Calculates transparent heuristic scores across:
- Skill Alignment (60%)
- Role Alignment (20%)
- Eligibility: Experience & Education (10%)
- Location and Work Preferences (10%)
Separates required vs preferred skills, accounts for assessed proficiency,
and identifies skills needing assessment and learning priorities.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
import json
from config.settings import settings
from processing.skills_taxonomy import get_canonical_skill_name


def calculate_job_match(
    user_profile: Dict[str, Any],
    user_skills: List[Dict[str, Any]],
    job: Any,
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Computes an explainable match score for a user-job pair.
    Weights default to:
        skills: 0.60, role: 0.20, eligibility: 0.10, preference: 0.10
    """
    w_skill = weights.get("weight_skill", settings.weight_skill) if weights else settings.weight_skill
    w_role = weights.get("weight_role", settings.weight_role) if weights else settings.weight_role
    w_elig = weights.get("weight_eligibility", settings.weight_eligibility) if weights else settings.weight_eligibility
    w_pref = weights.get("weight_preference", settings.weight_preference) if weights else settings.weight_preference

    # Parse job skills
    job_req_skills: List[str] = json.loads(job.required_skills) if isinstance(job.required_skills, str) else (job.required_skills or [])
    job_pref_skills: List[str] = json.loads(job.preferred_skills) if isinstance(job.preferred_skills, str) else (job.preferred_skills or [])

    # User skills mapping: canonical_name -> dict(proficiency_level, skill_source)
    user_skill_map: Dict[str, Dict[str, Any]] = {}
    for us in user_skills:
        name = us["skill_name"]
        canonical = get_canonical_skill_name(name) or name
        # If both declared and assessed exist, assessed takes precedence for proficiency level
        existing = user_skill_map.get(canonical)
        if not existing or us["skill_source"] == "assessed":
            user_skill_map[canonical] = us

    # 1. Skill Alignment Score (0 - 100)
    matched_skills = []
    missing_required = []
    missing_preferred = []
    skills_needing_assessment = []

    req_points = 0.0
    total_req_weight = len(job_req_skills) * 1.0 if job_req_skills else 1.0

    for r_skill in job_req_skills:
        c_skill = get_canonical_skill_name(r_skill) or r_skill
        if c_skill in user_skill_map:
            u_info = user_skill_map[c_skill]
            matched_skills.append(c_skill)
            # Proficiency weighting:
            # Assessed Level 3-4: 1.0
            # Assessed Level 2: 0.85
            # Declared: 0.75
            # Assessed Level 1: 0.50
            if u_info["skill_source"] == "assessed":
                lvl = u_info["proficiency_level"]
                mult = 1.0 if lvl >= 3 else (0.85 if lvl == 2 else 0.5)
            else:
                mult = 0.75
                skills_needing_assessment.append(c_skill)
            req_points += mult
        else:
            missing_required.append(c_skill)

    req_score = (req_points / total_req_weight) * 100.0 if job_req_skills else 80.0

    # Preferred skills score
    pref_points = 0.0
    total_pref_weight = len(job_pref_skills) * 1.0 if job_pref_skills else 1.0

    for p_skill in job_pref_skills:
        c_skill = get_canonical_skill_name(p_skill) or p_skill
        if c_skill in user_skill_map:
            matched_skills.append(c_skill)
            pref_points += 1.0
        else:
            missing_preferred.append(c_skill)

    pref_score = (pref_points / total_pref_weight) * 100.0 if job_pref_skills else 100.0

    # Skills component: 75% required + 25% preferred
    skill_score = min(100.0, (req_score * 0.75) + (pref_score * 0.25))

    # 2. Role Alignment Score (0 - 100)
    user_preferred_roles = user_profile.get("preferred_roles", [])
    if isinstance(user_preferred_roles, str):
        try:
            user_preferred_roles = json.loads(user_preferred_roles)
        except Exception:
            user_preferred_roles = [user_preferred_roles]

    role_score = 50.0  # Base neutral score
    job_cat = getattr(job, "category", "Other")
    job_title_lower = job.job_title.lower()

    if any(r.lower() == job_cat.lower() for r in user_preferred_roles):
        role_score = 100.0
    elif any(r.lower() in job_title_lower for r in user_preferred_roles):
        role_score = 90.0
    elif job_cat == "Other":
        role_score = 65.0
    else:
        role_score = 40.0

    # 3. Eligibility Score (Experience & Education) (0 - 100)
    user_yoe = float(user_profile.get("years_of_experience", 0.0))
    job_exp = getattr(job, "experience_level", "mid") or "mid"
    
    # Target experience benchmarks
    exp_benchmarks = {"entry": 1.0, "mid": 3.0, "senior": 5.0, "lead": 7.0, "executive": 10.0}
    target_yoe = exp_benchmarks.get(job_exp.lower(), 3.0)

    if user_yoe >= target_yoe:
        eligibility_score = 100.0
    else:
        # Proportional eligibility
        eligibility_score = max(30.0, (user_yoe / target_yoe) * 100.0)

    # 4. Location and Preferences Score (0 - 100)
    pref_score_items = []
    
    # Workplace type preference
    u_workplace_pref = user_profile.get("workplace_preference", "any").lower()
    job_workplace = (getattr(job, "workplace_type", "onsite") or "onsite").lower()
    if u_workplace_pref in ("any", "") or u_workplace_pref == job_workplace:
        pref_score_items.append(100.0)
    elif u_workplace_pref == "remote" and job_workplace != "remote":
        pref_score_items.append(30.0)
    elif u_workplace_pref == "hybrid" and job_workplace in ("hybrid", "remote"):
        pref_score_items.append(90.0)
    else:
        pref_score_items.append(60.0)

    # Location preference
    user_locations = user_profile.get("preferred_locations", [])
    if isinstance(user_locations, str):
        try:
            user_locations = json.loads(user_locations)
        except Exception:
            user_locations = []
    
    job_loc = (getattr(job, "location", "") or "").lower()
    if not user_locations or job_workplace == "remote":
        pref_score_items.append(100.0)
    elif any(loc.lower() in job_loc for loc in user_locations):
        pref_score_items.append(100.0)
    else:
        pref_score_items.append(50.0)

    # Salary preference check
    user_min_salary = user_profile.get("min_salary")
    job_max_salary = getattr(job, "salary_max", None)
    if user_min_salary and job_max_salary:
        if job_max_salary >= user_min_salary:
            pref_score_items.append(100.0)
        else:
            pref_score_items.append(40.0)

    preference_score = sum(pref_score_items) / len(pref_score_items) if pref_score_items else 80.0

    # Overall Weighted Score
    overall_score = (
        (skill_score * w_skill) +
        (role_score * w_role) +
        (eligibility_score * w_elig) +
        (preference_score * w_pref)
    )
    overall_score = round(max(0.0, min(100.0, overall_score)), 1)

    # Match Category
    if overall_score >= settings.threshold_strong:
        match_category = "Strong Match"
    elif overall_score >= settings.threshold_potential:
        match_category = "Potential Match"
    else:
        match_category = "Explore"

    # Explanation Generation
    matched_str = ", ".join(matched_skills[:4]) if matched_skills else "None yet"
    missing_str = ", ".join(missing_required[:3]) if missing_required else "None"
    
    explanation_parts = [
        f"**Match Overview**: {match_category} ({overall_score}/100).",
        f"• **Skill Alignment ({round(skill_score, 1)}%)**: Matched {len(matched_skills)} skills ({matched_str}). Missing {len(missing_required)} core skills ({missing_str}).",
        f"• **Role Alignment ({round(role_score, 1)}%)**: Classified as {job_cat} against your target roles.",
        f"• **Experience Eligibility ({round(eligibility_score, 1)}%)**: Your {user_yoe} yrs vs required {job_exp} level.",
        f"• **Preference Fit ({round(preference_score, 1)}%)**: Matches work mode ({job_workplace}) and location preferences."
    ]
    explanation = "\n".join(explanation_parts)

    return {
        "user_id": user_profile.get("user_id"),
        "job_id": job.job_id,
        "overall_score": overall_score,
        "skill_score": round(skill_score, 1),
        "role_score": round(role_score, 1),
        "eligibility_score": round(eligibility_score, 1),
        "preference_score": round(preference_score, 1),
        "match_category": match_category,
        "matched_skills": matched_skills,
        "missing_required_skills": missing_required,
        "missing_preferred_skills": missing_preferred,
        "skills_needing_assessment": skills_needing_assessment,
        "explanation": explanation,
        "suggested_learning_priorities": missing_required[:5]
    }
