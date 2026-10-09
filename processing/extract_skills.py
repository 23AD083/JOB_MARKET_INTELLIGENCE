"""
Deterministic Context-Aware Skill Extraction.
Extracts canonical skills from job descriptions, distinguishing required vs preferred skills
using section headers and taxonomy-informed pattern matching.
"""

import re
from typing import Dict, List, Set, Tuple
from processing.skills_taxonomy import SKILLS_TAXONOMY, get_canonical_skill_name

# Patterns indicating required vs preferred sections
REQUIRED_SECTION_PATTERNS = [
    r"(?:required|minimum|basic|must\s+have|core)\s*(?:skills?|qualifications?|requirements?|experience)",
    r"what\s+you(?:'ll|\s+will)\s+need",
    r"requirements?:?",
    r"what\s+we(?:'re|\s+are)\s+looking\s+for"
]

PREFERRED_SECTION_PATTERNS = [
    r"(?:preferred|nice\s+to\s+have|bonus|plus|desired|optional|additional)(?:\s*(?:skills?|qualifications?|requirements?|experience))?:?",
    r"bonus\s+points?\s*(?:if|for)?",
    r"what\s+gives\s+you\s+an\s+edge"
]


def split_description_sections(text: str) -> Tuple[str, str, str]:
    """
    Splits job description into (overview/general, required_section, preferred_section).
    If distinct headers are not found, returns (text, '', '').
    """
    lines = text.split("\n")
    current_mode = "general"
    general_parts = []
    required_parts = []
    preferred_parts = []

    for line in lines:
        line_clean = line.strip().lower()
        
        # Check if line marks start of preferred section
        is_pref_header = any(re.search(pat, line_clean) for pat in PREFERRED_SECTION_PATTERNS)
        is_req_header = any(re.search(pat, line_clean) for pat in REQUIRED_SECTION_PATTERNS)

        if is_pref_header:
            current_mode = "preferred"
            preferred_parts.append(line)
        elif is_req_header:
            current_mode = "required"
            required_parts.append(line)
        elif re.search(r"^(?:about\s+the\s+company|benefits|what\s+we\s+offer|compensation):?", line_clean):
            current_mode = "other"
        else:
            if current_mode == "required":
                required_parts.append(line)
            elif current_mode == "preferred":
                preferred_parts.append(line)
            elif current_mode == "general":
                general_parts.append(line)

    return ("\n".join(general_parts), "\n".join(required_parts), "\n".join(preferred_parts))


def match_skills_in_text(text: str) -> Set[str]:
    """
    Deterministic context-aware matching of skills against taxonomy.
    """
    if not text:
        return set()

    found_skills: Set[str] = set()
    text_lower = text.lower()

    for canonical, data in SKILLS_TAXONOMY.items():
        pattern = data.get("regex")
        if pattern:
            # Match using context-aware regex
            if re.search(pattern, text, flags=re.IGNORECASE):
                found_skills.add(canonical)
            continue

        # If no custom regex, match exact word boundaries on canonical and aliases
        canonical_pattern = rf"\b{re.escape(canonical.lower())}\b"
        if re.search(canonical_pattern, text_lower):
            found_skills.add(canonical)
            continue

        for alias in data.get("aliases", []):
            alias_pattern = rf"\b{re.escape(alias.lower())}\b"
            if re.search(alias_pattern, text_lower):
                found_skills.add(canonical)
                break

    return found_skills


def extract_skills_from_job(title: str, description: str) -> Dict[str, List[str]]:
    """
    Extracts canonical skills from job title and description.
    Distinguishes required skills from preferred skills.
    Returns:
        {
            "required_skills": sorted list of canonical skills,
            "preferred_skills": sorted list of canonical skills,
            "all_skills": sorted list of all unique skills
        }
    """
    title_skills = match_skills_in_text(title)
    gen_text, req_text, pref_text = split_description_sections(description)

    req_skills = match_skills_in_text(req_text)
    pref_skills = match_skills_in_text(pref_text)
    gen_skills = match_skills_in_text(gen_text)

    # Any skill in the title is inherently required/core
    req_skills.update(title_skills)

    # If sections were separated
    if req_skills or pref_skills:
        # Skills in general text: if not already preferred, treat as required
        for s in gen_skills:
            if s not in pref_skills:
                req_skills.add(s)
        # Skills can't be both required and preferred; required takes precedence
        pref_skills = pref_skills - req_skills
    else:
        # When no explicit section headers exist, all found skills are treated as required
        req_skills.update(gen_skills)

    all_skills = sorted(list(req_skills | pref_skills))
    
    return {
        "required_skills": sorted(list(req_skills)),
        "preferred_skills": sorted(list(pref_skills)),
        "all_skills": all_skills
    }
