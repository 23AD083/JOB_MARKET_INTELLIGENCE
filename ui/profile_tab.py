"""
My Profile Tab Component.
Enables editing education, experience, target roles, location/work preferences,
and managing declared skills while distinctly presenting assessed skills.
"""

import json
from typing import Dict, List, Tuple
import pandas as pd

from database.repository import repo
from processing.skills_taxonomy import get_all_canonical_skills, CATEGORIES


def load_user_profile(user_id: str) -> Tuple[str, str, float, List[str], List[str], str, str, float, str, pd.DataFrame, pd.DataFrame]:
    """Loads user profile data for the UI fields."""
    user = repo.get_or_create_user(username="default_candidate")
    prof = repo.get_user_profile(user_id)
    
    degree = prof.education_degree if prof else "Bachelor's"
    field = prof.field_of_study if prof else "Computer Science"
    yoe = prof.years_of_experience if prof else 3.0
    
    pref_roles = json.loads(prof.preferred_roles) if prof and prof.preferred_roles else ["Software Development", "Data Engineering"]
    pref_locs = json.loads(prof.preferred_locations) if prof and prof.preferred_locations else ["Remote", "New York"]
    workplace = prof.workplace_preference if prof else "any"
    emp_type = prof.employment_type_preference if prof else "full-time"
    min_sal = prof.min_salary if prof and prof.min_salary else 80000.0
    interests = prof.career_interests if prof and prof.career_interests else "Backend systems, data pipelines, scalable architecture."

    # Skills separation
    all_skills = repo.get_user_skills(user_id)
    declared = []
    assessed = []

    level_names = {0: "0 (None)", 1: "1 (Beginner)", 2: "2 (Developing)", 3: "3 (Proficient)", 4: "4 (Advanced)"}

    for us in all_skills:
        row = {
            "Skill": us["skill_name"],
            "Category": us["category"],
            "Proficiency Level": level_names.get(us["proficiency_level"], str(us["proficiency_level"])),
            "Evidence / Notes": us.get("evidence") or "Self-declared",
            "Timestamp": us.get("assessed_at") or "Declared"
        }
        if us["skill_source"] == "assessed":
            assessed.append(row)
        else:
            declared.append(row)

    declared_df = pd.DataFrame(declared) if declared else pd.DataFrame(columns=["Skill", "Category", "Proficiency Level", "Evidence / Notes", "Timestamp"])
    assessed_df = pd.DataFrame(assessed) if assessed else pd.DataFrame(columns=["Skill", "Category", "Proficiency Level", "Evidence / Notes", "Timestamp"])

    return (
        degree,
        field,
        yoe,
        pref_roles,
        pref_locs,
        workplace,
        emp_type,
        min_sal,
        interests,
        declared_df,
        assessed_df
    )


def save_user_profile(
    user_id: str,
    degree: str,
    field: str,
    yoe: float,
    roles: List[str],
    locations: str,
    workplace: str,
    emp_type: str,
    min_sal: float,
    interests: str,
    new_declared_skill: str,
    new_declared_level: int
) -> Tuple[str, pd.DataFrame, pd.DataFrame]:
    """Saves profile updates and optionally adds new declared skills."""
    loc_list = [loc.strip() for loc in locations.split(",") if loc.strip()] if isinstance(locations, str) else locations

    profile_data = {
        "education_degree": degree,
        "field_of_study": field,
        "years_of_experience": float(yoe),
        "preferred_roles": roles,
        "preferred_locations": loc_list,
        "workplace_preference": workplace,
        "employment_type_preference": emp_type,
        "min_salary": float(min_sal) if min_sal else None,
        "career_interests": interests
    }

    repo.update_user_profile(user_id, profile_data)

    # If new declared skill added
    if new_declared_skill and new_declared_skill.strip():
        repo.set_user_skill(
            user_id=user_id,
            skill_name=new_declared_skill.strip(),
            proficiency_level=int(new_declared_level),
            source="declared",
            evidence="Declared in user profile editor"
        )

    # Reload dataframes
    _, _, _, _, _, _, _, _, _, declared_df, assessed_df = load_user_profile(user_id)
    return ("Profile successfully updated and saved!", declared_df, assessed_df)
