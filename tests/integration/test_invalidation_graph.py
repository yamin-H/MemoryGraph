"""Integration tests for invalidation in the graph."""

import pytest


@pytest.mark.integration
def test_invalidation_meeting_tomorrow(hydradb_client):
    """Test time-bound fact 'meeting tomorrow' gets invalidated."""
    from apps.api.pipeline.graph import run_pipeline

    # Session 1: Alex has meeting tomorrow
    session1 = {
        "session_id": "test-invalidation-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [
            {"role": "user", "content": "I have a meeting tomorrow at 9am with the team."},
        ],
    }
    run_pipeline(session1)

    # Session 2: Next day - run invalidator
    session2 = {
        "session_id": "test-invalidation-2",
        "user_id": "alex",
        "started_at": "2024-01-16T10:00:00Z",
        "messages": [
            {"role": "user", "content": "Meeting is done."},
        ],
    }
    run_pipeline(session2)

    # Verify INVALIDATED_BY edge exists
    with hydradb_client._driver.session() as db_session:
        result = db_session.run("""
            MATCH (f:Fact)-[:INVALIDATED_BY]->(s:Session)
            WHERE f.content CONTAINS 'meeting'
            RETURN f, s
        """)
        assert result.single() is not None

        # Verify fact is marked is_current: false
        result = db_session.run("""
            MATCH (f:Fact {is_current: false})
            WHERE f.content CONTAINS 'meeting'
            RETURN f
        """)
        assert result.single() is not None


@pytest.mark.integration
def test_invalidation_travel_expired(hydradb_client):
    """Test 'traveling this week' expires after the week."""
    from apps.api.pipeline.graph import run_pipeline

    # Session 1: Traveling this week
    session1 = {
        "session_id": "test-invalidation-travel-1",
        "user_id": "alex",
        "started_at": "2024-01-10T10:30:00Z",
        "messages": [
            {"role": "user", "content": "I'm traveling this week to Tokyo for a conference."},
        ],
    }
    run_pipeline(session1)

    # Session 2: Two weeks later
    session2 = {
        "session_id": "test-invalidation-travel-2",
        "user_id": "alex",
        "started_at": "2024-01-24T10:00:00Z",
        "messages": [
            {"role": "user", "content": "Back from Tokyo trip."},
        ],
    }
    run_pipeline(session2)

    # Verify travel fact invalidated
    with hydradb_client._driver.session() as db_session:
        result = db_session.run("""
            MATCH (f:Fact {is_current: false})
            WHERE f.content CONTAINS 'traveling'
            RETURN f
        """)
        assert result.single() is not None


@pytest.mark.integration
def test_invalidation_permanent_fact_not_invalidated(hydradb_client):
    """Test permanent facts (location, job, name) never get invalidated."""
    from apps.api.pipeline.graph import run_pipeline

    # Session 1: Permanent facts
    session1 = {
        "session_id": "test-invalidation-perm-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [
            {"role": "user", "content": "I'm Alex. I live in Dhaka and work as a software engineer. I have a cat named Pixel."},
        ],
    }
    run_pipeline(session1)

    # Session 2: Much later
    session2 = {
        "session_id": "test-invalidation-perm-2",
        "user_id": "alex",
        "started_at": "2024-06-15T10:00:00Z",
        "messages": [
            {"role": "user", "content": "Just a regular update."},
        ],
    }
    run_pipeline(session2)

    # Verify permanent facts remain current
    with hydradb_client._driver.session() as db_session:
        result = db_session.run("""
            MATCH (f:Fact {is_current: true})
            WHERE f.content CONTAINS 'Dhaka' OR f.content CONTAINS 'software engineer' OR f.content CONTAINS 'Pixel'
            RETURN count(f) AS c
        """)
        assert result.single()["c"] == 3

        # No invalidations for these
        result = db_session.run("""
            MATCH (f:Fact)-[:INVALIDATED_BY]->()
            WHERE f.content CONTAINS 'Dhaka' OR f.content CONTAINS 'software engineer' OR f.content CONTAINS 'Pixel'
            RETURN count(f) AS c
        """)
        assert result.single()["c"] == 0


@pytest.mark.integration
def test_invalidation_multiple_timebound_facts(hydradb_client):
    """Test multiple time-bound facts invalidated in one session."""
    from apps.api.pipeline.graph import run_pipeline

    # Session 1: Multiple time-bound facts
    session1 = {
        "session_id": "test-invalidation-multi-1",
        "user_id": "alex",
        "started_at": "2024-01-10T10:30:00Z",
        "messages": [
            {"role": "user", "content": "I have a meeting tomorrow at 9am. I'm sick today. I'm traveling this week."},
        ],
    }
    run_pipeline(session1)

    # Session 2: Week later
    session2 = {
        "session_id": "test-invalidation-multi-2",
        "user_id": "alex",
        "started_at": "2024-01-17T10:00:00Z",
        "messages": [
            {"role": "user", "content": "All done."},
        ],
    }
    result2 = run_pipeline(session2)

    # Should have multiple invalidations
    assert result2["write_result"]["invalidations_applied"] >= 2


@pytest.mark.integration
def test_invalidation_already_invalidated_not_reinvalidated(hydradb_client):
    """Test already invalidated facts aren't processed again."""
    from apps.api.pipeline.graph import run_pipeline

    # Session 1: Meeting tomorrow
    session1 = {
        "session_id": "test-invalidation-re-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [{"role": "user", "content": "I have a meeting tomorrow at 9am."}],
    }
    run_pipeline(session1)

    # Session 2: Next day - invalidates meeting
    session2 = {
        "session_id": "test-invalidation-re-2",
        "user_id": "alex",
        "started_at": "2024-01-16T10:00:00Z",
        "messages": [{"role": "user", "content": "Meeting done."}],
    }
    run_pipeline(session2)

    # Session 3: Another day - should not re-invalidate
    session3 = {
        "session_id": "test-invalidation-re-3",
        "user_id": "alex",
        "started_at": "2024-01-17T10:00:00Z",
        "messages": [{"role": "user", "content": "Another day."}],
    }
    result3 = run_pipeline(session3)

    # No new invalidations for already invalidated fact
    assert result3["write_result"]["invalidations_applied"] == 0


@pytest.mark.integration
def test_invalidation_sick_temporary_state(hydradb_client):
    """Test 'currently sick' temporary state expires."""
    from apps.api.pipeline.graph import run_pipeline

    # Session 1: Currently sick
    session1 = {
        "session_id": "test-invalidation-sick-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [{"role": "user", "content": "I'm currently sick with the flu."}],
    }
    run_pipeline(session1)

    # Session 2: Week later - should be recovered
    session2 = {
        "session_id": "test-invalidation-sick-2",
        "user_id": "alex",
        "started_at": "2024-01-22T10:00:00Z",
        "messages": [{"role": "user", "content": "Feeling better now."}],
    }
    run_pipeline(session2)

    # Verify sick fact invalidated
    with hydradb_client._driver.session() as db_session:
        result = db_session.run("""
            MATCH (f:Fact {is_current: false})
            WHERE f.content CONTAINS 'sick'
            RETURN f
        """)
        assert result.single() is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])