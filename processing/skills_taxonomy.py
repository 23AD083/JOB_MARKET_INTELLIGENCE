"""
Curated Skills Taxonomy and Context-Aware Normalization.
Contains canonical names, categories, aliases, and regex-safe boundaries to eliminate false positives.
"""

from typing import Dict, List, Optional, Set
import re

# Comprehensive Skills Taxonomy
# Format: Canonical Name -> { category, aliases, regex_pattern (optional override), related_skills }
SKILLS_TAXONOMY: Dict[str, Dict] = {
    # Programming
    "Python": {
        "category": "Programming",
        "aliases": ["python3", "python 3", "py"],
        "regex": r"\b(python(?:3|\s*3)?)\b",
        "related": ["Pandas", "NumPy", "FastAPI", "Django"]
    },
    "Java": {
        "category": "Programming",
        "aliases": ["core java", "java 8", "java 11", "java 17", "java 21"],
        "regex": r"\bjava\b(?!\s*script)",
        "related": ["Spring Boot", "REST APIs"]
    },
    "C++": {
        "category": "Programming",
        "aliases": ["cpp", "c plus plus"],
        "regex": r"\b(c\+\+|cpp|c\s+plus\s+plus)\b",
        "related": ["C", "Software Engineering"]
    },
    "C#": {
        "category": "Programming",
        "aliases": ["csharp", "c sharp", ".net"],
        "regex": r"\b(c#|csharp|c\s+sharp|\.net\s+core|\.net)\b",
        "related": ["Software Engineering"]
    },
    "JavaScript": {
        "category": "Programming",
        "aliases": ["js", "es6", "vanilla js"],
        "regex": r"\b(javascript|js|es6)\b",
        "related": ["TypeScript", "React", "Node.js"]
    },
    "TypeScript": {
        "category": "Programming",
        "aliases": ["ts"],
        "regex": r"\b(typescript|ts)\b",
        "related": ["JavaScript", "React", "Node.js"]
    },
    "Golang": {
        "category": "Programming",
        "aliases": ["go", "go lang", "golang"],
        # Context-aware: do not match english verb 'go'
        "regex": r"\b(golang|go\s+language|go\s+programming|(?:python|c\+\+|java)\s*,\s*go\b|\bgo\s*,\s*(?:python|rust|docker))\b",
        "related": ["Docker", "Kubernetes", "Microservices"]
    },
    "Rust": {
        "category": "Programming",
        "aliases": ["rust-lang", "rustlang"],
        "regex": r"\b(rust\s+programming|rustlang|rust\s+language|\brust\b(?=\s*(?:developer|engineer|code|backend)))\b",
        "related": ["C++", "Software Engineering"]
    },
    "R": {
        "category": "Programming",
        "aliases": ["r-project", "r stats"],
        # Context-aware: do not match single letter 'R' inside text unless R programming / stats / language
        "regex": r"\b(r\s+programming|r\s+language|r\s+statistical|r\s*\/python|python\/r|r\s*and\s*python)\b",
        "related": ["Python", "Statistical Analysis", "Data Analytics and BI"]
    },

    # Data & Databases
    "SQL": {
        "category": "Data",
        "aliases": ["structured query language", "relational database", "ansi sql"],
        "regex": r"\b(sql|structured\s+query\s+language)\b",
        "related": ["PostgreSQL", "MySQL", "Pandas", "ETL"]
    },
    "PostgreSQL": {
        "category": "Data",
        "aliases": ["postgres", "pgsql"],
        "regex": r"\b(postgresql|postgres|pgsql)\b",
        "related": ["SQL", "Databases"]
    },
    "MySQL": {
        "category": "Data",
        "aliases": ["mariadb"],
        "regex": r"\b(mysql|mariadb)\b",
        "related": ["SQL"]
    },
    "MongoDB": {
        "category": "Data",
        "aliases": ["mongo", "nosql"],
        "regex": r"\b(mongodb|mongo|nosql)\b",
        "related": ["Databases"]
    },
    "Redis": {
        "category": "Data",
        "aliases": ["redis cache"],
        "regex": r"\b(redis)\b",
        "related": ["Databases", "Microservices"]
    },
    "Pandas": {
        "category": "Data",
        "aliases": ["pandas library"],
        "regex": r"\b(pandas)\b",
        "related": ["Python", "NumPy", "Data Analytics and BI"]
    },
    "NumPy": {
        "category": "Data",
        "aliases": ["numpy library"],
        "regex": r"\b(numpy)\b",
        "related": ["Python", "Pandas", "scikit-learn"]
    },
    "Snowflake": {
        "category": "Data",
        "aliases": ["snowflake data warehouse"],
        "regex": r"\b(snowflake(?:\s+data\s+warehouse)?)\b",
        "related": ["SQL", "data warehousing", "ETL"]
    },
    "BigQuery": {
        "category": "Data",
        "aliases": ["google bigquery", "gbq"],
        "regex": r"\b(bigquery|google\s+bigquery|gbq)\b",
        "related": ["SQL", "GCP", "data warehousing"]
    },

    # Data Engineering
    "ETL": {
        "category": "Data Engineering",
        "aliases": ["elt", "extract transform load"],
        "regex": r"\b(etl|elt|extract\s*,\s*transform\s*,\s*load|data\s+pipelines?)\b",
        "related": ["Airflow", "Apache Spark", "SQL", "data warehousing"]
    },
    "data pipelines": {
        "category": "Data Engineering",
        "aliases": ["data pipeline", "pipeline architecture"],
        "regex": r"\b(data\s+pipelines?|pipeline\s+architecture)\b",
        "related": ["ETL", "Airflow", "Kafka"]
    },
    "Apache Spark": {
        "category": "Data Engineering",
        "aliases": ["spark", "pyspark", "spark streaming"],
        "regex": r"\b(apache\s+spark|spark|pyspark)\b",
        "related": ["Hadoop", "Data Engineering", "Databricks"]
    },
    "Airflow": {
        "category": "Data Engineering",
        "aliases": ["apache airflow", "workflow orchestration"],
        "regex": r"\b(apache\s+airflow|airflow)\b",
        "related": ["ETL", "data pipelines", "Python"]
    },
    "Kafka": {
        "category": "Data Engineering",
        "aliases": ["apache kafka", "event streaming"],
        "regex": r"\b(apache\s+kafka|kafka)\b",
        "related": ["data pipelines", "Microservices"]
    },
    "dbt": {
        "category": "Data Engineering",
        "aliases": ["data build tool"],
        # Context-aware: match dbt in data engineering context
        "regex": r"\b(dbt|data\s+build\s+tool)\b",
        "related": ["SQL", "Snowflake", "BigQuery"]
    },
    "data warehousing": {
        "category": "Data Engineering",
        "aliases": ["data warehouse", "dwh", "star schema", "dimensional modeling"],
        "regex": r"\b(data\s+warehous(?:e|ing)|dwh|dimensional\s+modeling)\b",
        "related": ["Snowflake", "BigQuery", "SQL"]
    },
    "Databricks": {
        "category": "Data Engineering",
        "aliases": ["databricks lakehouse", "delta lake"],
        "regex": r"\b(databricks|delta\s+lake)\b",
        "related": ["Apache Spark", "Python", "Data Engineering"]
    },

    # Software Engineering
    "REST APIs": {
        "category": "Software Engineering",
        "aliases": ["rest api", "restful", "restful api", "rest services", "web api"],
        "regex": r"\b(rest\s+apis?|restful(?:\s+apis?)?|web\s+apis?)\b",
        "related": ["FastAPI", "Django", "Flask", "Spring Boot"]
    },
    "FastAPI": {
        "category": "Software Engineering",
        "aliases": ["fastapi framework"],
        "regex": r"\b(fastapi)\b",
        "related": ["Python", "REST APIs", "Docker"]
    },
    "Django": {
        "category": "Software Engineering",
        "aliases": ["django framework", "django rest framework", "drf"],
        "regex": r"\b(django(?:\s+rest\s+framework)?|drf)\b",
        "related": ["Python", "REST APIs", "SQL"]
    },
    "Flask": {
        "category": "Software Engineering",
        "aliases": ["flask framework"],
        "regex": r"\b(flask(?:\s+framework)?)\b",
        "related": ["Python", "REST APIs"]
    },
    "React": {
        "category": "Software Engineering",
        "aliases": ["reactjs", "react.js", "react native"],
        "regex": r"\b(react|reactjs|react\.js)\b",
        "related": ["JavaScript", "TypeScript", "Next.js"]
    },
    "Next.js": {
        "category": "Software Engineering",
        "aliases": ["nextjs", "next.js framework"],
        "regex": r"\b(nextjs|next\.js)\b",
        "related": ["React", "TypeScript", "JavaScript"]
    },
    "Node.js": {
        "category": "Software Engineering",
        "aliases": ["nodejs", "node"],
        "regex": r"\b(nodejs|node\.js|node(?=\s+backend|\s+server))\b",
        "related": ["JavaScript", "TypeScript", "REST APIs"]
    },
    "Spring Boot": {
        "category": "Software Engineering",
        "aliases": ["spring", "spring framework"],
        "regex": r"\b(spring\s+boot|spring\s+framework|spring)\b",
        "related": ["Java", "Microservices", "REST APIs"]
    },
    "Git": {
        "category": "Software Engineering",
        "aliases": ["github", "gitlab", "version control"],
        # Avoid matching 'git' in accidental substring
        "regex": r"\b(git|github|gitlab|version\s+control)\b",
        "related": ["CI/CD", "Software Engineering"]
    },
    "Microservices": {
        "category": "Software Engineering",
        "aliases": ["microservice architecture", "distributed systems"],
        "regex": r"\b(microservices?|microservice\s+architecture|distributed\s+systems?)\b",
        "related": ["Docker", "Kubernetes", "REST APIs"]
    },
    "GraphQL": {
        "category": "Software Engineering",
        "aliases": ["graphql api"],
        "regex": r"\b(graphql)\b",
        "related": ["REST APIs", "Node.js"]
    },

    # Cloud and DevOps
    "AWS": {
        "category": "Cloud and DevOps",
        "aliases": ["amazon web services", "aws cloud"],
        "regex": r"\b(aws|amazon\s+web\s+services)\b",
        "related": ["S3", "EC2", "Cloud and DevOps"]
    },
    "S3": {
        "category": "Cloud and DevOps",
        "aliases": ["amazon s3", "aws s3"],
        "regex": r"\b(aws\s+s3|amazon\s+s3|\bs3\s+buckets?|\bs3\b(?=\s+storage|\s+api))\b",
        "related": ["AWS", "Cloud and DevOps"]
    },
    "EC2": {
        "category": "Cloud and DevOps",
        "aliases": ["amazon ec2", "aws ec2"],
        "regex": r"\b(aws\s+ec2|amazon\s+ec2|\bec2\s+instances?|\bec2\b)\b",
        "related": ["AWS", "Cloud and DevOps"]
    },
    "Azure": {
        "category": "Cloud and DevOps",
        "aliases": ["microsoft azure", "azure cloud"],
        "regex": r"\b(azure|microsoft\s+azure)\b",
        "related": ["Cloud and DevOps"]
    },
    "GCP": {
        "category": "Cloud and DevOps",
        "aliases": ["google cloud platform", "google cloud"],
        "regex": r"\b(gcp|google\s+cloud(?:\s+platform)?)\b",
        "related": ["Cloud and DevOps", "BigQuery"]
    },
    "Docker": {
        "category": "Cloud and DevOps",
        "aliases": ["containerization", "containers", "docker-compose"],
        "regex": r"\b(docker|containerization|containers?|docker-compose)\b",
        "related": ["Kubernetes", "CI/CD"]
    },
    "Kubernetes": {
        "category": "Cloud and DevOps",
        "aliases": ["k8s"],
        "regex": r"\b(kubernetes|k8s)\b",
        "related": ["Docker", "Cloud and DevOps"]
    },
    "CI/CD": {
        "category": "Cloud and DevOps",
        "aliases": ["cicd", "continuous integration", "continuous deployment"],
        "regex": r"\b(ci\/cd|cicd|continuous\s+integration|continuous\s+deployment)\b",
        "related": ["Git", "Docker", "Jenkins"]
    },
    "Terraform": {
        "category": "Cloud and DevOps",
        "aliases": ["infrastructure as code", "iac"],
        "regex": r"\b(terraform|infrastructure\s+as\s+code|iac)\b",
        "related": ["AWS", "Azure", "Cloud and DevOps"]
    },
    "Linux": {
        "category": "Cloud and DevOps",
        "aliases": ["unix", "bash", "shell scripting"],
        "regex": r"\b(linux|unix|bash|shell\s+scripting)\b",
        "related": ["Cloud and DevOps"]
    },

    # AI and ML
    "scikit-learn": {
        "category": "AI and ML",
        "aliases": ["sklearn", "scikit learn"],
        "regex": r"\b(scikit-learn|sklearn|scikit\s+learn)\b",
        "related": ["Python", "feature engineering", "model evaluation"]
    },
    "feature engineering": {
        "category": "AI and ML",
        "aliases": ["feature extraction", "feature selection"],
        "regex": r"\b(feature\s+engineering|feature\s+extraction|feature\s+selection)\b",
        "related": ["scikit-learn", "Python", "AI and ML"]
    },
    "model evaluation": {
        "category": "AI and ML",
        "aliases": ["cross-validation", "model validation", "metrics evaluation"],
        "regex": r"\b(model\s+evaluation|cross-validation|model\s+validation|roc-auc|confusion\s+matrix)\b",
        "related": ["scikit-learn", "AI and ML"]
    },
    "NLP": {
        "category": "AI and ML",
        "aliases": ["natural language processing", "text processing"],
        "regex": r"\b(nlp|natural\s+language\s+processing|text\s+processing)\b",
        "related": ["Python", "AI and ML"]
    },
    "PyTorch": {
        "category": "AI and ML",
        "aliases": ["torch"],
        "regex": r"\b(pytorch|torch(?=\s+library|\s+tensors|\s+nn))\b",
        "related": ["Python", "Deep Learning"]
    },
    "TensorFlow": {
        "category": "AI and ML",
        "aliases": ["keras", "tf"],
        "regex": r"\b(tensorflow|keras|tf(?=\s+model|\s+keras))\b",
        "related": ["Python", "Deep Learning"]
    },

    # Data Analytics and BI
    "Power BI": {
        "category": "Data Analytics and BI",
        "aliases": ["powerbi", "dax"],
        "regex": r"\b(power\s*bi|powerbi|dax)\b",
        "related": ["Excel", "SQL", "Tableau"]
    },
    "Tableau": {
        "category": "Data Analytics and BI",
        "aliases": ["tableau desktop", "tableau server"],
        "regex": r"\b(tableau(?:\s+desktop|\s+server)?)\b",
        "related": ["Power BI", "SQL", "Data Visualization"]
    },
    "Excel": {
        "category": "Data Analytics and BI",
        "aliases": ["ms excel", "spreadsheets", "vlookup"],
        "regex": r"\b(excel|ms\s+excel|spreadsheets?|advanced\s+excel)\b",
        "related": ["Power BI", "SQL"]
    },
    "Data Visualization": {
        "category": "Data Analytics and BI",
        "aliases": ["data viz", "dashboarding", "visualizations"],
        "regex": r"\b(data\s+visualization|data\s+viz|dashboarding|visualizations?)\b",
        "related": ["Power BI", "Tableau", "Looker"]
    },
    "Statistical Analysis": {
        "category": "Data Analytics and BI",
        "aliases": ["statistics", "hypothesis testing", "regression analysis"],
        "regex": r"\b(statistical\s+analysis|hypothesis\s+testing|regression\s+analysis|inferential\s+statistics)\b",
        "related": ["Python", "R", "Excel"]
    }
}

# Categories
CATEGORIES: List[str] = [
    "Software Development",
    "Data Engineering",
    "Data Science and AI/ML",
    "Cloud and DevOps",
    "Data Analytics and BI",
    "Other"
]


def get_canonical_skill_name(raw_name: str) -> Optional[str]:
    """
    Returns canonical skill name if raw_name matches a canonical name or known alias.
    """
    norm = raw_name.strip().lower()
    for canonical, data in SKILLS_TAXONOMY.items():
        if canonical.lower() == norm:
            return canonical
        for alias in data.get("aliases", []):
            if alias.lower() == norm:
                return canonical
    return None


def get_all_canonical_skills() -> List[str]:
    """Returns sorted list of all canonical skills in taxonomy."""
    return sorted(list(SKILLS_TAXONOMY.keys()))


def get_skills_by_category() -> Dict[str, List[str]]:
    """Groups canonical skills by their category."""
    grouped: Dict[str, List[str]] = {}
    for skill, data in SKILLS_TAXONOMY.items():
        cat = data["category"]
        grouped.setdefault(cat, []).append(skill)
    return grouped
