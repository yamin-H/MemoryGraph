"""Shared pytest fixtures for MemoryGraph tests."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root and apps/api to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "apps" / "api"))

from apps.api.db.hydra import HydraDB, build_bolt_auth


@pytest.fixture(scope="session")
def hydradb_client():
    """Provide a HydraDB client connected to localhost."""
    from neo4j import GraphDatabase

    uri = os.environ.get("HYDRADB_URI", "neo4j://127.0.0.1:7687")
    token = os.environ.get("HYDRADB_TOKEN", "local-development-token-32-bytes")
    auth, _ = build_bolt_auth(token)

    driver = GraphDatabase.driver(uri, auth=auth)
    try:
        with driver.session() as session:
            session.run("MATCH (f:Fact) RETURN count(*) LIMIT 1")
    except Exception:
        driver.close()
        pytest.skip("HydraDB not available")
        return

    db = HydraDB(uri=uri, auth_token=token)
    db.connect()
    yield db
    db.close()


@pytest.fixture
def sample_sessions():
    """Load sample sessions from fixture file."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample_sessions.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return data["sessions"]


@pytest.fixture
def sample_session(sample_sessions):
    """Provide the first sample session (Alex intro)."""
    return sample_sessions[0]


@pytest.fixture
def sample_questions():
    """Load sample questions from fixture file."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample_questions.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return data["questions"]


@pytest.fixture
def groq_mock():
    """Mock Groq client for unit tests."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"facts": []}'
    mock_client.chat.completions.create = MagicMock(return_value=mock_response)
    return mock_client


@pytest.fixture
def mock_groq_facts():
    """Mock Groq response with extracted facts."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "facts": [
            {
                "content": "Alex lives in Rajshahi",
                "entity_name": "Alex",
                "entity_type": "person",
                "confidence": 0.9
            },
            {
                "content": "Alex works as a software engineer",
                "entity_name": "Alex",
                "entity_type": "person",
                "confidence": 0.9
            },
            {
                "content": "Alex has a dog named Mochi",
                "entity_name": "Alex",
                "entity_type": "person",
                "confidence": 0.8
            }
        ]
    })
    mock_client.chat.completions.create = MagicMock(return_value=mock_response)
    return mock_client


@pytest.fixture
def mock_groq_summary():
    """Mock Groq response with session summary."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "summary": "Alex introduced himself. He lives in Rajshahi, works as a software engineer, and has a dog named Mochi."
    })
    mock_client.chat.completions.create = MagicMock(return_value=mock_response)
    return mock_client


@pytest.fixture
def mock_groq_supersession():
    """Mock Groq response for supersession detection."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "contradictions": [
            {
                "entity_name": "Alex",
                "attribute": "location",
                "old_fact_content": "Alex lives in Rajshahi",
                "new_fact_content": "Alex lives in Dhaka",
                "reason": "location updated",
                "is_contradiction": True
            }
        ]
    })
    mock_client.chat.completions.create = MagicMock(return_value=mock_response)
    return mock_client


@pytest.fixture
def mock_groq_invalidation():
    """Mock Groq response for invalidation detection."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "invalidations": [
            {
                "fact_id": 1,
                "reason": "Meeting tomorrow has passed",
                "invalidated_at_session": "alex-session-3"
            }
        ]
    })
    mock_client.chat.completions.create = MagicMock(return_value=mock_response)
    return mock_client


@pytest.fixture
def mock_groq_parser():
    """Mock Groq response for question parsing."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "entity_name": "Alex",
        "question_type": "current_fact",
        "keywords": ["live", "location"],
        "original_question": "Where does Alex live?"
    })
    mock_client.chat.completions.create = MagicMock(return_value=mock_response)
    return mock_client


@pytest.fixture
def mock_hydradb():
    """Mock HydraDB client for unit tests."""
    from unittest.mock import MagicMock
    mock_db = MagicMock()
    mock_db._driver = MagicMock()
    mock_session = MagicMock()
    mock_db._driver.session.return_value.__enter__.return_value = mock_session
    mock_db._driver.session.return_value.__exit__.return_value = None
    return mock_db


# Removed autouse redis fixture since unit tests don't need Redis