"""
Skill Gap Analysis Tab Component.
Empirically identifies high-demand missing skills across target job postings,
highlights declared skills needing assessment, and provides structured learning roadmaps.
"""

from typing import Tuple
import pandas as pd

from database.repository import repo
from matching.skill_gaps import analyze_skill_gaps


def run_skill_gap_analysis(user_id: str, target_category: str, job_id_filter: str) -> Tuple[str, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Computes empirical skill gap breakdown."""
    jid = job_id_filter.strip() if job_id_filter and job_id_filter.strip() else None
    gaps = analyze_skill_gaps(user_id=user_id, target_category=target_category, specific_job_id=jid)

    expl_md = f"""### **Empirical Gap Analysis Breakdown**
{gaps['explanation']}
"""

    # 1. High Priority Gaps Table
    high_priority_rows = []
    for g in gaps.get("high_priority_gaps", []):
        high_priority_rows.append({
            "Missing Skill": g["skill"],
            "Category": g["category"],
            "Market Demand %": f"{g['market_penetration_pct']}%",
            "Required in Postings": g["required_in_jobs"],
            "Preferred in Postings": g["preferred_in_jobs"],
            "Related Skills": ", ".join(g["related_skills"][:3]) if g["related_skills"] else "None"
        })
    gaps_df = pd.DataFrame(high_priority_rows) if high_priority_rows else pd.DataFrame(columns=["Missing Skill", "Category", "Market Demand %", "Required in Postings", "Preferred in Postings", "Related Skills"])

    # 2. Learning Roadmap
    roadmap_rows = []
    for step in gaps.get("learning_path", []):
        roadmap_rows.append({
            "Priority Step": f"Step {step['step']}",
            "Recommended Skill": step["skill"],
            "Category": step["category"],
            "Empirical Rationale": step["rationale"]
        })
    roadmap_df = pd.DataFrame(roadmap_rows) if roadmap_rows else pd.DataFrame(columns=["Priority Step", "Recommended Skill", "Category", "Empirical Rationale"])

    # 3. Skills Needing Assessment
    assess_rows = []
    for item in gaps.get("skills_needing_assessment", []):
        assess_rows.append({
            "Skill": item["skill"],
            "Current Status": "Self-Declared Only",
            "Recommended Action": "Take technical assessment to verify proficiency"
        })
    assess_df = pd.DataFrame(assess_rows) if assess_rows else pd.DataFrame(columns=["Skill", "Current Status", "Recommended Action"])

    return (expl_md, gaps_df, roadmap_df, assess_df)
