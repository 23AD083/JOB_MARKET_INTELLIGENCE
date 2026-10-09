"""
Rule-Based Non-LLM Job Summarization Module.
Uses regex patterns, sentence segmentation, bullet extraction, and TF-IDF sentence ranking
to extract structured evidence. If a field cannot be extracted confidently, outputs 'Not specified'.
Never invents details or guesses.
"""

from typing import Dict, List, Optional
import re
from sklearn.feature_extraction.text import TfidfVectorizer


# Section Header Matchers
RESPONSIBILITY_HEADERS = [
    r"(?:key\s+|core\s+)?responsibilities:?",
    r"what\s+you(?:'ll|\s+will)\s+do:?",
    r"what\s+you\s+will\s+be\s+doing:?",
    r"duties\s+(?:and|&)\s+responsibilities:?",
    r"role\s+overview:?",
    r"your\s+mission:?"
]

EDUCATION_PATTERNS = [
    r"(?:(?:bachelor|master|doctorate|ph\.?d\.?)(?:'s)?(?:\s+degree)?|b\.?s\.?|m\.?s\.?|degree)\s+(?:in|of)\s+[^.\n;]+",
    r"(?:bachelor(?:'s)?|master(?:'s)?|ph\.?d\.?)\s+(?:degree)?",
    r"degree\s+in\s+[^.\n;]+"
]

EXPERIENCE_PATTERNS = [
    r"\b(?:\d+\+?|\d+\s*-\s*\d+)\s*(?:years?|yrs?)(?:\s+of)?(?:\s+[a-zA-Z\s/-]+)?\s+experience[^.\n;]*",
    r"(?:at\s+least|minimum\s+of)\s+\d+\s+years?(?:\s+of)?(?:\s+[a-zA-Z\s/-]+)?\s+experience[^.\n;]*"
]

WORK_MODE_PATTERNS = [
    r"\b(?:remote|hybrid|on-site|onsite|in-office)\b(?:\s+(?:eligible|based|work|position|friendly|first))?[^.\n]*"
]

DEADLINE_PATTERNS = [
    r"(?:deadline|closing\s+date|apply\s+by|applications\s+close|closes\s+on):\s*([a-zA-Z0-9\s,/-]+)",
    r"(?:apply\s+before|deadline\s+is)\s+([a-zA-Z0-9\s,/-]+)"
]


def clean_bullet_point(line: str) -> str:
    """Removes common bullet prefixes like *, -, bullet character, 1., etc."""
    cleaned = re.sub(r"^[\s*•\-–—►▪]+\s*", "", line).strip()
    cleaned = re.sub(r"^\d+[\.\)]\s*", "", cleaned).strip()
    return cleaned


def extract_bullet_items(text: str, max_items: int = 5) -> List[str]:
    """Extracts bulleted lines from a block of text."""
    lines = text.split("\n")
    bullets = []
    for line in lines:
        raw = line.strip()
        if not raw:
            continue
        if re.match(r"^[\*•\-–—►▪]|\d+[\.\)]", raw) and len(raw) > 10:
            cleaned = clean_bullet_point(raw)
            if cleaned and cleaned not in bullets:
                bullets.append(cleaned)
                if len(bullets) >= max_items:
                    break
    return bullets


def extract_field_with_regex(text: str, patterns: List[str]) -> str:
    """Extracts the first matching evidence sentence or phrase, or 'Not specified'."""
    for pat in patterns:
        match = re.search(pat, text, flags=re.IGNORECASE)
        if match:
            # If capture group exists, use it; otherwise use full matched string
            res = match.group(1) if match.groups() else match.group(0)
            cleaned = res.strip().strip(".,;")
            if len(cleaned) > 2:
                return cleaned
    return "Not specified"


def extract_role_overview(description: str, title: str) -> str:
    """
    Extracts 1-3 sentences that best describe the role overview.
    Uses first paragraph heuristics and TF-IDF sentence ranking if lengthy.
    """
    paragraphs = [p.strip() for p in description.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [p.strip() for p in description.split("\n") if p.strip()]

    # First check for an explicit role overview section
    intro_candidates = []
    for p in paragraphs[:5]:
        p_lower = p.lower()
        if re.search(r"^(?:role\s+overview|position\s+overview|summary|about\s+the\s+role):?", p_lower):
            intro_candidates.append(p)
            break

    if not intro_candidates:
        for p in paragraphs[:4]:
            p_lower = p.lower()
            # Filter out boilerplate like "About Us" or headers
            if len(p) > 30 and not re.search(r"^(?:about\s+us|about\s+our\s+company|who\s+we\s+are):?", p_lower) and not any(re.search(h, p_lower) for h in RESPONSIBILITY_HEADERS):
                intro_candidates.append(p)
                break

    if intro_candidates:
        intro_text = intro_candidates[0]
        # Clean leading section header
        intro_text = re.sub(r"^(?:role\s+overview|position\s+overview|summary|about\s+the\s+role):\s*", "", intro_text, flags=re.IGNORECASE).strip()
        # Split into sentences
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", intro_text) if len(s.strip()) > 15]
        if sentences:
            return " ".join(sentences[:2])

    # Fallback to TF-IDF extractive ranking over sentences
    all_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", description) if len(s.strip()) > 25]
    if not all_sentences:
        return f"Position for {title}."

    if len(all_sentences) <= 2:
        return " ".join(all_sentences)

    try:
        tfidf = TfidfVectorizer(stop_words="english")
        tfidf_matrix = tfidf.fit_transform(all_sentences)
        # Score sentences by mean tf-idf weight
        sentence_scores = tfidf_matrix.sum(axis=1)
        top_idx = int(sentence_scores.argmax())
        return all_sentences[top_idx]
    except Exception:
        return all_sentences[0]


def extract_responsibilities(description: str) -> List[str]:
    """
    Extracts 3-5 key responsibilities using section detection and bullet parsing.
    """
    lines = description.split("\n")
    found_section = False
    section_lines = []

    for i, line in enumerate(lines):
        line_clean = line.strip().lower()
        if any(re.search(pat, line_clean) for pat in RESPONSIBILITY_HEADERS):
            found_section = True
            # Collect following lines until another section header
            for next_line in lines[i+1:]:
                next_clean = next_line.strip().lower()
                if any(re.search(pat, next_clean) for pat in [r"requirements?:?", r"qualifications?:?", r"benefits?:?", r"what\s+we\s+offer:?"]):
                    break
                section_lines.append(next_line)
            break

    if found_section and section_lines:
        bullets = extract_bullet_items("\n".join(section_lines), max_items=5)
        if bullets:
            return bullets

    # If no explicit header bullets, search entire text for bullet items starting with action verbs
    action_verb_bullets = []
    all_bullets = extract_bullet_items(description, max_items=8)
    action_verbs = {"build", "design", "develop", "implement", "create", "manage", "collaborate", "lead", "maintain", "architect", "support", "deliver", "optimize", "drive", "analyze"}
    for b in all_bullets:
        words = b.lower().split()
        if words and words[0] in action_verbs:
            action_verb_bullets.append(b)
            if len(action_verb_bullets) >= 5:
                break

    if action_verb_bullets:
        return action_verb_bullets

    if all_bullets:
        return all_bullets[:5]

    return ["Responsibilities outlined in detailed job posting."]


def generate_job_summary(
    title: str,
    description: str,
    required_skills: List[str],
    preferred_skills: List[str],
    location: Optional[str] = None,
    workplace_type: Optional[str] = None
) -> Dict:
    """
    Generates a structured, evidence-backed summary for a job record.
    Never invents missing details.
    """
    role_overview = extract_role_overview(description, title)
    responsibilities = extract_responsibilities(description)
    education = extract_field_with_regex(description, EDUCATION_PATTERNS)
    experience = extract_field_with_regex(description, EXPERIENCE_PATTERNS)
    
    # Location and work mode
    work_mode_extracted = extract_field_with_regex(description, WORK_MODE_PATTERNS)
    if workplace_type and workplace_type.lower() != "unspecified":
        loc_str = f"{workplace_type.capitalize()}"
        if location:
            loc_str += f" ({location})"
    elif work_mode_extracted != "Not specified":
        loc_str = work_mode_extracted
        if location and location not in loc_str:
            loc_str += f" - {location}"
    elif location:
        loc_str = location
    else:
        loc_str = "Not specified"

    deadline = extract_field_with_regex(description, DEADLINE_PATTERNS)

    # Build human-readable formatted summary text
    req_skills_str = ", ".join(required_skills) if required_skills else "Not specified"
    pref_skills_str = ", ".join(preferred_skills) if preferred_skills else "Not specified"
    resp_bullets_str = "\n".join([f"• {r}" for r in responsibilities])

    summary_text = f"""**Role Overview**: {role_overview}

**Key Responsibilities**:
{resp_bullets_str}

**Requirements & Skills**:
• **Core Skills**: {req_skills_str}
• **Preferred Skills**: {pref_skills_str}
• **Experience**: {experience}
• **Education**: {education}
• **Location / Work Mode**: {loc_str}
• **Deadline**: {deadline}"""

    return {
        "role_overview": role_overview,
        "key_responsibilities": responsibilities,
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "education_requirements": education,
        "experience_requirements": experience,
        "location_work_mode": loc_str,
        "application_deadline": deadline,
        "summary_text": summary_text
    }
