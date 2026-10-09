"""
Skill Assessments Tab Component.
Interactive technical assessment runner supporting multiple-choice and SQL sandbox evaluation.
Records attempts, updates assessed proficiency, and displays immediate transparent feedback.
"""

import json
from typing import Dict, List, Optional, Tuple
import pandas as pd
import gradio as gr

from database.repository import repo
from assessments.question_bank import question_bank
from assessments.evaluator import evaluate_multiple_choice, evaluate_sql_query_in_sandbox, calculate_proficiency_level


def load_question_for_skill(skill_name: str) -> Tuple[str, gr.Radio, str, str]:
    """Loads a question for the selected skill."""
    questions = question_bank.get_questions_for_skill(skill_name)
    if not questions:
        return (
            f"No assessment questions currently loaded for {skill_name}.",
            gr.Radio(choices=[], value=None),
            "",
            ""
        )

    q = questions[0]
    q_text = f"### **Question (Difficulty Level {q.get('difficulty', 2)})**\n\n{q['question']}"
    options = q.get("options", [])
    correct = q.get("correct_answer", "")
    rubric = q.get("rubric", "")

    return (q_text, gr.Radio(choices=options, value=None), correct, rubric)


def submit_assessment_attempt(
    user_id: str,
    skill_name: str,
    user_answer: str,
    correct_answer: str,
    rubric: str
) -> Tuple[str, pd.DataFrame]:
    """
    Evaluates assessment submission, awards proficiency, and updates database records.
    """
    if not user_answer:
        return ("Please select or enter an answer before submitting.", pd.DataFrame())

    is_correct, score, feedback = evaluate_multiple_choice(user_answer, correct_answer)
    lvl, lvl_name = calculate_proficiency_level(score)

    # Record in database
    repo.record_assessment_attempt(
        user_id=user_id,
        skill_name=skill_name,
        score=score,
        max_score=100.0,
        passed=is_correct,
        proficiency_level=lvl,
        feedback=feedback
    )

    result_md = f"""### **Assessment Results: {lvl_name} (Level {lvl})**
• **Demonstrated Score**: {score}/100.0
• **Status**: {'Passed' if is_correct else 'Review Needed'}
• **Feedback**: {feedback}
• **Rubric / Context**: {rubric}

> **Disclaimer**: Demonstrated skill assessments reflect performance on specific structured tasks and indicators, not an absolute guarantee of workplace competence.
"""

    # Reload user assessed skills
    user_skills = repo.get_user_skills(user_id)
    assessed_rows = []
    level_names = {0: "0 (None)", 1: "1 (Beginner)", 2: "2 (Developing)", 3: "3 (Proficient)", 4: "4 (Advanced)"}

    for us in user_skills:
        if us["skill_source"] == "assessed":
            assessed_rows.append({
                "Skill": us["skill_name"],
                "Category": us["category"],
                "Demonstrated Level": level_names.get(us["proficiency_level"], str(us["proficiency_level"])),
                "Evidence": us.get("evidence"),
                "Assessed Timestamp": us.get("assessed_at")
            })

    df = pd.DataFrame(assessed_rows) if assessed_rows else pd.DataFrame(columns=["Skill", "Category", "Demonstrated Level", "Evidence", "Assessed Timestamp"])
    return (result_md, df)
