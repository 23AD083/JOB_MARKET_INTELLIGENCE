"""
SQLAlchemy Database Models for Job Intelligence Pipeline.
Supports SQLite (default) and PostgreSQL with indexes, relationships, and JSON storage.
"""

from datetime import datetime
import json
from typing import Any, List, Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Index,
    UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    skills = relationship("UserSkill", back_populates="user", cascade="all, delete-orphan")
    attempts = relationship("AssessmentAttempt", back_populates="user", cascade="all, delete-orphan")
    matches = relationship("JobMatch", back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    education_degree = Column(String(100), nullable=True)  # e.g., Bachelor's, Master's, Ph.D., Bootcamp
    field_of_study = Column(String(100), nullable=True)
    years_of_experience = Column(Float, default=0.0, nullable=False)
    preferred_roles = Column(Text, default="[]")  # JSON list
    preferred_locations = Column(Text, default="[]")  # JSON list
    workplace_preference = Column(String(20), default="any")  # remote, hybrid, onsite, any
    employment_type_preference = Column(String(30), default="full-time")  # full-time, contract, internship, any
    min_salary = Column(Float, nullable=True)
    career_interests = Column(Text, nullable=True)
    target_companies = Column(Text, default="[]")  # JSON list
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="profile")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)  # Canonical name
    category = Column(String(50), nullable=False, index=True)  # Programming, Data, Cloud, etc.
    aliases = Column(Text, default="[]")  # JSON list of aliases
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user_skills = relationship("UserSkill", back_populates="skill")
    job_skills = relationship("JobSkill", back_populates="skill")
    assessments = relationship("Assessment", back_populates="skill")


class UserSkill(Base):
    __tablename__ = "user_skills"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(String(36), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    proficiency_level = Column(Integer, default=0, nullable=False)  # 0: None, 1: Beginner, 2: Developing, 3: Proficient, 4: Advanced
    skill_source = Column(String(20), default="declared", nullable=False)  # 'declared' vs 'assessed'
    evidence = Column(Text, nullable=True)  # Summary of evidence or question scores
    assessed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", "skill_source", name="uq_user_skill_source"),
    )

    user = relationship("User", back_populates="skills")
    skill = relationship("Skill", back_populates="user_skills")
    evidence_items = relationship("UserSkillEvidence", back_populates="user_skill", cascade="all, delete-orphan")


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String(36), primary_key=True)
    skill_id = Column(String(36), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    difficulty = Column(String(30), default="intermediate")  # beginner, intermediate, advanced
    description = Column(Text, nullable=True)

    skill = relationship("Skill", back_populates="assessments")
    questions = relationship("AssessmentQuestion", back_populates="assessment", cascade="all, delete-orphan")
    attempts = relationship("AssessmentAttempt", back_populates="assessment")


class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"

    id = Column(String(36), primary_key=True)
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(30), default="multiple_choice")  # multiple_choice, sql_query, short_answer
    options = Column(Text, default="[]")  # JSON list of options for multiple choice
    correct_answer = Column(Text, nullable=False)
    rubric = Column(Text, nullable=True)  # Scoring rubric for short answer or query explanation
    test_cases = Column(Text, default="[]")  # JSON list of test cases for SQL query verification
    difficulty_level = Column(Integer, default=1)  # 1 to 4

    assessment = relationship("Assessment", back_populates="questions")


class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    passed = Column(Boolean, default=False)
    proficiency_awarded = Column(Integer, default=1)
    feedback = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="attempts")
    assessment = relationship("Assessment", back_populates="attempts")


class UserSkillEvidence(Base):
    __tablename__ = "user_skill_evidence"

    id = Column(String(36), primary_key=True)
    user_skill_id = Column(String(36), ForeignKey("user_skills.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_id = Column(String(36), ForeignKey("assessment_attempts.id", ondelete="SET NULL"), nullable=True)
    evidence_type = Column(String(50), nullable=False)  # 'assessment_test', 'portfolio', 'certification'
    description = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    user_skill = relationship("UserSkill", back_populates="evidence_items")


class Job(Base):
    __tablename__ = "jobs"

    job_id = Column(String(64), primary_key=True)  # Normalized unique identifier
    source = Column(String(50), nullable=False, index=True)  # kaggle_csv, greenhouse, lever, adzuna, manual
    source_job_id = Column(String(100), nullable=True, index=True)
    job_title = Column(String(250), nullable=False, index=True)
    company_name = Column(String(200), nullable=False, index=True)
    job_description = Column(Text, nullable=False)
    location = Column(String(200), nullable=True)
    country = Column(String(50), nullable=True)
    employment_type = Column(String(50), nullable=True)  # full-time, part-time, contract, internship
    workplace_type = Column(String(20), nullable=True)  # remote, hybrid, onsite
    experience_level = Column(String(50), nullable=True)  # entry, mid, senior, lead, executive
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    salary_currency = Column(String(10), nullable=True)
    required_skills = Column(Text, default="[]")  # JSON list of canonical skill names
    preferred_skills = Column(Text, default="[]")  # JSON list of canonical skill names
    education_requirements = Column(String(200), nullable=True)
    original_job_url = Column(String(500), nullable=True)
    application_url = Column(String(500), nullable=True)
    company_website = Column(String(500), nullable=True)
    recruiter_name = Column(String(150), nullable=True)
    recruiter_email = Column(String(150), nullable=True)
    recruiter_phone = Column(String(50), nullable=True)
    recruiter_profile_url = Column(String(500), nullable=True)
    posted_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_verified_at = Column(DateTime, nullable=True)
    extraction_source = Column(String(100), nullable=True)
    verification_status = Column(String(50), default="unverified", nullable=False)  # unverified, format_validated, verified_reachable
    content_hash = Column(String(64), nullable=False, index=True)  # SHA-256 for duplicate detection
    
    # Classification
    category = Column(String(50), default="Other", nullable=False, index=True)
    category_confidence = Column(Float, default=0.0)

    # Relationships
    job_skills = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")
    summary = relationship("JobSummary", back_populates="job", uselist=False, cascade="all, delete-orphan")
    contact = relationship("JobContact", back_populates="job", uselist=False, cascade="all, delete-orphan")
    matches = relationship("JobMatch", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_job_source_source_id", "source", "source_job_id"),
        Index("idx_job_company_title", "company_name", "job_title"),
    )


class JobSkill(Base):
    __tablename__ = "job_skills"

    id = Column(String(36), primary_key=True)
    job_id = Column(String(64), ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(String(36), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    is_required = Column(Boolean, default=True, nullable=False)
    importance_weight = Column(Float, default=1.0)

    job = relationship("Job", back_populates="job_skills")
    skill = relationship("Skill", back_populates="job_skills")


class JobSummary(Base):
    __tablename__ = "job_summaries"

    id = Column(String(36), primary_key=True)
    job_id = Column(String(64), ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    role_overview = Column(Text, nullable=False)
    key_responsibilities = Column(Text, default="[]")  # JSON list
    required_skills = Column(Text, default="[]")  # JSON list
    preferred_skills = Column(Text, default="[]")  # JSON list
    education_requirements = Column(String(200), default="Not specified")
    experience_requirements = Column(String(200), default="Not specified")
    location_work_mode = Column(String(200), default="Not specified")
    application_deadline = Column(String(100), default="Not specified")
    summary_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    job = relationship("Job", back_populates="summary")


class JobContact(Base):
    __tablename__ = "job_contacts"

    id = Column(String(36), primary_key=True)
    job_id = Column(String(64), ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    original_job_url = Column(String(500), nullable=True)
    application_url = Column(String(500), nullable=True)
    company_website = Column(String(500), nullable=True)
    recruiter_name = Column(String(150), nullable=True)
    recruiter_email = Column(String(150), nullable=True)
    recruiter_phone = Column(String(50), nullable=True)
    recruiter_profile_url = Column(String(500), nullable=True)
    extraction_method = Column(String(100), default="structured_metadata")  # mailto, regex, json_ld, public_posting
    source_page = Column(String(500), nullable=True)
    verification_status = Column(String(50), default="extracted")  # extracted, format_validated, verified_reachable
    last_checked_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    job = relationship("Job", back_populates="contact")


class JobMatch(Base):
    __tablename__ = "job_matches"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(64), ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False, index=True)
    overall_score = Column(Float, nullable=False, index=True)  # 0 to 100
    skill_score = Column(Float, nullable=False)
    role_score = Column(Float, nullable=False)
    eligibility_score = Column(Float, nullable=False)
    preference_score = Column(Float, nullable=False)
    match_category = Column(String(20), nullable=False)  # strong, potential, explore
    matched_skills = Column(Text, default="[]")  # JSON list
    missing_required_skills = Column(Text, default="[]")  # JSON list
    missing_preferred_skills = Column(Text, default="[]")  # JSON list
    skills_needing_assessment = Column(Text, default="[]")  # JSON list
    explanation = Column(Text, nullable=False)
    suggested_learning_priorities = Column(Text, default="[]")  # JSON list
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_job_match"),
    )

    user = relationship("User", back_populates="matches")
    job = relationship("Job", back_populates="matches")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id = Column(String(36), primary_key=True)
    source_name = Column(String(50), nullable=False, index=True)
    status = Column(String(30), nullable=False)  # completed, failed, partial
    records_fetched = Column(Integer, default=0)
    records_accepted = Column(Integer, default=0)
    duplicates_found = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    duration_seconds = Column(Float, default=0.0)
    log_messages = Column(Text, default="")
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)


class SourceConfiguration(Base):
    __tablename__ = "source_configurations"

    id = Column(String(36), primary_key=True)
    source_name = Column(String(50), unique=True, nullable=False)  # greenhouse, lever, adzuna, kaggle_csv
    is_enabled = Column(Boolean, default=True)
    config_json = Column(Text, default="{}")  # Non-sensitive parameters (e.g. board names, endpoints)
    last_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
