"""
Database Repository and Data Access Layer.
Handles parameterized queries, transactions, relationship cascading,
and thread-safe SQLAlchemy sessions for both SQLite and PostgreSQL.
"""

from datetime import datetime
import json
import os
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import create_engine, desc, func, or_, text
from sqlalchemy.orm import sessionmaker, scoped_session, joinedload

from config.settings import settings
from database.models import (
    Base,
    User,
    UserProfile,
    Skill,
    UserSkill,
    Assessment,
    AssessmentQuestion,
    AssessmentAttempt,
    UserSkillEvidence,
    Job,
    JobSkill,
    JobSummary,
    JobContact,
    JobMatch,
    IngestionRun,
    SourceConfiguration
)


class DatabaseRepository:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or settings.database_url
        # If SQLite, ensure data directory exists
        if self.db_url.startswith("sqlite:///"):
            sqlite_path = self.db_url.replace("sqlite:///", "")
            parent_dir = os.path.dirname(sqlite_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

        # Create engine
        connect_args = {"check_same_thread": False} if self.db_url.startswith("sqlite") else {}
        self.engine = create_engine(self.db_url, connect_args=connect_args, pool_pre_ping=True)
        self.SessionFactory = scoped_session(sessionmaker(bind=self.engine, expire_on_commit=False, autoflush=False, autocommit=False))

    def init_db(self):
        """Creates all database tables defined in Base metadata."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self):
        return self.SessionFactory()

    # ------------------ Jobs & Ingestion ------------------

    def save_job_record(
        self,
        job_data: Dict[str, Any],
        summary_data: Optional[Dict[str, Any]] = None,
        contact_data: Optional[Dict[str, Any]] = None
    ) -> Job:
        """Saves or updates a normalized job record, summary, and contact information."""
        session = self.get_session()
        try:
            job_id = job_data["job_id"]
            existing = session.query(Job).filter(Job.job_id == job_id).first()

            if not existing:
                existing = Job(
                    job_id=job_id,
                    source=job_data["source"],
                    source_job_id=job_data.get("source_job_id"),
                    job_title=job_data["job_title"],
                    company_name=job_data["company_name"],
                    job_description=job_data["job_description"],
                    location=job_data.get("location"),
                    country=job_data.get("country"),
                    employment_type=job_data.get("employment_type"),
                    workplace_type=job_data.get("workplace_type"),
                    experience_level=job_data.get("experience_level"),
                    salary_min=job_data.get("salary_min"),
                    salary_max=job_data.get("salary_max"),
                    salary_currency=job_data.get("salary_currency", "USD"),
                    required_skills=json.dumps(job_data.get("required_skills", [])),
                    preferred_skills=json.dumps(job_data.get("preferred_skills", [])),
                    education_requirements=job_data.get("education_requirements"),
                    original_job_url=job_data.get("original_job_url"),
                    application_url=job_data.get("application_url"),
                    company_website=job_data.get("company_website"),
                    recruiter_name=job_data.get("recruiter_name"),
                    recruiter_email=job_data.get("recruiter_email"),
                    recruiter_phone=job_data.get("recruiter_phone"),
                    recruiter_profile_url=job_data.get("recruiter_profile_url"),
                    posted_at=job_data.get("posted_at"),
                    fetched_at=job_data.get("fetched_at", datetime.utcnow()),
                    last_verified_at=job_data.get("last_verified_at", datetime.utcnow()),
                    extraction_source=job_data.get("extraction_source"),
                    verification_status=job_data.get("verification_status", "unverified"),
                    content_hash=job_data["content_hash"],
                    category=job_data.get("category", "Other"),
                    category_confidence=job_data.get("category_confidence", 0.0)
                )
                session.add(existing)
            else:
                # Update last verified and links if better
                existing.last_verified_at = datetime.utcnow()
                if job_data.get("application_url") and not existing.application_url:
                    existing.application_url = job_data["application_url"]

            session.flush()

            # Save Summary
            if summary_data:
                existing_summary = session.query(JobSummary).filter(JobSummary.job_id == job_id).first()
                if not existing_summary:
                    summary_obj = JobSummary(
                        id=str(uuid.uuid4()),
                        job_id=job_id,
                        role_overview=summary_data.get("role_overview", ""),
                        key_responsibilities=json.dumps(summary_data.get("key_responsibilities", [])),
                        required_skills=json.dumps(summary_data.get("required_skills", [])),
                        preferred_skills=json.dumps(summary_data.get("preferred_skills", [])),
                        education_requirements=summary_data.get("education_requirements", "Not specified"),
                        experience_requirements=summary_data.get("experience_requirements", "Not specified"),
                        location_work_mode=summary_data.get("location_work_mode", "Not specified"),
                        application_deadline=summary_data.get("application_deadline", "Not specified"),
                        summary_text=summary_data.get("summary_text", "")
                    )
                    session.add(summary_obj)

            # Save Contact
            if contact_data:
                existing_contact = session.query(JobContact).filter(JobContact.job_id == job_id).first()
                if not existing_contact:
                    contact_obj = JobContact(
                        id=str(uuid.uuid4()),
                        job_id=job_id,
                        original_job_url=contact_data.get("original_job_url"),
                        application_url=contact_data.get("application_url"),
                        company_website=contact_data.get("company_website"),
                        recruiter_name=contact_data.get("recruiter_name"),
                        recruiter_email=contact_data.get("recruiter_email"),
                        recruiter_phone=contact_data.get("recruiter_phone"),
                        recruiter_profile_url=contact_data.get("recruiter_profile_url"),
                        extraction_method=contact_data.get("extraction_method", "structured_metadata"),
                        source_page=contact_data.get("source_page"),
                        verification_status=contact_data.get("verification_status", "extracted"),
                        last_checked_at=datetime.utcnow()
                    )
                    session.add(contact_obj)

            session.commit()
            return session.query(Job).options(joinedload(Job.summary), joinedload(Job.contact)).filter(Job.job_id == job_id).first()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_existing_hashes_and_ids(self) -> Tuple[set, set]:
        """Returns sets of (source, source_job_id) and content_hash for deduplication."""
        session = self.get_session()
        try:
            source_ids = set()
            for r in session.query(Job.source, Job.source_job_id).filter(Job.source_job_id != None).all():
                source_ids.add((r[0], r[1]))
            hashes = set(r[0] for r in session.query(Job.content_hash).all())
            return (source_ids, hashes)
        finally:
            session.close()

    def get_all_jobs(
        self,
        query_str: Optional[str] = None,
        category: Optional[str] = None,
        experience: Optional[str] = None,
        workplace_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Job]:
        """Queries jobs with parameterized search and filtering."""
        session = self.get_session()
        try:
            q = session.query(Job)
            if query_str and query_str.strip():
                term = f"%{query_str.strip()}%"
                q = q.filter(
                    or_(
                        Job.job_title.ilike(term),
                        Job.company_name.ilike(term),
                        Job.location.ilike(term),
                        Job.required_skills.ilike(term),
                        Job.job_description.ilike(term)
                    )
                )
            if category and category != "All":
                q = q.filter(Job.category == category)
            if experience and experience != "All":
                q = q.filter(Job.experience_level == experience.lower())
            if workplace_type and workplace_type != "All":
                q = q.filter(Job.workplace_type == workplace_type.lower())

            q = q.order_by(desc(Job.fetched_at))
            return q.offset(offset).limit(limit).all()
        finally:
            session.close()

    def get_job_by_id(self, job_id: str) -> Optional[Job]:
        session = self.get_session()
        try:
            return session.query(Job).options(joinedload(Job.summary), joinedload(Job.contact)).filter(Job.job_id == job_id).first()
        finally:
            session.close()

    def get_total_jobs_count(self) -> int:
        session = self.get_session()
        try:
            return session.query(func.count(Job.job_id)).scalar() or 0
        finally:
            session.close()

    def get_category_counts(self) -> Dict[str, int]:
        session = self.get_session()
        try:
            results = session.query(Job.category, func.count(Job.job_id)).group_by(Job.category).all()
            return {cat: count for cat, count in results}
        finally:
            session.close()

    def get_source_counts(self) -> Dict[str, int]:
        session = self.get_session()
        try:
            results = session.query(Job.source, func.count(Job.job_id)).group_by(Job.source).all()
            return {src: count for src, count in results}
        finally:
            session.close()

    # ------------------ Ingestion Run Tracking ------------------

    def record_ingestion_run(
        self,
        source_name: str,
        status: str,
        records_fetched: int,
        records_accepted: int,
        duplicates_found: int,
        errors_count: int,
        duration_seconds: float,
        log_messages: str
    ) -> IngestionRun:
        session = self.get_session()
        try:
            run = IngestionRun(
                id=str(uuid.uuid4()),
                source_name=source_name,
                status=status,
                records_fetched=records_fetched,
                records_accepted=records_accepted,
                duplicates_found=duplicates_found,
                errors_count=errors_count,
                duration_seconds=round(duration_seconds, 2),
                log_messages=log_messages,
                started_at=datetime.utcnow(),
                finished_at=datetime.utcnow()
            )
            session.add(run)
            session.commit()
            return run
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_recent_ingestion_runs(self, limit: int = 10) -> List[IngestionRun]:
        session = self.get_session()
        try:
            return session.query(IngestionRun).order_by(desc(IngestionRun.started_at)).limit(limit).all()
        finally:
            session.close()

    # ------------------ User Profile & Skills ------------------

    def get_or_create_user(self, username: str = "default_user", email: Optional[str] = None) -> User:
        session = self.get_session()
        try:
            user = session.query(User).filter(User.username == username).first()
            if not user:
                user = User(
                    id=str(uuid.uuid4()),
                    username=username,
                    email=email or f"{username}@local.dev",
                    created_at=datetime.utcnow()
                )
                session.add(user)
                session.flush()

                # Create default empty profile
                profile = UserProfile(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    education_degree="Bachelor's",
                    field_of_study="Computer Science",
                    years_of_experience=3.0,
                    preferred_roles=json.dumps(["Software Development", "Data Engineering"]),
                    preferred_locations=json.dumps(["Remote", "New York", "San Francisco"]),
                    workplace_preference="any",
                    employment_type_preference="full-time",
                    min_salary=80000.0,
                    career_interests="Backend engineering, data pipelines, and scalable distributed architectures.",
                    target_companies=json.dumps([])
                )
                session.add(profile)
                session.commit()
            return user
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        session = self.get_session()
        try:
            return session.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        finally:
            session.close()

    def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> UserProfile:
        session = self.get_session()
        try:
            prof = session.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if not prof:
                prof = UserProfile(id=str(uuid.uuid4()), user_id=user_id)
                session.add(prof)

            for key, val in profile_data.items():
                if hasattr(prof, key):
                    if isinstance(val, (list, dict)):
                        setattr(prof, key, json.dumps(val))
                    else:
                        setattr(prof, key, val)

            prof.updated_at = datetime.utcnow()
            session.commit()
            return prof
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_user_skills(self, user_id: str) -> List[Dict[str, Any]]:
        """Returns all skills for a user with category, proficiency, and source (declared vs assessed)."""
        session = self.get_session()
        try:
            records = session.query(UserSkill, Skill).join(Skill, UserSkill.skill_id == Skill.id).filter(UserSkill.user_id == user_id).all()
            result = []
            for us, sk in records:
                result.append({
                    "skill_name": sk.name,
                    "category": sk.category,
                    "proficiency_level": us.proficiency_level,
                    "skill_source": us.skill_source,
                    "evidence": us.evidence,
                    "assessed_at": us.assessed_at.isoformat() if us.assessed_at else None
                })
            return result
        finally:
            session.close()

    def set_user_skill(
        self,
        user_id: str,
        skill_name: str,
        proficiency_level: int,
        source: str = "declared",
        evidence: Optional[str] = None
    ):
        """Sets or updates a user skill, keeping declared vs assessed separate."""
        session = self.get_session()
        try:
            # Find or create skill in skills table
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

            # Find user skill for this source
            user_skill = session.query(UserSkill).filter(
                UserSkill.user_id == user_id,
                UserSkill.skill_id == skill.id,
                UserSkill.skill_source == source
            ).first()

            if not user_skill:
                user_skill = UserSkill(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    skill_id=skill.id,
                    skill_source=source,
                    proficiency_level=proficiency_level,
                    evidence=evidence,
                    assessed_at=datetime.utcnow() if source == "assessed" else None
                )
                session.add(user_skill)
            else:
                user_skill.proficiency_level = proficiency_level
                user_skill.evidence = evidence
                if source == "assessed":
                    user_skill.assessed_at = datetime.utcnow()

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ------------------ Assessments ------------------

    def record_assessment_attempt(
        self,
        user_id: str,
        skill_name: str,
        score: float,
        max_score: float,
        passed: bool,
        proficiency_level: int,
        feedback: str
    ) -> AssessmentAttempt:
        session = self.get_session()
        try:
            # Find skill
            skill = session.query(Skill).filter(Skill.name == skill_name).first()
            if not skill:
                skill = Skill(id=str(uuid.uuid4()), name=skill_name, category="General")
                session.add(skill)
                session.flush()

            # Find or create assessment record
            assessment = session.query(Assessment).filter(Assessment.skill_id == skill.id).first()
            if not assessment:
                assessment = Assessment(
                    id=str(uuid.uuid4()),
                    skill_id=skill.id,
                    title=f"{skill_name} Proficiency Assessment",
                    difficulty="standard"
                )
                session.add(assessment)
                session.flush()

            attempt = AssessmentAttempt(
                id=str(uuid.uuid4()),
                user_id=user_id,
                assessment_id=assessment.id,
                score=score,
                max_score=max_score,
                passed=passed,
                proficiency_awarded=proficiency_level,
                feedback=feedback,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            session.add(attempt)
            session.commit()

            # Automatically update user_skills with assessed proficiency
            self.set_user_skill(
                user_id=user_id,
                skill_name=skill_name,
                proficiency_level=proficiency_level,
                source="assessed",
                evidence=f"Demonstrated in assessment: {score}/{max_score} pts ({feedback[:100]})"
            )

            return attempt
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ------------------ Job Matches ------------------

    def save_job_match(self, match_data: Dict[str, Any]):
        session = self.get_session()
        try:
            user_id = match_data["user_id"]
            job_id = match_data["job_id"]
            existing = session.query(JobMatch).filter(
                JobMatch.user_id == user_id,
                JobMatch.job_id == job_id
            ).first()

            if not existing:
                existing = JobMatch(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    job_id=job_id,
                    overall_score=match_data["overall_score"],
                    skill_score=match_data["skill_score"],
                    role_score=match_data["role_score"],
                    eligibility_score=match_data["eligibility_score"],
                    preference_score=match_data["preference_score"],
                    match_category=match_data["match_category"],
                    matched_skills=json.dumps(match_data.get("matched_skills", [])),
                    missing_required_skills=json.dumps(match_data.get("missing_required_skills", [])),
                    missing_preferred_skills=json.dumps(match_data.get("missing_preferred_skills", [])),
                    skills_needing_assessment=json.dumps(match_data.get("skills_needing_assessment", [])),
                    explanation=match_data["explanation"],
                    suggested_learning_priorities=json.dumps(match_data.get("suggested_learning_priorities", [])),
                    calculated_at=datetime.utcnow()
                )
                session.add(existing)
            else:
                existing.overall_score = match_data["overall_score"]
                existing.skill_score = match_data["skill_score"]
                existing.role_score = match_data["role_score"]
                existing.eligibility_score = match_data["eligibility_score"]
                existing.preference_score = match_data["preference_score"]
                existing.match_category = match_data["match_category"]
                existing.matched_skills = json.dumps(match_data.get("matched_skills", []))
                existing.missing_required_skills = json.dumps(match_data.get("missing_required_skills", []))
                existing.missing_preferred_skills = json.dumps(match_data.get("missing_preferred_skills", []))
                existing.skills_needing_assessment = json.dumps(match_data.get("skills_needing_assessment", []))
                existing.explanation = match_data["explanation"]
                existing.suggested_learning_priorities = json.dumps(match_data.get("suggested_learning_priorities", []))
                existing.calculated_at = datetime.utcnow()

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_user_matches(self, user_id: str, limit: int = 50) -> List[Tuple[JobMatch, Job]]:
        session = self.get_session()
        try:
            return session.query(JobMatch, Job).join(Job, JobMatch.job_id == Job.job_id)\
                .filter(JobMatch.user_id == user_id)\
                .order_by(desc(JobMatch.overall_score))\
                .limit(limit).all()
        finally:
            session.close()


# Singleton repository instance
repo = DatabaseRepository()
