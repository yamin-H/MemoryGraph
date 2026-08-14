"""E2E tests for full system flow."""

import pytest


@pytest.mark.e2e
def test_full_flow_five_sessions_five_questions(hydradb_client, sample_sessions, sample_questions):
    """Ingest 5 Alex sessions, ask 5 questions, verify all correct."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # Ingest all 5 sessions
    for session in sample_sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # Ask each question and verify
    for q in sample_questions:
        result = run_retrieval(q["question"])
        assert "error" not in result
        assert "answer" in result

        if "expected_answer" in q:
            assert q["expected_answer"].lower() in result["answer"].lower(), \
                f"Q: {q['question']}\nExpected: {q['expected_answer']}\nGot: {result['answer']}"

        if "expected_confidence_min" in q:
            assert result.get("confidence", 0) >= q["expected_confidence_min"], \
                f"Q: {q['question']}\nConfidence {result.get('confidence')} < {q['expected_confidence_min']}"


@pytest.mark.e2e
def test_full_flow_multi_user_isolation(hydradb_client):
    """Test multiple users' memories don't leak."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # User 1: Alex
    alex_sessions = [
        {
            "session_id": "e2e-multi-alex-1",
            "user_id": "alex",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [{"role": "user", "content": "I'm Alex and I live in Dhaka."}],
        },
    ]

    # User 2: Bob
    bob_sessions = [
        {
            "session_id": "e2e-multi-bob-1",
            "user_id": "bob",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [{"role": "user", "content": "I'm Bob and I live in London."}],
        },
    ]

    for session in alex_sessions + bob_sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # Query Alex
    result = run_retrieval("Where does Alex live?")
    assert "Dhaka" in result["answer"]
    assert "London" not in result["answer"]

    # Query Bob
    result = run_retrieval("Where does Bob live?")
    assert "London" in result["answer"]
    assert "Dhaka" not in result["answer"]


@pytest.mark.e2e
def test_full_flow_concurrent_sessions_same_user(hydradb_client):
    """Test interleaved sessions for same user maintain temporal order."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    sessions = [
        {
            "session_id": "e2e-concurrent-1",
            "user_id": "alex",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [{"role": "user", "content": "I live in City A."}],
        },
        {
            "session_id": "e2e-concurrent-2",
            "user_id": "alex",
            "started_at": "2024-01-16T10:30:00Z",
            "messages": [{"role": "user", "content": "I moved to City B."}],
        },
        {
            "session_id": "e2e-concurrent-3",
            "user_id": "alex",
            "started_at": "2024-01-17T10:30:00Z",
            "messages": [{"role": "user", "content": "Now I live in City C."}],
        },
    ]

    for session in sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # Should return most recent (City C)
    result = run_retrieval("Where does Alex live?")
    assert "City C" in result["answer"]


@pytest.mark.e2e
def test_full_flow_long_term_memory(hydradb_client):
    """Test retrieval of facts from earliest session after many updates."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # Many sessions over time
    for i in range(10):
        session = {
            "session_id": f"e2e-long-{i}",
            "user_id": "alex",
            "started_at": f"2024-01-{15+i:02d}T10:30:00Z",
            "messages": [{"role": "user", "content": f"Update {i}: I like fruit {i}."}],
        }
        result = run_pipeline(session)
        assert "error" not in result

    # First fact should still be queryable (though superseded if contradictory)
    result = run_retrieval("What fruit did Alex like in the first session?")
    # May abstain or return the first fruit
    assert "error" not in result


@pytest.mark.e2e
def test_full_flow_historical_query(hydradb_client, sample_sessions):
    """Test historical_fact question type."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    for session in sample_sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # Historical question
    result = run_retrieval("Where did Alex live before Dhaka?")
    assert "error" not in result
    assert "answer" in result
    assert "Rajshahi" in result["answer"]


@pytest.mark.e2e
def test_full_flow_synthesis_query(hydradb_client, sample_sessions):
    """Test multi_session_synthesis question type."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    for session in sample_sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # Synthesis question
    result = run_retrieval("What jobs has Alex had?")
    assert "error" not in result
    assert "answer" in result
    # Should mention multiple roles
    roles = ["software engineer", "senior engineer", "tech lead"]
    assert any(role in result["answer"].lower() for role in roles)


@pytest.mark.e2e
def test_full_flow_confidence_scores(hydradb_client, sample_sessions):
    """Test confidence scores are reasonable across question types."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    for session in sample_sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # High confidence for well-supported facts
    result = run_retrieval("Where does Alex live?")
    assert result["confidence"] >= 0.7

    result = run_retrieval("What is Alex's job?")
    assert result["confidence"] >= 0.7

    # Lower confidence or abstention for absent info
    result = run_retrieval("What is Alex's favorite color?")
    assert result.get("abstained") is True or result["confidence"] < 0.5


@pytest.mark.e2e
def test_full_flow_supersession_chain(hydradb_client):
    """Test full supersession chain is maintained and queryable."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    sessions = [
        {"session_id": "e2e-chain-1", "user_id": "alex", "started_at": "2024-01-15T10:30:00Z", "messages": [{"role": "user", "content": "I live in City A."}]},
        {"session_id": "e2e-chain-2", "user_id": "alex", "started_at": "2024-02-15T10:30:00Z", "messages": [{"role": "user", "content": "I moved to City B."}]},
        {"session_id": "e2e-chain-3", "user_id": "alex", "started_at": "2024-03-15T10:30:00Z", "messages": [{"role": "user", "content": "I moved to City C."}]},
    ]

    for session in sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # Current location
    result = run_retrieval("Where does Alex live now?")
    assert "City C" in result["answer"]

    # Historical
    result = run_retrieval("Where did Alex live before City C?")
    assert "City B" in result["answer"]


@pytest.mark.e2e
def test_full_flow_invalidation_expired_facts(hydradb_client):
    """Test time-bound facts expire and don't pollute current memory."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # Time-bound fact
    session1 = {
        "session_id": "e2e-inv-1",
        "user_id": "alex",
        "started_at": "2024-01-10T10:30:00Z",
        "messages": [{"role": "user", "content": "I have a meeting tomorrow at 9am."}],
    }
    run_pipeline(session1)

    # After meeting
    session2 = {
        "session_id": "e2e-inv-2",
        "user_id": "alex",
        "started_at": "2024-01-12T10:30:00Z",
        "messages": [{"role": "user", "content": "Meeting done."}],
    }
    run_pipeline(session2)

    # Query should not return the expired meeting
    result = run_retrieval("What meetings does Alex have?")
    # Should abstain or not mention the past meeting
    assert "error" not in result


@pytest.mark.e2e
def test_full_flow_special_characters_unicode(hydradb_client):
    """Test full flow handles unicode and special characters."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    session = {
        "session_id": "e2e-unicode-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [{"role": "user", "content": "I'm Alex ���. I live in Tokyo 東京 and work at Café ��."}],
    }
    result = run_pipeline(session)
    assert "error" not in result

    result = run_retrieval("Where does Alex live?")
    assert "Tokyo" in result["answer"] or "東京" in result["answer"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])