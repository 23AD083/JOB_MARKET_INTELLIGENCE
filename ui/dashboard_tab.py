"""
Dashboard Tab Component.
Displays overview metrics, category distribution, top matched opportunities,
and recent ingestion run history.
"""

import json
from typing import Any, List, Tuple
import pandas as pd
import plotly.express as px
import gradio as gr

from database.repository import repo
from matching.score import calculate_job_match


def get_dashboard_metrics(user_id: str) -> Tuple[str, str, str, Any, pd.DataFrame, pd.DataFrame]:
    """Computes real-time metrics and charts for the Dashboard tab."""
    total_jobs = repo.get_total_jobs_count()
    category_counts = repo.get_category_counts()
    recent_runs = repo.get_recent_ingestion_runs(limit=5)
    
    # Calculate new jobs from most recent run
    new_jobs_latest = recent_runs[0].records_accepted if recent_runs else 0
    sources_connected = len(repo.get_source_counts()) or 1

    total_str = f"## **{total_jobs:,}**\nTotal Jobs Stored"
    new_str = f"## **+{new_jobs_latest}**\nNew in Latest Run"
    sources_str = f"## **{sources_connected}**\nActive Data Sources"

    # Category chart
    if category_counts:
        cat_df = pd.DataFrame(list(category_counts.items()), columns=["Category", "Count"])
        fig = px.bar(
            cat_df,
            x="Count",
            y="Category",
            orientation="h",
            color="Category",
            color_discrete_sequence=["#2563eb", "#3b82f6", "#60a5fa", "#93c5fd", "#cbd5e1", "#64748b"],
            title="Jobs by Classified Category"
        )
        fig.update_layout(
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            showlegend=False,
            height=280,
            xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
            yaxis=dict(showgrid=False)
        )
    else:
        fig = px.bar(title="No job categories yet")

    # Top matches for current user
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

    all_jobs = repo.get_all_jobs(limit=100)
    matches = []
    for job in all_jobs:
        m = calculate_job_match(prof_dict, user_skills, job)
        matches.append({
            "Job Title": job.job_title,
            "Company": job.company_name,
            "Category": job.category,
            "Match Score": f"{m['overall_score']}%",
            "Classification": m["match_category"],
            "Location": job.location or "Not specified",
            "Job ID": job.job_id
        })

    matches.sort(key=lambda x: float(x["Match Score"].replace("%", "")), reverse=True)
    top_matches_df = pd.DataFrame(matches[:6]) if matches else pd.DataFrame(columns=["Job Title", "Company", "Category", "Match Score", "Classification", "Location"])

    # Recent ingestion runs table
    runs_data = []
    for r in recent_runs:
        runs_data.append({
            "Source": r.source_name,
            "Status": r.status.upper(),
            "Fetched": r.records_fetched,
            "Accepted": r.records_accepted,
            "Duplicates": r.duplicates_found,
            "Errors": r.errors_count,
            "Duration (s)": f"{r.duration_seconds}s",
            "Timestamp": r.started_at.strftime("%Y-%m-%d %H:%M")
        })
    runs_df = pd.DataFrame(runs_data) if runs_data else pd.DataFrame(columns=["Source", "Status", "Fetched", "Accepted", "Duplicates", "Errors", "Duration (s)", "Timestamp"])

    return (total_str, new_str, sources_str, fig, top_matches_df, runs_df)
