"""
Skill Assessment Question Bank and Question Provider.
Loads structured questions across technical skills and difficulty levels.
"""

from typing import Any, Dict, List, Optional
import json
import os


class QuestionBank:
    def __init__(self):
        self.questions_by_skill: Dict[str, List[Dict[str, Any]]] = {}
        self._load_questions()

    def _load_questions(self):
        json_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_questions.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for q in data:
                    skill = q["skill"]
                    self.questions_by_skill.setdefault(skill, []).append(q)
            except Exception:
                pass

    def get_skills_with_assessments(self) -> List[str]:
        """Returns sorted list of skills that have active assessment questions."""
        return sorted(list(self.questions_by_skill.keys()))

    def get_questions_for_skill(self, skill_name: str, difficulty: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieves questions for a given skill, optionally filtered by difficulty (1-4)."""
        qs = self.questions_by_skill.get(skill_name, [])
        if difficulty is not None:
            filtered = [q for q in qs if q.get("difficulty") == difficulty]
            return filtered if filtered else qs
        return qs


question_bank = QuestionBank()
