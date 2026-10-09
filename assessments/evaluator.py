"""
Assessment Evaluator and In-Memory SQL Sandbox.
Evaluates multiple-choice and SQL query responses safely.
Assigns proficiency levels (1: Beginner, 2: Developing, 3: Proficient, 4: Advanced).
Strictly blocks arbitrary shell or Python execution for security.
"""

import sqlite3
from typing import Any, Dict, List, Optional, Tuple


def evaluate_multiple_choice(user_answer: Optional[str], correct_answer: Optional[str]) -> Tuple[bool, float, str]:
    """
    Evaluates a multiple choice question response safely.
    Returns (is_correct, score, feedback).
    """
    if not user_answer or not str(user_answer).strip():
        return (False, 0.0, "Please select an answer before submitting.")
    if not correct_answer or not str(correct_answer).strip():
        return (False, 0.0, "No correct answer defined for this question.")

    u_norm = str(user_answer).strip().lower()
    c_norm = str(correct_answer).strip().lower()

    if u_norm == c_norm or (len(u_norm) > 10 and u_norm in c_norm):
        return (True, 100.0, "Correct! Demonstrated clear conceptual understanding.")
    return (False, 0.0, f"Incorrect. The correct answer was: '{correct_answer}'.")


def evaluate_sql_query_in_sandbox(user_query: str, expected_query: str) -> Tuple[bool, float, str]:
    """
    Safely executes user query and expected query against an in-memory SQLite sandbox
    with test schema and compares result sets.
    Blocks destructive statements (DROP, INSERT, UPDATE, DELETE, ATTACH).
    """
    q_lower = user_query.strip().lower()
    # Security check: Read-only SELECTs only
    disallowed_keywords = ["drop", "delete", "insert", "update", "alter", "attach", "detach", "vacuum", "pragma"]
    for kw in disallowed_keywords:
        if kw in q_lower:
            return (False, 0.0, f"Security violation: Sandbox only permits read-only SELECT queries. Keyword '{kw}' is blocked.")

    try:
        # Create in-memory database
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()

        # Seed sample evaluation tables
        cursor.execute("""
            CREATE TABLE employees (
                id INTEGER PRIMARY KEY,
                name TEXT,
                department_id INTEGER,
                salary REAL,
                hire_date TEXT
            );
        """)
        cursor.executemany("""
            INSERT INTO employees VALUES (?, ?, ?, ?, ?);
        """, [
            (1, "Alice", 101, 95000, "2021-03-15"),
            (2, "Bob", 101, 105000, "2020-07-01"),
            (3, "Charlie", 102, 80000, "2022-01-10"),
            (4, "Dana", 102, 115000, "2019-11-20"),
            (5, "Evan", 103, 72000, "2023-05-04")
        ])

        # Execute expected query
        cursor.execute(expected_query)
        expected_rows = cursor.fetchall()

        # Execute user query
        cursor.execute(user_query)
        user_rows = cursor.fetchall()

        conn.close()

        if user_rows == expected_rows:
            return (True, 100.0, "Query matched expected result set perfectly!")
        else:
            return (False, 30.0, f"Query executed but output differs from expected. Returned {len(user_rows)} rows vs {len(expected_rows)} expected.")

    except Exception as e:
        return (False, 0.0, f"SQL syntax or execution error: {str(e)}")


def calculate_proficiency_level(score_percentage: float) -> Tuple[int, str]:
    """
    Maps percentage score to proficiency level:
    - Level 0: Not assessed
    - Level 1: Beginner (< 40%)
    - Level 2: Developing (40% - 69%)
    - Level 3: Proficient (70% - 89%)
    - Level 4: Advanced (>= 90%)
    """
    if score_percentage >= 90.0:
        return (4, "Advanced")
    elif score_percentage >= 70.0:
        return (3, "Proficient")
    elif score_percentage >= 40.0:
        return (2, "Developing")
    elif score_percentage > 0.0:
        return (1, "Beginner")
    return (0, "Not Assessed")
