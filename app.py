"""
Complete Non-LLM Job Intelligence Pipeline.
Main application entry point and Gradio web interface.
Deployable to Hugging Face Spaces (CPU, zero generative AI APIs).
"""

import os
import gradio as gr
import pandas as pd

from config.settings import settings
from database.init_db import initialize_database
from database.repository import repo
from ui.theme import CUSTOM_CSS
from ui.dashboard_tab import get_dashboard_metrics
from ui.jobs_tab import search_and_filter_jobs
from ui.details_tab import get_job_details_view
from ui.profile_tab import load_user_profile, save_user_profile
from ui.assessments_tab import load_question_for_skill, submit_assessment_attempt
from ui.gaps_tab import run_skill_gap_analysis
from ui.sources_tab import handle_csv_upload_and_ingest, run_manual_source_sync, test_source_connection
from ui.settings_tab import update_matching_weights, get_taxonomy_table, get_system_status, export_jobs_csv
from assessments.question_bank import question_bank
from processing.skills_taxonomy import CATEGORIES, get_all_canonical_skills

# Initialize DB, seed taxonomy, assessment questions, and synthetic dataset
default_user = initialize_database()
CURRENT_USER_ID = default_user.id


def build_app() -> gr.Blocks:
    with gr.Blocks(title="Job Intelligence Pipeline") as demo:
        # Header Bar
        with gr.Row(elem_classes=["app-header"]):
            with gr.Column(scale=8):
                gr.Markdown(
                    """
# **Job Intelligence Pipeline**
#### Deterministic Multi-Source Postings Ingestion • Extractive Non-LLM NLP • Explainable Matching & Assessments
"""
                )
            with gr.Column(scale=4):
                refresh_all_btn = gr.Button("🔄 Refresh Dashboard Data", size="sm", elem_classes=["primary-btn"])

        # Main Tabs
        with gr.Tabs() as tabs:
            
            # ---------------- TAB 1: DASHBOARD ----------------
            with gr.Tab("📊 Dashboard", id="tab_dashboard"):
                with gr.Row():
                    m_total = gr.Markdown("## --\nTotal Jobs Stored")
                    m_new = gr.Markdown("## --\nNew in Latest Run")
                    m_sources = gr.Markdown("## --\nActive Data Sources")

                with gr.Row():
                    with gr.Column(scale=5):
                        dash_chart = gr.Plot(label="Jobs by Category")
                    with gr.Column(scale=7):
                        gr.Markdown("### **Top Matched Opportunities for Your Profile**")
                        top_jobs_table = gr.DataFrame(
                            headers=["Job Title", "Company", "Category", "Match Score", "Classification", "Location", "Job ID"],
                            interactive=False,
                            wrap=True
                        )

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### **Recent Data Ingestion Status**")
                        runs_table = gr.DataFrame(interactive=False, wrap=True)

            # ---------------- TAB 2: DISCOVER JOBS ----------------
            with gr.Tab("🔍 Discover Jobs", id="tab_discover"):
                with gr.Row():
                    search_input = gr.Textbox(label="Search Keywords", placeholder="e.g. Python, Data Engineer, San Francisco...", scale=4)
                    category_filter = gr.Dropdown(choices=["All"] + CATEGORIES, value="All", label="Category", scale=2)
                    experience_filter = gr.Dropdown(choices=["All", "Entry", "Mid", "Senior", "Lead"], value="All", label="Experience", scale=2)
                    workplace_filter = gr.Dropdown(choices=["All", "Remote", "Hybrid", "Onsite"], value="All", label="Workplace Mode", scale=2)

                with gr.Row():
                    min_score_slider = gr.Slider(minimum=0.0, maximum=100.0, value=0.0, step=5.0, label="Minimum Match Score (%)", scale=3)
                    sort_dropdown = gr.Dropdown(
                        choices=["Match Score (High to Low)", "Company (A-Z)", "Title (A-Z)"],
                        value="Match Score (High to Low)",
                        label="Sort Order",
                        scale=3
                    )
                    search_btn = gr.Button("Filter Jobs", elem_classes=["primary-btn"], scale=2)

                jobs_results_table = gr.DataFrame(
                    headers=["Job ID", "Title", "Company", "Category", "Match %", "Match Type", "Location", "Work Mode", "Experience", "Salary", "Top Required Skills"],
                    interactive=False,
                    wrap=True
                )

                selected_job_instruction = gr.Markdown("💡 *Tip: Copy a **Job ID** from the table above and open the **Job Details** tab to inspect full extractive analysis.*")

            # ---------------- TAB 3: JOB DETAILS ----------------
            with gr.Tab("📄 Job Details", id="tab_details"):
                with gr.Row():
                    job_id_input = gr.Textbox(label="Enter Job ID", placeholder="e.g. kaggle_csv_de-401 or copy from Discover Jobs", scale=6)
                    load_job_btn = gr.Button("Inspect Job Details", elem_classes=["primary-btn"], scale=2)

                detail_header = gr.Markdown("### Please select or enter a Job ID above.")
                detail_match = gr.Markdown()
                
                with gr.Row():
                    with gr.Column(scale=6):
                        detail_summary = gr.Markdown()
                    with gr.Column(scale=6):
                        detail_contacts = gr.Markdown()

                detail_raw = gr.Markdown()

            # ---------------- TAB 4: MY PROFILE ----------------
            with gr.Tab("👤 My Profile", id="tab_profile"):
                with gr.Row():
                    with gr.Column(scale=6):
                        gr.Markdown("### **Candidate Qualifications & Preferences**")
                        prof_degree = gr.Textbox(label="Education Degree", value="Bachelor's")
                        prof_field = gr.Textbox(label="Field of Study", value="Computer Science")
                        prof_yoe = gr.Number(label="Years of Experience", value=3.0, precision=1)
                        prof_roles = gr.CheckboxGroup(choices=CATEGORIES, label="Preferred Target Roles", value=["Software Development", "Data Engineering"])
                        prof_locations = gr.Textbox(label="Preferred Locations (comma-separated)", value="Remote, New York, San Francisco")
                        prof_workplace = gr.Dropdown(choices=["any", "remote", "hybrid", "onsite"], value="any", label="Workplace Mode Preference")
                        prof_emp_type = gr.Dropdown(choices=["full-time", "contract", "internship", "any"], value="full-time", label="Employment Type Preference")
                        prof_min_salary = gr.Number(label="Target Minimum Salary (Annual USD)", value=80000.0)
                        prof_interests = gr.Textbox(label="Career Interests & Technical Focus", lines=2, value="Backend systems, data pipelines, scalable distributed architectures.")

                    with gr.Column(scale=6):
                        gr.Markdown("### **Add / Update Declared Skills**")
                        new_skill_dropdown = gr.Dropdown(choices=get_all_canonical_skills(), label="Select Canonical Skill", value="Python")
                        new_skill_level = gr.Slider(minimum=1, maximum=4, step=1, value=3, label="Self-Reported Proficiency (1: Beginner, 2: Developing, 3: Proficient, 4: Advanced)")
                        save_prof_btn = gr.Button("💾 Save Profile Changes", elem_classes=["primary-btn"])
                        prof_status_msg = gr.Markdown()

                        gr.Markdown("### **Current Declared Skills**")
                        prof_declared_table = gr.DataFrame(interactive=False, wrap=True)

                        gr.Markdown("### **Verified Assessed Skills (Earned via Assessment)**")
                        prof_assessed_table = gr.DataFrame(interactive=False, wrap=True)

            # ---------------- TAB 5: SKILL ASSESSMENTS ----------------
            with gr.Tab("📝 Skill Assessments", id="tab_assessments"):
                gr.Markdown(
                    """
### **Demonstrated Skill Assessment Engine**
Assessments evaluate demonstrated technical understanding using deterministic rubrics and tests.
*Disclaimer: Assessments are indicators of demonstrated performance, not guarantees of workplace competence.*
"""
                )
                with gr.Row():
                    assess_skill_select = gr.Dropdown(
                        choices=question_bank.get_skills_with_assessments(),
                        value="Python",
                        label="Select Skill to Assess",
                        scale=4
                    )
                    load_q_btn = gr.Button("Load Question", elem_classes=["primary-btn"], scale=2)

                q_display = gr.Markdown()
                q_options_radio = gr.Radio(label="Select Your Answer", choices=[])
                submit_answer_btn = gr.Button("Submit Assessment Answer", elem_classes=["primary-btn"])

                # Hidden state for correct answer and rubric
                state_correct = gr.State()
                state_rubric = gr.State()

                assess_feedback = gr.Markdown()
                gr.Markdown("### **Your Verified Assessed Credentials**")
                assess_history_table = gr.DataFrame(interactive=False, wrap=True)

            # ---------------- TAB 6: SKILL GAP ANALYSIS ----------------
            with gr.Tab("📈 Skill Gap Analysis", id="tab_gaps"):
                gr.Markdown("### **Empirical Market Gap & Learning Order Analysis**")
                with gr.Row():
                    gap_cat_select = gr.Dropdown(choices=["All"] + CATEGORIES, value="All", label="Target Category", scale=4)
                    gap_job_id = gr.Textbox(label="Optional Specific Job ID", placeholder="Leave blank to analyze all market postings", scale=4)
                    run_gaps_btn = gr.Button("Analyze Skill Gaps", elem_classes=["primary-btn"], scale=2)

                gap_explanation_md = gr.Markdown()
                
                with gr.Row():
                    with gr.Column(scale=6):
                        gr.Markdown("#### **High-Priority Missing Skills (Ranked by Market Demand)**")
                        gap_high_priority_table = gr.DataFrame(interactive=False, wrap=True)
                    with gr.Column(scale=6):
                        gr.Markdown("#### **Recommended Learning Order (Empirical Rationale)**")
                        gap_roadmap_table = gr.DataFrame(interactive=False, wrap=True)

                gr.Markdown("#### **Declared Skills Needing Assessment Verification**")
                gap_unassessed_table = gr.DataFrame(interactive=False, wrap=True)

            # ---------------- TAB 7: DATA SOURCES ----------------
            with gr.Tab("🔌 Data Sources & Ingestion", id="tab_sources"):
                gr.Markdown("### **Connector Ingestion & Pipeline Configuration**")
                
                with gr.Accordion("📁 1. Kaggle / Custom CSV Dataset Import", open=True):
                    csv_file_input = gr.File(label="Upload Job Postings CSV", file_types=[".csv"])
                    csv_upload_btn = gr.Button("Ingest & Deduplicate CSV", elem_classes=["primary-btn"])
                    csv_result_md = gr.Markdown()

                with gr.Accordion("🌐 2. External API Connectors (Greenhouse, Lever, Adzuna)", open=True):
                    with gr.Row():
                        gh_tokens_input = gr.Textbox(label="Greenhouse Employer Boards (comma-separated)", value="canonical, cloudflare, gitlab, stripe, figma, discord, reddit", scale=4)
                        lever_slugs_input = gr.Textbox(label="Lever Employer Slugs (comma-separated)", value="coursera, atlassian", scale=4)

                    with gr.Row():
                        adzuna_id_input = gr.Textbox(label="Adzuna App ID (Optional)", placeholder="Enter App ID if available", scale=3)
                        adzuna_key_input = gr.Textbox(label="Adzuna App Key (Optional, Masked)", type="password", placeholder="Enter App Key if available", scale=3)
                        adzuna_country_input = gr.Dropdown(choices=["us", "gb", "ca", "au", "de"], value="us", label="Adzuna Country", scale=2)

                    with gr.Row():
                        sync_source_dropdown = gr.Dropdown(choices=["All Enabled Sources", "greenhouse", "lever", "adzuna"], value="All Enabled Sources", label="Select Source to Sync", scale=4)
                        test_conn_btn = gr.Button("Test Connection", scale=2)
                        run_sync_btn = gr.Button("Run Ingestion Now", elem_classes=["primary-btn"], scale=2)

                    sync_feedback_md = gr.Markdown()

                gr.Markdown("### **Ingestion Audit Log**")
                sources_runs_table = gr.DataFrame(interactive=False, wrap=True)

            # ---------------- TAB 8: SETTINGS ----------------
            with gr.Tab("⚙️ Settings & System", id="tab_settings"):
                with gr.Row():
                    with gr.Column(scale=6):
                        gr.Markdown("### **Matching Heuristic Weights**")
                        w_skill_slider = gr.Slider(minimum=0.0, maximum=1.0, value=0.60, step=0.05, label="Skill Alignment Weight (Default: 0.60)")
                        w_role_slider = gr.Slider(minimum=0.0, maximum=1.0, value=0.20, step=0.05, label="Role Alignment Weight (Default: 0.20)")
                        w_elig_slider = gr.Slider(minimum=0.0, maximum=1.0, value=0.10, step=0.05, label="Experience Eligibility Weight (Default: 0.10)")
                        w_pref_slider = gr.Slider(minimum=0.0, maximum=1.0, value=0.10, step=0.05, label="Preferences Weight (Default: 0.10)")
                        save_weights_btn = gr.Button("Save Weight Configuration", elem_classes=["primary-btn"])
                        weights_status_md = gr.Markdown()

                    with gr.Column(scale=6):
                        status_display_md = gr.Markdown(get_system_status())
                        export_btn = gr.Button("Export Stored Jobs (CSV)", elem_classes=["primary-btn"])
                        export_file_out = gr.File(label="Download Exported CSV")

                gr.Markdown("### **Configurable Canonical Skills Taxonomy**")
                taxonomy_view_table = gr.DataFrame(value=get_taxonomy_table(), interactive=False, wrap=True)

        # ---------------- EVENT WIRINGS ----------------

        # Initial load / Refresh Dashboard
        def refresh_dash():
            return get_dashboard_metrics(CURRENT_USER_ID)

        demo.load(refresh_dash, outputs=[m_total, m_new, m_sources, dash_chart, top_jobs_table, runs_table])
        refresh_all_btn.click(refresh_dash, outputs=[m_total, m_new, m_sources, dash_chart, top_jobs_table, runs_table])

        # Discover Jobs
        def do_search(q, cat, exp, wp, min_sc, s_by):
            return search_and_filter_jobs(CURRENT_USER_ID, q, cat, exp, wp, min_sc, s_by)

        search_btn.click(
            do_search,
            inputs=[search_input, category_filter, experience_filter, workplace_filter, min_score_slider, sort_dropdown],
            outputs=[jobs_results_table]
        )
        # Also auto-populate Discover Jobs on load
        demo.load(
            do_search,
            inputs=[search_input, category_filter, experience_filter, workplace_filter, min_score_slider, sort_dropdown],
            outputs=[jobs_results_table]
        )

        # Job Details View
        def do_load_details(jid):
            return get_job_details_view(CURRENT_USER_ID, jid)

        load_job_btn.click(
            do_load_details,
            inputs=[job_id_input],
            outputs=[detail_header, detail_match, detail_summary, detail_contacts, detail_raw]
        )

        # Profile Load & Save
        def do_load_prof():
            return load_user_profile(CURRENT_USER_ID)

        demo.load(
            do_load_prof,
            outputs=[
                prof_degree, prof_field, prof_yoe, prof_roles, prof_locations,
                prof_workplace, prof_emp_type, prof_min_salary, prof_interests,
                prof_declared_table, prof_assessed_table
            ]
        )

        def do_save_prof(deg, fld, y, r, loc, wp, et, sal, intr, n_sk, n_lvl):
            return save_user_profile(CURRENT_USER_ID, deg, fld, y, r, loc, wp, et, sal, intr, n_sk, n_lvl)

        save_prof_btn.click(
            do_save_prof,
            inputs=[
                prof_degree, prof_field, prof_yoe, prof_roles, prof_locations,
                prof_workplace, prof_emp_type, prof_min_salary, prof_interests,
                new_skill_dropdown, new_skill_level
            ],
            outputs=[prof_status_msg, prof_declared_table, prof_assessed_table]
        )

        # Assessments
        def do_load_q(skill):
            return load_question_for_skill(skill)

        load_q_btn.click(
            do_load_q,
            inputs=[assess_skill_select],
            outputs=[q_display, q_options_radio, state_correct, state_rubric]
        )
        # Load initial assessment question on load
        demo.load(
            do_load_q,
            inputs=[assess_skill_select],
            outputs=[q_display, q_options_radio, state_correct, state_rubric]
        )

        def do_submit_q(skill, ans, corr, rub):
            return submit_assessment_attempt(CURRENT_USER_ID, skill, ans, corr, rub)

        submit_answer_btn.click(
            do_submit_q,
            inputs=[assess_skill_select, q_options_radio, state_correct, state_rubric],
            outputs=[assess_feedback, assess_history_table]
        )

        # Skill Gaps
        def do_run_gaps(cat, jid):
            return run_skill_gap_analysis(CURRENT_USER_ID, cat, jid)

        run_gaps_btn.click(
            do_run_gaps,
            inputs=[gap_cat_select, gap_job_id],
            outputs=[gap_explanation_md, gap_high_priority_table, gap_roadmap_table, gap_unassessed_table]
        )

        # Data Sources
        csv_upload_btn.click(
            handle_csv_upload_and_ingest,
            inputs=[csv_file_input],
            outputs=[csv_result_md, sources_runs_table]
        )

        test_conn_btn.click(
            test_source_connection,
            inputs=[sync_source_dropdown, gh_tokens_input, lever_slugs_input, adzuna_id_input, adzuna_key_input, adzuna_country_input],
            outputs=[sync_feedback_md]
        )

        run_sync_btn.click(
            run_manual_source_sync,
            inputs=[sync_source_dropdown, gh_tokens_input, lever_slugs_input, adzuna_id_input, adzuna_key_input, adzuna_country_input],
            outputs=[sync_feedback_md, sources_runs_table]
        )

        # Settings
        save_weights_btn.click(
            update_matching_weights,
            inputs=[w_skill_slider, w_role_slider, w_elig_slider, w_pref_slider],
            outputs=[weights_status_md]
        )

        export_btn.click(
            export_jobs_csv,
            outputs=[export_file_out]
        )

    return demo


# Create app instance
app = build_app()

if __name__ == "__main__":
    app.launch(
        server_name=settings.server_name,
        server_port=settings.server_port,
        css=CUSTOM_CSS,
        theme=gr.themes.Base(),
        share=False
    )
