"""
Deterministic Role Classification with Interpretable Evidence Scoring.
Classifies jobs into 6 categories based on title patterns, taxonomy skill distributions,
and keyword signals. Does NOT claim to be a calibrated statistical probability.
"""

from typing import Dict, List, Tuple
import re
from processing.skills_taxonomy import SKILLS_TAXONOMY, CATEGORIES

# Category keyword and title patterns
CATEGORY_SIGNALS = {
    "Data Engineering": {
        "title_keywords": [
            r"\bdata\s+engine(?:er|ering)\b",
            r"\betl\s+developer\b",
            r"\bdata\s+platform\s+engineer\b",
            r"\bbig\s+data\s+engineer\b",
            r"\bpipeline\s+engineer\b",
            r"\banalytics\s+engineer\b"
        ],
        "category_skills": ["ETL", "data pipelines", "Apache Spark", "Airflow", "Kafka", "dbt", "data warehousing", "Snowflake", "Databricks"]
    },
    "Data Science and AI/ML": {
        "title_keywords": [
            r"\bdata\s+scientist\b",
            r"\bmachine\s+learning\b",
            r"\bml\s+engineer\b",
            r"\bai\s+engineer\b",
            r"\bnlp\s+engineer\b",
            r"\bcomputer\s+vision\b",
            r"\bdeep\s+learning\b",
            r"\bapplied\s+scientist\b"
        ],
        "category_skills": ["scikit-learn", "feature engineering", "model evaluation", "NLP", "PyTorch", "TensorFlow", "R"]
    },
    "Cloud and DevOps": {
        "title_keywords": [
            r"\bdevops\b",
            r"\bcloud\s+engineer\b",
            r"\bcloud\s+architect\b",
            r"\bsite\s+reliability\b",
            r"\bsre\b",
            r"\binfrastructure\s+engineer\b",
            r"\bplatform\s+engineer\b",
            r"\bsysadmin\b"
        ],
        "category_skills": ["AWS", "S3", "EC2", "Azure", "GCP", "Docker", "Kubernetes", "CI/CD", "Terraform", "Linux"]
    },
    "Data Analytics and BI": {
        "title_keywords": [
            r"\bdata\s+analyst\b",
            r"\bbi\s+developer\b",
            r"\bbusiness\s+intelligence\b",
            r"\breporting\s+analyst\b",
            r"\boperations\s+analyst\b",
            r"\binsights\s+analyst\b"
        ],
        "category_skills": ["Power BI", "Tableau", "Excel", "Data Visualization", "Statistical Analysis"]
    },
    "Software Development": {
        "title_keywords": [
            r"\bsoftware\s+engineer\b",
            r"\bsoftware\s+developer\b",
            r"\bfull[\s-]stack\b",
            r"\bback[\s-]end\b",
            r"\bfront[\s-]end\b",
            r"\bweb\s+developer\b",
            r"\bapplication\s+developer\b",
            r"\bjava\s+developer\b",
            r"\bpython\s+developer\b"
        ],
        "category_skills": ["REST APIs", "FastAPI", "Django", "Flask", "React", "Next.js", "Node.js", "Spring Boot", "Git", "Microservices"]
    }
}


def classify_job(title: str, description: str, detected_skills: List[str]) -> Tuple[str, float, Dict]:
    """
    Classifies a job into one of the 6 canonical categories.
    Returns:
        (category_name, evidence_score, evidence_dict)
    
    Evidence score is an interpretable metric from 0.0 to 1.0 based on rule weights:
    - Title match: 50 points
    - Skill alignment proportion: up to 40 points
    - Body keywords: 10 points
    """
    scores: Dict[str, float] = {cat: 0.0 for cat in CATEGORIES if cat != "Other"}
    evidence_details: Dict[str, Dict] = {cat: {"title_matches": [], "skill_matches": []} for cat in scores}

    title_lower = title.lower()
    desc_lower = description.lower()
    skills_set = set(detected_skills)

    for cat, signals in CATEGORY_SIGNALS.items():
        # Title check (strongest indicator)
        for pat in signals["title_keywords"]:
            if re.search(pat, title_lower):
                scores[cat] += 55.0
                evidence_details[cat]["title_matches"].append(pat)
                break

        # Detected skill alignment
        matched_cat_skills = [s for s in signals["category_skills"] if s in skills_set]
        if matched_cat_skills:
            evidence_details[cat]["skill_matches"] = matched_cat_skills
            # Up to 35 points based on matching category skills
            skill_score = min(35.0, len(matched_cat_skills) * 10.0)
            scores[cat] += skill_score

        # Supporting body keywords (up to 10 points)
        for pat in signals["title_keywords"][:3]:
            if re.search(pat, desc_lower):
                scores[cat] += 5.0
                break

    # Find the top category
    top_cat = "Other"
    best_score = 0.0

    for cat, score in scores.items():
        if score > best_score:
            best_score = score
            top_cat = cat

    # Normalize score between 0.0 and 1.0 (evidence confidence)
    confidence = round(min(1.0, best_score / 100.0), 2)
    if best_score < 20.0:
        top_cat = "Other"
        confidence = 0.15

    top_evidence = evidence_details.get(top_cat, {"title_matches": [], "skill_matches": []})
    top_evidence["raw_points"] = best_score
    top_evidence["note"] = "Interpretable heuristic score, not a statistical probability."

    return (top_cat, confidence, top_evidence)
