"""E2E tests for abstention behavior."""

import pytest


@pytest.mark.e2e
def test_abstention_on_unknown_topic(hydradb_client, sample_sessions):
    """Test asking about something never mentioned returns abstention."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # Ingest Alex sessions
    for session in sample_sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # Ask about something never mentioned
    result = run_retrieval("What is Alex's favorite color?")

    assert "error" not in result
    # Should abstain or give low confidence
    assert result.get("abstained") is True or result.get("confidence", 1) < 0.5
    if "abstention_reason" in result:
        assert result["abstention_reason"] is not None


@pytest.mark.e2e
def test_abstention_dog_passed_away(hydradb_client, sample_sessions):
    """Test 'Does Alex still have a dog?' handles Mochi's passing."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # Ingest all sessions (includes Mochi dying)
    for session in sample_sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # Ask about dog
    result = run_retrieval("Does Alex still have a dog?")

    assert "error" not in result
    # Should either abstain or answer that Mochi passed away
    if result.get("abstained"):
        assert "Mochi" in result.get("abstention_reason", "") or "Mochi" in result.get("answer", "")
    else:
        assert "Mochi" in result.get("answer", "") or "passed" in result.get("answer", "").lower()


@pytest.mark.e2e
def test_abstention_no_memory_at_all(hydradb_client):
    """Test abstention on completely empty database."""
    from apps.api.pipeline.graph import run_retrieval

    # No ingestion at all
    result = run_retrieval("Where does Alex live?")

    assert "error" not in result
    assert result.get("abstained") is True
    assert "no memory found" in result.get("abstention_reason", "").lower()


@pytest.mark.e2e
def test_abstention_wrong_entity(hydradb_client, sample_sessions):
    """Test asking about entity that doesn't exist."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    for session in sample_sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # Ask about non-existent entity
    result = run_retrieval("Where does Charlie live?")

    assert "error" not in result
    assert result.get("abstained") is True
    assert "no memory found" in result.get("abstention_reason", "").lower()


@pytest.mark.e2e
def test_abstention_irrelevant_facts(hydradb_client, sample_sessions):
    """Test abstention when facts exist but don't answer the question."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    for session in sample_sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # Alex has a cat, not a dog
    result = run_retrieval("What is Alex's dog's name?")

    assert "error" not in result
    # Should abstain because memory exists but doesn't answer (absent_information type)
    assert result.get("abstained") is True
    assert "does not answer" in result.get("abstention_reason", "").lower()


@pytest.mark.e2e
def test_abstention_conflict_returns_most_recent(hydradb_client):
    """Test conflicting facts returns most recent with conflict flag."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # Create conflicting location facts
    run_pipeline({
        "session_id": "e2e-conflict-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [{"role": "user", "content": "I live in City A."}],
    })

    run_pipeline({
        "session_id": "e2e-conflict-2",
        "user_id": "alex",
        "started_at": "2024-02-01T16:30:00Z",
        "messages": [{"role": "user", "content": "I live in City B."}],
    })

    result = run_retrieval("Where does Alex live?")

    assert "error" not in result
    assert result.get("abstained") is False
    # Should return most recent (City B)
    assert "City B" in result["answer"]
    # Should have conflict flag in answer metadata
    assert result.get("has_conflict") is True or "conflict" in str(result).lower()


@pytest.mark.e2e
def test_abstention_historical_question_with_no_history(hydradb_client):
    """Test historical question when no superseded facts exist."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # Only one session, no history
    run_pipeline({
        "session_id": "e2e-hist-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [{"role": "user", "content": "I live in Dhaka."}],
    })

    result = run_retrieval("Where did Alex live before Dhaka?")

    assert "error" not in result
    # Should either abstain or answer no history
    assert result.get("abstained") is True or "no" in result.get("answer", "").lower()


@pytest.mark.e2e
def test_abstention_empty_question(hydradb_client, sample_sessions):
    """Test empty or nonsense question handled gracefully."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    for session in sample_sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # Empty question
    result = run_retrieval("")
    assert "error" not in result

    # Nonsense
    result = run_retrieval("???")
    assert "error" not in result


@pytest.mark.e2e
def test_abstention_confidence_threshold_behavior(hydradb_client, sample_sessions):
    """Test confidence scores align with abstention decisions."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    for session in sample_sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # High confidence - no abstention
    result = run_retrieval("Where does Alex live?")
    answer = result.get("answer", {})
    assert answer.get("abstained") is False
    assert answer.get("confidence", 0) >= 0.7

    # Low confidence - abstention
    result = run_retrieval("What is Alex's favorite color?")
    answer = result.get("answer", {})
    assert answer.get("abstained") is True
    assert answer.get("confidence", 1) < 0.35


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])
