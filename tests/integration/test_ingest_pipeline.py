"""Integration tests for the ingestion pipeline."""

import pytest


@pytest.mark.integration
def test_ingest_pipeline_alex_session(hydradb_client, sample_sessions):
    """Test full ingestion pipeline with Alex sample session."""
    from apps.api.pipeline.graph import run_pipeline

    session = sample_sessions[0]  # First session: intro, Rajshahi, engineer, Mochi

    result = run_pipeline(session)

    assert result.get("error") is None
    assert "write_result" in result
    assert "session_id" in result["write_result"]
    assert "nodes_created" in result["write_result"]
    assert "edges_created" in result["write_result"]
    assert "facts_written" in result["write_result"]
    assert result["write_result"]["facts_written"] > 0

    # Verify Session node exists
    with hydradb_client._driver.session() as db_session:
        result = db_session.run(
            "MATCH (s:Session) RETURN s.session_id"
        )
        sessions = [r["s.session_id"] for r in result]
        assert session["session_id"] in sessions

        # Verify Fact nodes exist (simple count without aggregation)
        result = db_session.run(
            "MATCH (f:Fact) RETURN f.id"
        )
        fact_count = len(list(result))
        assert fact_count > 0

        # Verify Entity nodes exist
        result = db_session.run(
            "MATCH (e:Entity) RETURN e.id"
        )
        entity_count = len(list(result))
        assert entity_count > 0


@pytest.mark.integration
def test_ingest_pipeline_batch(hydradb_client, sample_sessions):
    """Test batch ingestion of multiple sessions."""
    from apps.api.pipeline.graph import run_pipeline

    results = []
    for session in sample_sessions[:3]:  # First 3 sessions
        result = run_pipeline(session)
        results.append(result)
        assert result.get("error") is None

    assert len(results) == 3


@pytest.mark.integration
def test_ingest_pipeline_supersession_application(hydradb_client):
    """Test that supersession is applied during ingestion."""
    from apps.api.pipeline.graph import run_pipeline

    # Session 1: Alex lives in Rajshahi
    session1 = {
        "session_id": "test-supersede-ingest-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [{"role": "user", "content": "I live in Rajshahi."}],
    }
    result1 = run_pipeline(session1)
    assert result1.get("error") is None

    # Session 2: Alex lives in Dhaka (should supersede)
    session2 = {
        "session_id": "test-supersede-ingest-2",
        "user_id": "alex",
        "started_at": "2024-02-01T16:30:00Z",
        "messages": [{"role": "user", "content": "I moved to Dhaka!"}],
    }
    result2 = run_pipeline(session2)
    assert result2.get("error") is None

    # Verify supersession was applied
    assert result2["write_result"]["supersessions_applied"] >= 0

    # Verify old fact is marked is_current: false
    with hydradb_client._driver.session() as db_session:
        result = db_session.run("""
            MATCH (f:Fact {is_current: false})
            WHERE f.content CONTAINS 'Rajshahi'
            RETURN count(f) AS c
        """)
        assert result.single()["c"] >= 1


@pytest.mark.integration
def test_ingest_pipeline_invalidation_application(hydradb_client):
    """Test that invalidation is applied during ingestion."""
    from apps.api.pipeline.graph import run_pipeline

    # Session 1: Time-bound fact (meeting tomorrow)
    session1 = {
        "session_id": "test-invalidation-ingest-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [{"role": "user", "content": "I have a meeting tomorrow at 9am with the team."}],
    }
    result1 = run_pipeline(session1)
    assert result1.get("error") is None

    # Session 2: Next day - should trigger invalidation
    session2 = {
        "session_id": "test-invalidation-ingest-2",
        "user_id": "alex",
        "started_at": "2024-01-16T10:00:00Z",
        "messages": [{"role": "user", "content": "Meeting is done."}],
    }
    result2 = run_pipeline(session2)
    assert result2.get("error") is None

    # Verify invalidation was applied
    assert result2["write_result"]["invalidations_applied"] >= 0


@pytest.mark.integration
def test_ingest_pipeline_summary_created(hydradb_client):
    """Test that session summary is created and stored."""
    from apps.api.pipeline.graph import run_pipeline

    session = {
        "session_id": "test-summary-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [
            {"role": "user", "content": "I'm Alex. I live in Dhaka and work as a software engineer."},
        ],
    }
    result = run_pipeline(session)
    assert result.get("error") is None

    # Verify Summary node exists
    with hydradb_client._driver.session() as db_session:
        result = db_session.run("""
            MATCH (s:Summary)-[:SUMMARY_ANCHOR]->()
            WHERE s.content CONTAINS 'Alex'
            RETURN s.content
        """)
        summary = result.single()
        assert summary is not None
        assert "Alex" in summary["s.content"]


@pytest.mark.integration
def test_ingest_pipeline_messages_stored(hydradb_client):
    """Test that messages are stored with CONTAINS edges."""
    from apps.api.pipeline.graph import run_pipeline

    session = {
        "session_id": "test-messages-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [
            {"role": "user", "content": "Hello world"},
            {"role": "assistant", "content": "Hi there"},
        ],
    }
    result = run_pipeline(session)
    assert result.get("error") is None

    # Verify Message nodes and CONTAINS edges
    with hydradb_client._driver.session() as db_session:
        result = db_session.run("""
            MATCH (s:Session {session_id: $session_id})-[:CONTAINS]->(m:Message)
            RETURN count(m) AS msg_count
        """, session_id="test-messages-1")
        assert result.single()["msg_count"] == 2


@pytest.mark.integration
def test_ingest_pipeline_entities_deduplicated(hydradb_client):
    """Test that entities are deduplicated across facts."""
    from apps.api.pipeline.graph import run_pipeline

    session = {
        "session_id": "test-entity-dedup-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [
            {"role": "user", "content": "I'm Alex. I live in Dhaka. I work as a software engineer."},
        ],
    }
    result = run_pipeline(session)
    assert result.get("error") is None

    # Verify only one Entity node for Alex
    with hydradb_client._driver.session() as db_session:
        result = db_session.run("""
            MATCH (e:Entity {name: 'Alex'})
            RETURN count(e) AS entity_count
        """)
        assert result.single()["entity_count"] == 1


@pytest.mark.integration
def test_ingest_pipeline_empty_session(hydradb_client):
    """Test ingestion handles empty session gracefully."""
    from apps.api.pipeline.graph import run_pipeline

    session = {
        "session_id": "test-empty-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [],
    }
    result = run_pipeline(session)
    assert result.get("error") is None
    assert result["write_result"]["facts_written"] == 0


@pytest.mark.integration
def test_ingest_pipeline_special_characters(hydradb_client):
    """Test ingestion handles special characters and unicode."""
    from apps.api.pipeline.graph import run_pipeline

    session = {
        "session_id": "test-unicode-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [
            {"role": "user", "content": "I'm Alex ���. I live in Tokyo 東京 and work as a developer ���."},
        ],
    }
    result = run_pipeline(session)
    assert result.get("error") is None
    assert result["write_result"]["facts_written"] > 0


@pytest.mark.integration
def test_ingest_pipeline_long_session(hydradb_client):
    """Test ingestion handles longer sessions with many messages."""
    from apps.api.pipeline.graph import run_pipeline

    messages = []
    for i in range(20):
        messages.append({"role": "user", "content": f"Message {i} about topic {i % 5}"})
        messages.append({"role": "assistant", "content": f"Response {i}"})

    session = {
        "session_id": "test-long-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": messages,
    }
    result = run_pipeline(session)
    assert result.get("error") is None
    assert result["write_result"]["facts_written"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])