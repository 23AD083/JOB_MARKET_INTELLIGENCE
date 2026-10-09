"""
Test application startup, schema initialization, and Gradio interface construction.
"""

import pytest
from app import build_app
from database.repository import repo
from database.init_db import initialize_database


def test_app_initialization_and_startup():
    # Initialize DB and ensure sample data loads
    user = initialize_database()
    assert user is not None
    assert user.id is not None

    # Total jobs should be at least seeded sample jobs (> 0)
    total_jobs = repo.get_total_jobs_count()
    assert total_jobs > 0

    # Test Gradio Blocks creation
    demo = build_app()
    assert demo is not None
    assert hasattr(demo, "blocks")
