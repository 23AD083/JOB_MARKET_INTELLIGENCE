---
title: Job Intelligence Pipeline
emoji: 🎯
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 6.30.0
app_file: app.py
pinned: false
license: mit
---

# Complete Non-LLM Job Intelligence Pipeline

A production-grade, end-to-end **Job Intelligence Pipeline** that ingests job postings across multiple heterogeneous sources, normalizes and deduplicates records, summarizes job descriptions and extracts technical skills using **pure deterministic rules and extractive NLP (Zero Generative LLMs / Zero Paid APIs)**, evaluates user competencies via technical assessments, and calculates explainable personalized job match scores.

Designed to run natively on **CPU environments** and deployable directly to **Hugging Face Spaces**.

---

## 🌟 Key Features

1. **100% Non-Generative / Non-LLM Architecture**:
   - Zero dependency on OpenAI, Anthropic, Gemini, or any paid AI API.
   - Summarization, skill extraction, role classification, and match scoring operate via deterministic token/regex matching, TF-IDF extractive ranking, and structured taxonomy.
   - Extremely cost-effective, predictable, reproducible, and private.

2. **Modular Multi-Source Ingestion**:
   - **Kaggle / Local CSV Datasets**: Flexible column mapping and fallback encoding detection.
   - **Greenhouse Public Boards**: Ingests public job listings for configured participating employers (`canonical`, `automattic`, `airtable`, etc.).
   - **Lever Public Postings**: Ingests structured postings from employers (`coursera`, `atlassian`, etc.).
   - **Adzuna API**: Direct job search integration when API credentials are provided.
   - **Manual Import**: Safe fallback for raw text or single URLs with anti-SSRF protections.
   - **Fault Isolation**: Pipeline continues uninterrupted if one source fails.

3. **Standardized Job Schema & Strict Validation**:
   - Pydantic schema enforcing required fields, URL formats, salary normalization, and workplace modes.
   - Primary deduplication by `(source, source_job_id)`.
   - Secondary deduplication using SHA-256 content hashes (`company`, `title`, `location`, `description`).

4. **Curated Skills Taxonomy & Context-Aware NLP**:
   - Over 40 canonical skills across 7 categories: Programming, Data, Data Engineering, Software Engineering, Cloud & DevOps, AI/ML, and Analytics.
   - Boundary-safe regex rules preventing false positives (e.g. single-letter "R", "Go" as a verb, "C" as language).
   - Distinguishes **required** vs **preferred** qualifications based on section headers.

5. **Explainable Match Scoring**:
   - Transparent heuristic formula:
     $$\text{Score} = (0.60 \times \text{Skill Alignment}) + (0.20 \times \text{Role Alignment}) + (0.10 \times \text{Eligibility}) + (0.10 \times \text{Preferences})$$
   - Distinguishes **declared** skills from **assessed** skills.
   - Provides clear breakdown of matched skills, missing core skills, missing bonus skills, and skills needing assessment.

6. **Demonstrated Skill Assessment Engine**:
   - Technical evaluation engine with question banks across Python, SQL, Java, REST APIs, Git, Docker, and AWS.
   - Safe in-memory SQLite sandbox query execution for SQL assessments.
   - Illustrative 5-tier proficiency scale (0: None, 1: Beginner, 2: Developing, 3: Proficient, 4: Advanced).

7. **Application Link & Contact Provenance**:
   - Separates direct apply URLs, job-board URLs, and official company websites.
   - Extracts recruiter contacts with strict RFC5322 validation and provenance tracking.
   - Blocks SSRF: rejects localhost, RFC1918 private IPs, and cloud metadata endpoints.
   - Never fabricates contact information; clearly shows *"Not publicly listed"* when absent.

8. **Professional Gradio UI**:
   - Clean, restrained dashboard with white/light-gray background and single dark slate accent.
   - 8 Dedicated Tabs: Dashboard, Discover Jobs, Job Details, My Profile, Skill Assessments, Skill Gap Analysis, Data Sources, and Settings.

---

## 🏗️ Project Architecture

```
Job_Market_Analysis/
├── app.py                     # Gradio Web Interface entry point (Hugging Face Spaces compatible)
├── requirements.txt           # Core Python dependencies
├── README.md                  # Hugging Face Spaces frontmatter and documentation
├── .gitignore                 # Excludes local databases, caches, and secrets
├── config/
│   ├── settings.py            # Environment-driven configuration & credential masking
│   └── security.py            # SSRF protection and URL validation utilities
├── connectors/
│   ├── base.py                # BaseJobConnector abstract class
│   ├── kaggle_csv.py          # Flexible CSV ingestion connector
│   ├── greenhouse.py          # Greenhouse public API board connector
│   ├── lever.py               # Lever public postings API connector
│   ├── adzuna.py              # Adzuna job search API connector
│   └── manual.py              # Manual text and SSRF-safe URL import
├── database/
│   ├── models.py              # SQLAlchemy ORM models (SQLite & PostgreSQL compatible)
│   ├── repository.py          # Parameterized data access layer
│   └── init_db.py             # Schema initialization and seed data loader
├── ingestion/
│   ├── validate.py            # Pydantic schema validation
│   ├── normalize.py           # Normalization, HTML cleaning, content hash
│   ├── deduplicate.py         # Primary & secondary deduplication index
│   └── runner.py              # Multi-source ingestion orchestrator & telemetry
├── processing/
│   ├── skills_taxonomy.py     # Canonical taxonomy, categories, aliases, regex
│   ├── extract_skills.py      # Context-aware required/preferred skill extractor
│   ├── classify.py            # Deterministic role classifier with evidence scoring
│   ├── summarize.py           # Extractive non-LLM rule-based summarizer
│   └── extract_contacts.py    # Public contact & direct apply URL extractor
├── matching/
│   ├── score.py               # Explainable match scoring engine
│   └── skill_gaps.py          # Empirical market gap & learning roadmap calculator
├── assessments/
│   ├── question_bank.py       # Technical assessment question loader
│   └── evaluator.py           # MCQ evaluator and in-memory SQL sandbox
├── ui/
│   ├── theme.py               # Clean professional CSS and theme tokens
│   ├── dashboard_tab.py       # Metrics, Plotly category distribution, recent runs
│   ├── jobs_tab.py            # Multi-field search, filters, and match ranking
│   ├── details_tab.py         # Deep-dive view, summary, provenance, raw posting
│   ├── profile_tab.py         # Qualifications form & declared vs assessed skills
│   ├── assessments_tab.py     # Interactive assessment quiz & feedback
│   ├── gaps_tab.py            # Empirical market demand ranking & learning path
│   ├── sources_tab.py         # CSV upload, connector sync, credentials management
│   └── settings_tab.py        # Weight tuning, taxonomy viewer, CSV exporter
├── data/
│   ├── sample_jobs.csv        # Synthetic seed dataset covering 6 categories
│   └── sample_questions.json  # Pre-seeded assessment question bank
└── tests/
    ├── test_app_startup.py    # App startup & initialization test
    ├── test_classify.py       # Role classification tests
    ├── test_connectors.py     # Connector resilience & fault isolation tests
    ├── test_contacts.py       # Contact extraction & anti-SSRF tests
    ├── test_database.py       # SQLAlchemy CRUD & persistence tests
    ├── test_deduplicate.py    # Primary & secondary deduplication tests
    ├── test_matching.py       # Match scoring & gap identification tests
    ├── test_normalize.py      # Field normalization & validation tests
    ├── test_skills.py         # Context-aware skill extraction tests
    └── test_summarize.py      # Rule-based summarization tests
```

---

## 🚀 Quickstart & Local Installation

### 1. Prerequisites
- Python 3.11+
- Git

### 2. Clone and Setup Environment
```bash
git clone https://github.com/your-username/job-intelligence-pipeline.git
cd job-intelligence-pipeline

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run Automated Tests
```bash
# Run the 33 automated tests
python -m pytest -v tests
```

### 4. Launch the Web Interface
```bash
python app.py
```
Open your browser and navigate to `http://localhost:7860`.

---


## 📊 Standardized Schema Reference

Each job is strictly normalized to the following schema:

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `job_id` | String | Deterministic unique identifier (`source_sourceid` or hash) |
| `source` | String | Origin connector (`kaggle_csv`, `greenhouse`, `lever`, etc.) |
| `source_job_id` | String? | Source-specific posting identifier |
| `job_title` | String | Job title |
| `company_name` | String | Employing organization |
| `job_description`| Text | Cleaned text description |
| `location` | String? | Geographical location |
| `country` | String? | Country code |
| `employment_type`| String? | `full-time`, `part-time`, `contract`, `internship` |
| `workplace_type` | String? | `remote`, `hybrid`, `onsite` |
| `experience_level`| String? | `entry`, `mid`, `senior`, `lead` |
| `salary_min` | Float? | Minimum annual compensation |
| `salary_max` | Float? | Maximum annual compensation |
| `salary_currency`| String? | ISO currency code (`USD`, `GBP`, `EUR`) |
| `required_skills`| JSON List | Canonical core skills extracted from text |
| `preferred_skills`| JSON List | Canonical bonus/nice-to-have skills |
| `education_requirements`| String?| Extracted degree requirements |
| `original_job_url`| String? | Source job board link |
| `application_url` | String? | Direct apply link |
| `company_website` | String? | Official employer domain |
| `recruiter_name`  | String? | Verified recruiter name (if published) |
| `recruiter_email` | String? | Validated public email address |
| `recruiter_phone` | String? | Validated public contact number |
| `verification_status`| String | `unverified`, `format_validated`, `verified_reachable` |
| `content_hash`    | String | SHA-256 hash for duplicate detection |
| `category`        | String | Role category (Software Dev, Data Eng, AI/ML, etc.) |

---

## 🔒 Security and Privacy Compliance

- **SSRF Prevention**: All external URLs pass through `config/security.py` which rejects `localhost`, `127.0.0.1`, RFC1918 private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), and AWS/GCP cloud metadata endpoints (`169.254.169.254`, `metadata.google.internal`).
- **No Fabricated Contacts**: Recruiter contacts are extracted strictly from public source postings. The system displays *"Not publicly listed"* whenever details are absent.
- **Safe Sandboxing**: No untrusted arbitrary Python code execution. SQL assessments execute in an in-memory SQLite sandbox with read-only query assertions.
- **Credential Masking**: Secrets and database passwords are never shown in plain text in logs or the UI.

---

## 🧪 Automated Testing Verification

The test suite validates all required pipeline modules:

```bash
$ python -m pytest -v tests
============================= test session starts =============================
tests/test_app_startup.py::test_app_initialization_and_startup PASSED    [  3%]
tests/test_classify.py::test_classify_data_engineering PASSED            [  6%]
tests/test_classify.py::test_classify_ai_ml PASSED                       [  9%]
tests/test_classify.py::test_classify_cloud_devops PASSED                [ 12%]
tests/test_classify.py::test_classify_other_sparse PASSED                [ 15%]
tests/test_connectors.py::test_kaggle_csv_empty_file PASSED              [ 18%]
tests/test_connectors.py::test_manual_connector_text_import PASSED       [ 21%]
tests/test_connectors.py::test_adzuna_unconfigured_credentials PASSED    [ 24%]
tests/test_connectors.py::test_ingestion_runner_fault_isolation PASSED   [ 27%]
tests/test_contacts.py::test_ssrf_url_blocking PASSED                    [ 30%]
tests/test_contacts.py::test_contact_extraction_valid_email_and_phone PASSED [ 33%]
tests/test_contacts.py::test_contact_extraction_no_hallucinations PASSED [ 36%]
tests/test_database.py::test_user_creation_and_profile_update PASSED     [ 39%]
tests/test_database.py::test_save_and_query_job PASSED                   [ 42%]
tests/test_database.py::test_record_assessment_attempt_updates_user_skill PASSED [ 45%]
tests/test_deduplicate.py::test_primary_deduplication PASSED             [ 48%]
tests/test_deduplicate.py::test_secondary_hash_deduplication PASSED      [ 51%]
tests/test_deduplicate.py::test_distinct_jobs_not_deduplicated PASSED    [ 54%]
tests/test_matching.py::test_matching_score_calculation PASSED           [ 57%]
tests/test_matching.py::test_missing_skills_identification PASSED        [ 60%]
tests/test_normalize.py::test_clean_html_text PASSED                     [ 63%]
tests/test_normalize.py::test_parse_salary_string PASSED                 [ 66%]
tests/test_normalize.py::test_normalize_workplace_type PASSED            [ 69%]
tests/test_normalize.py::test_normalize_experience_level PASSED          [ 72%]
tests/test_normalize.py::test_compute_content_hash_consistency PASSED    [ 75%]
tests/test_normalize.py::test_normalize_job_dict_valid PASSED            [ 78%]
tests/test_normalize.py::test_normalize_job_dict_reject_missing_fields PASSED [ 81%]
tests/test_skills.py::test_alias_normalization PASSED                    [ 84%]
tests/test_skills.py::test_avoid_false_positive_single_letter_r PASSED   [ 87%]
tests/test_skills.py::test_avoid_false_positive_go PASSED                [ 90%]
tests/test_skills.py::test_required_vs_preferred_skills_separation PASSED [ 93%]
tests/test_summarize.py::test_extractive_summary_generation PASSED       [ 96%]
tests/test_summarize.py::test_not_specified_fallback_without_guessing PASSED [100%]
============================= 33 passed in 16.27s =============================
```

---
<img width="1620" height="876" alt="Screenshot 2026-10-09 143644" src="https://github.com/user-attachments/assets/2c50e786-a53b-40bf-b719-92d64c333db7" />
<img width="1579" height="606" alt="Screenshot 2026-10-09 143658" src="https://github.com/user-attachments/assets/9c9562bc-d09e-4ad8-a939-df0c8f345ea7" />
<img width="1529" height="879" alt="Screenshot 2026-10-09 143723" src="https://github.com/user-attachments/assets/3e1d156e-086e-4862-a729-a592b415f9e8" />
<img width="1600" height="877" alt="Screenshot 2026-10-09 143710" src="https://github.com/user-attachments/assets/7246b998-cff7-412d-a2ec-3e99171f6423" />


## 📄 License
This project is licensed under the MIT License.
