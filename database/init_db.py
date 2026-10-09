"""
Database Initialization and Seed Data Loader.
Initializes tables, seeds skills taxonomy, assessment questions bank,
and imports synthetic sample jobs if the database is freshly created.
"""

from datetime import datetime
import json
import os
import uuid
import logging

from database.repository import repo
from database.models import Skill, Assessment, AssessmentQuestion
from processing.skills_taxonomy import SKILLS_TAXONOMY
from connectors.kaggle_csv import KaggleCSVConnector
from ingestion.normalize import normalize_job_dict
from ingestion.deduplicate import DeduplicationIndex, filter_duplicates

logger = logging.getLogger(__name__)


def seed_taxonomy():
    """Populates the skills table with canonical skills from taxonomy."""
    session = repo.get_session()
    try:
        existing_names = set(r[0] for r in session.query(Skill.name).all())
        for canonical, data in SKILLS_TAXONOMY.items():
            if canonical not in existing_names:
                skill_obj = Skill(
                    id=str(uuid.uuid4()),
                    name=canonical,
                    category=data["category"],
                    aliases=json.dumps(data.get("aliases", [])),
                    description=f"Standard canonical skill in category {data['category']}.",
                    created_at=datetime.utcnow()
                )
                session.add(skill_obj)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error seeding taxonomy: {e}")
    finally:
        session.close()


def seed_questions():
    """Seeds assessment question bank from data/sample_questions.json."""
    json_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_questions.json")
    if not os.path.exists(json_path):
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            questions_data = json.load(f)

        session = repo.get_session()
        existing_texts = set(r[0] for r in session.query(AssessmentQuestion.question_text).all())

        for q in questions_data:
            q_text = q["question"]
            if q_text in existing_texts:
                continue

            skill_name = q["skill"]
            skill = session.query(Skill).filter(Skill.name == skill_name).first()
            if not skill:
                skill = Skill(
                    id=str(uuid.uuid4()),
                    name=skill_name,
                    category="Software Engineering",
                    aliases=json.dumps([]),
                    created_at=datetime.utcnow()
                )
                session.add(skill)
                session.flush()

            assessment = session.query(Assessment).filter(Assessment.skill_id == skill.id).first()
            if not assessment:
                assessment = Assessment(
                    id=str(uuid.uuid4()),
                    skill_id=skill.id,
                    title=f"{skill_name} Technical Assessment",
                    difficulty="standard",
                    description=f"Demonstrated technical proficiency evaluation for {skill_name}."
                )
                session.add(assessment)
                session.flush()

            q_obj = AssessmentQuestion(
                id=str(uuid.uuid4()),
                assessment_id=assessment.id,
                question_text=q_text,
                question_type=q.get("type", "multiple_choice"),
                options=json.dumps(q.get("options", [])),
                correct_answer=q["correct_answer"],
                rubric=q.get("rubric"),
                test_cases=json.dumps(q.get("test_cases", [])),
                difficulty_level=q.get("difficulty", 2)
            )
            session.add(q_obj)

        session.commit()
    except Exception as e:
        logger.error(f"Error seeding questions: {e}")
    finally:
        session.close()


def seed_sample_jobs():
    """Imports initial synthetic sample jobs if the database has 0 jobs."""
    total_jobs = repo.get_total_jobs_count()
    if total_jobs > 0:
        return

    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_jobs.csv")
    if not os.path.exists(csv_path):
        return

    try:
        connector = KaggleCSVConnector(file_path_or_bytes=csv_path)
        raw_records = connector.fetch_jobs(limit=100)

        existing_ids, existing_hashes = repo.get_existing_hashes_and_ids()
        dedup_index = DeduplicationIndex(existing_ids, existing_hashes)

        from processing.summarize import generate_job_summary
        from processing.extract_contacts import extract_contacts_from_text_and_urls

        accepted_count = 0
        for raw in raw_records:
            norm = normalize_job_dict(raw, source="kaggle_csv")
            if not norm:
                continue

            is_dup, _ = dedup_index.is_duplicate(norm)
            if is_dup:
                continue

            dedup_index.register(norm)

            # Summarize and contacts
            summary_dict = generate_job_summary(
                title=norm.job_title,
                description=norm.job_description,
                required_skills=norm.required_skills,
                preferred_skills=norm.preferred_skills,
                location=norm.location,
                workplace_type=norm.workplace_type
            )
            contacts_dict = extract_contacts_from_text_and_urls(
                description=norm.job_description,
                original_job_url=norm.original_job_url,
                api_apply_url=norm.application_url,
                api_company_url=norm.company_website,
                company_name=norm.company_name
            )

            repo.save_job_record(
                job_data=norm.model_dump(),
                summary_data=summary_dict,
                contact_data=contacts_dict
            )
            accepted_count += 1

        repo.record_ingestion_run(
            source_name="seed_sample_csv",
            status="completed",
            records_fetched=len(raw_records),
            records_accepted=accepted_count,
            duplicates_found=0,
            errors_count=0,
            duration_seconds=0.5,
            log_messages=f"Successfully initialized seed database with {accepted_count} jobs."
        )
    except Exception as e:
        logger.error(f"Error seeding sample jobs: {e}")


def initialize_database():
    """Initializes tables, seeds taxonomy, questions, and synthetic dataset."""
    repo.init_db()
    seed_taxonomy()
    seed_questions()
    seed_sample_jobs()
    # Ensure default user exists with sample declared profile
    user = repo.get_or_create_user(username="default_candidate", email="candidate@pipeline.ai")
    # Add initial declared skills for demonstration
    for skill_name, level in [("Python", 3), ("SQL", 3), ("Git", 2), ("REST APIs", 2), ("Pandas", 3)]:
        repo.set_user_skill(
            user_id=user.id,
            skill_name=skill_name,
            proficiency_level=level,
            source="declared",
            evidence="Self-reported initial profile"
        )
    return user
