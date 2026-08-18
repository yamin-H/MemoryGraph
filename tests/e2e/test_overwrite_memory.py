"""E2E tests for memory overwriting."""

import pytest


@pytest.mark.e2e
def test_overwrite_city_job_pet(hydradb_client):
    """Test Alex changing city, job, pet always returns most recent truth."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # Session 1: Rajshahi, engineer, dog Mochi
    run_pipeline({
        "session_id": "e2e-overwrite-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [{"role": "user", "content": "I live in Rajshahi and work as a software engineer. I have a dog named Mochi."}],
    })

    # Session 2: Dhaka, senior engineer, cat Pixel
    run_pipeline({
        "session_id": "e2e-overwrite-2",
        "user_id": "alex",
        "started_at": "2024-02-01T16:30:00Z",
        "messages": [{"role": "user", "content": "I moved to Dhaka and got promoted to senior engineer. Adopted a cat named Pixel."}],
    })

    # Query city - should be Dhaka
    result = run_retrieval("Where does Alex live?")
    assert "Dhaka" in result["answer"]

    # Query job - should be senior engineer (or later tech lead)
    result = run_retrieval("What is Alex's job?")
    assert "engineer" in result["answer"].lower()

    # Query pet - should be Pixel
    result = run_retrieval("What pet does Alex have?")
    assert "Pixel" in result["answer"]

    # Verify old facts marked is_current: false
    with hydradb_client._driver.session() as db_session:
        result = db_session.run("""
            MATCH (f:Fact {is_current: false})
            WHERE f.content CONTAINS 'Rajshahi'
            RETURN count(f) AS c
        """)
        assert result.single()["c"] > 0


@pytest.mark.e2e
def test_overwrite_multiple_attributes_same_session(hydradb_client):
    """Test multiple attribute changes in one session."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # Single session with multiple changes
    run_pipeline({
        "session_id": "e2e-multi-attr-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [{"role": "user", "content": "I live in Dhaka and work as a software engineer. I have a cat named Pixel."}],
    })

    # Second session: all three change
    run_pipeline({
        "session_id": "e2e-multi-attr-2",
        "user_id": "alex",
        "started_at": "2024-02-01T16:30:00Z",
        "messages": [{"role": "user", "content": "I moved to Chittagong, got promoted to tech lead, and adopted a dog named Buddy."}],
    })

    # All should reflect latest
    result = run_retrieval("Where does Alex live?")
    assert "Chittagong" in result["answer"]

    result = run_retrieval("What is Alex's job?")
    assert "tech lead" in result["answer"].lower()

    result = run_retrieval("What pet does Alex have?")
    assert "Buddy" in result["answer"]


@pytest.mark.e2e
def test_overwrite_partial_update(hydradb_client):
    """Test updating only some attributes preserves others."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # Session 1: Full profile
    run_pipeline({
        "session_id": "e2e-partial-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [{"role": "user", "content": "I live in Dhaka. I work as a software engineer. I have a cat named Pixel."}],
    })

    # Session 2: Only location changes
    run_pipeline({
        "session_id": "e2e-partial-2",
        "user_id": "alex",
        "started_at": "2024-02-01T16:30:00Z",
        "messages": [{"role": "user", "content": "I moved to Chittagong."}],
    })

    # Location should update
    result = run_retrieval("Where does Alex live?")
    assert "Chittagong" in result["answer"]

    # Job should remain
    result = run_retrieval("What is Alex's job?")
    assert "software engineer" in result["answer"].lower()

    # Pet should remain
    result = run_retrieval("What pet does Alex have?")
    assert "Pixel" in result["answer"]


@pytest.mark.e2e
def test_overwrite_supersession_edge_created(hydradb_client):
    """Test SUPERSEDES edges are created for each overwritten fact."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    run_pipeline({
        "session_id": "e2e-super-edge-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [{"role": "user", "content": "I live in City A."}],
    })

    run_pipeline({
        "session_id": "e2e-super-edge-2",
        "user_id": "alex",
        "started_at": "2024-02-01T16:30:00Z",
        "messages": [{"role": "user", "content": "I live in City B."}],
    })

    run_pipeline({
        "session_id": "e2e-super-edge-3",
        "user_id": "alex",
        "started_at": "2024-03-01T16:30:00Z",
        "messages": [{"role": "user", "content": "I live in City C."}],
    })

    # Verify chain of supersessions
    with hydradb_client._driver.session() as db_session:
        result = db_session.run("""
            MATCH (f1:Fact)-[:SUPERSEDES]->(f2:Fact)-[:SUPERSEDES]->(f3:Fact)
            WHERE f1.content CONTAINS 'City C'
              AND f2.content CONTAINS 'City B'
              AND f3.content CONTAINS 'City A'
            RETURN count(*) AS c
        """)
        assert result.single()["c"] >= 1


@pytest.mark.e2e
def test_overwrite_conflicting_facts_in_same_session(hydradb_client):
    """Test handling of contradictory statements within same session."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    # Single session with contradiction
    run_pipeline({
        "session_id": "e2e-conflict-session-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [{"role": "user", "content": "I live in Dhaka. Actually, I live in Chittagong."}],
    })

    # Should resolve to latest in session (Chittagong)
    result = run_retrieval("Where does Alex live?")
    assert "Chittagong" in result["answer"]


@pytest.mark.e2e
def test_overwrite_name_change(hydradb_client):
    """Test entity name change (rare but possible)."""
    from apps.api.pipeline.graph import run_pipeline, run_retrieval

    run_pipeline({
        "session_id": "e2e-name-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [{"role": "user", "content": "My name is Alex."}],
    })

    run_pipeline({
        "session_id": "e2e-name-2",
        "user_id": "alex",
        "started_at": "2024-02-01T16:30:00Z",
        "messages": [{"role": "user", "content": "Actually, I go by Alexander now."}],
    })

    # Query by new name
    result = run_retrieval("Who is Alexander?")
    assert "error" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])
