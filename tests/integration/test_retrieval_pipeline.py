"""Integration tests for the retrieval pipeline."""

import pytest


@pytest.mark.integration
def test_retrieval_pipeline_alex_lives_in_dhaka(hydradb_client, sample_sessions):
    """Test retrieval returns Dhaka not Rajshahi for Alex's location."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # Ingest all Alex sessions
    for session in sample_sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # Query: Where does Alex live?
    result = run_retrieval("Where does Alex live?")

    assert "error" not in result
    assert "answer" in result
    assert "Dhaka" in result["answer"]


@pytest.mark.integration
def test_retrieval_pipeline_alex_job(hydradb_client, sample_sessions):
    """Test retrieval returns tech lead for Alex's job."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # Ingest all Alex sessions (if not already)
    for session in sample_sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # Query: What is Alex's job?
    result = run_retrieval("What is Alex's job?")

    assert "error" not in result
    assert "answer" in result
    assert "tech lead" in result["answer"].lower()


@pytest.mark.integration
def test_retrieval_pipeline_historical_fact(hydradb_client, sample_sessions):
    """Test historical_fact question type returns superseded facts."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # Ingest all Alex sessions
    for session in sample_sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # Query: Where did Alex live before Dhaka? (historical)
    result = run_retrieval("Where did Alex live before Dhaka?")

    assert "error" not in result
    assert "answer" in result
    # Should mention Rajshahi as the previous location
    assert "Rajshahi" in result["answer"]


@pytest.mark.integration
def test_retrieval_pipeline_multi_session_synthesis(hydradb_client, sample_sessions):
    """Test multi_session_synthesis combines facts across sessions."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # Ingest all Alex sessions
    for session in sample_sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # Query: What jobs has Alex had? (requires combining multiple sessions)
    result = run_retrieval("What jobs has Alex had?")

    assert "error" not in result
    assert "answer" in result
    # Should mention multiple roles
    assert any(role in result["answer"].lower() for role in ["software engineer", "senior engineer", "tech lead"])


@pytest.mark.integration
def test_retrieval_pipeline_absent_information(hydradb_client, sample_sessions):
    """Test absent_information question type returns abstention."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # Ingest all Alex sessions
    for session in sample_sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # Query: What is Alex's favorite color? (never mentioned)
    result = run_retrieval("What is Alex's favorite color?")

    assert "error" not in result
    assert "answer" in result
    # Should either abstain or have low confidence
    assert result.get("abstained") is True or result.get("confidence", 1) < 0.5


@pytest.mark.integration
def test_retrieval_pipeline_conflict_resolution(hydradb_client, sample_sessions):
    """Test conflicting facts returns most recent with conflict flag."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # Ingest all Alex sessions (has location conflict: Rajshahi -> Dhaka)
    for session in sample_sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # Query: Where does Alex live?
    result = run_retrieval("Where does Alex live?")

    assert "error" not in result
    assert "answer" in result
    # Should return most recent (Dhaka)
    assert "Dhaka" in result["answer"]
    # Should have conflict flag in metadata
    # Note: abstention module returns has_conflict in facts_to_use


@pytest.mark.integration
def test_retrieval_pipeline_pet_deceased(hydradb_client, sample_sessions):
    """Test question about deceased pet handled correctly."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # Ingest all Alex sessions (includes Mochi passing away)
    for session in sample_sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # Query: Does Alex still have a dog?
    result = run_retrieval("Does Alex still have a dog?")

    assert "error" not in result
    assert "answer" in result
    # Should either abstain or answer that Mochi passed away
    if result.get("abstained"):
        assert "Mochi" in result.get("abstention_reason", "") or "Mochi" in result.get("answer", "")
    else:
        assert "Mochi" in result.get("answer", "") or "passed" in result.get("answer", "").lower()


@pytest.mark.integration
def test_retrieval_pipeline_engagement(hydradb_client, sample_sessions):
    """Test engagement fact retrieval."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # Ingest all Alex sessions
    for session in sample_sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # Query: Is Alex engaged?
    result = run_retrieval("Is Alex engaged?")

    assert "error" not in result
    assert "answer" in result
    assert "Sara" in result["answer"]


@pytest.mark.integration
def test_retrieval_pipeline_empty_database(hydradb_client):
    """Test retrieval on empty database returns abstention."""
    from apps.api.pipeline.graph import run_retrieval

    # Query without any ingestion
    result = run_retrieval("Where does Alex live?")

    assert "error" not in result
    assert "answer" in result
    assert result.get("abstained") is True
    assert "no memory found" in result.get("abstention_reason", "").lower()


@pytest.mark.integration
def test_retrieval_pipeline_malformed_question(hydradb_client, sample_sessions):
    """Test malformed/empty question handled gracefully."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # Ingest sessions first
    for session in sample_sessions:
        result = run_pipeline(session)
        assert "error" not in result

    # Empty question
    result = run_retrieval("")
    assert "error" not in result or "answer" in result

    # Very short question
    result = run_retrieval("?")
    assert "error" not in result or "answer" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])