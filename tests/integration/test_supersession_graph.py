"""Integration tests for supersession in the graph."""

import pytest


@pytest.mark.integration
def test_supersession_rajshahi_to_dhaka(hydradb_client):
    """Test 'lives in Dhaka' supersedes 'lives in Rajshahi'."""
    from apps.api.pipeline.graph import run_pipeline

    # Session 1: Alex lives in Rajshahi
    session1 = {
        "session_id": "test-supersede-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [
            {"role": "user", "content": "I live in Rajshahi."},
        ],
    }
    run_pipeline(session1)

    # Session 2: Alex lives in Dhaka (should supersede)
    session2 = {
        "session_id": "test-supersede-2",
        "user_id": "alex",
        "started_at": "2024-02-01T16:30:00Z",
        "messages": [
            {"role": "user", "content": "I moved to Dhaka!"},
        ],
    }
    run_pipeline(session2)

    # Verify SUPERSEDES edge exists
    with hydradb_client._driver.session() as db_session:
        result = db_session.run("""
            MATCH (old:Fact)-[:SUPERSEDES]->(new:Fact)
            WHERE old.content CONTAINS 'Rajshahi' AND new.content CONTAINS 'Dhaka'
            RETURN old, new
        """)
        assert result.single() is not None

        # Verify old fact has is_current: false
        result = db_session.run("""
            MATCH (f:Fact {is_current: false})
            WHERE f.content CONTAINS 'Rajshahi'
            RETURN f
        """)
        assert result.single() is not None

        # Verify query returns only Dhaka
        result = db_session.run("""
            MATCH (f:Fact {is_current: true})
            WHERE f.content CONTAINS 'live' OR f.content CONTAINS 'Dhaka' OR f.content CONTAINS 'Rajshahi'
            RETURN f.content
        """)
        contents = [r["f.content"] for r in result]
        # Should only have Dhaka, not Rajshahi
        assert any("Dhaka" in c for c in contents)
        # Rajshahi should not be in current facts
        assert not any("Rajshahi" in c for c in contents)


@pytest.mark.integration
def test_supersession_job_change(hydradb_client):
    """Test job title supersession (engineer -> senior engineer -> tech lead)."""
    from apps.api.pipeline.graph import run_pipeline

    # Session 1: Software engineer
    session1 = {
        "session_id": "test-supersede-job-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [{"role": "user", "content": "I work as a software engineer."}],
    }
    run_pipeline(session1)

    # Session 2: Senior engineer
    session2 = {
        "session_id": "test-supersede-job-2",
        "user_id": "alex",
        "started_at": "2024-02-01T16:30:00Z",
        "messages": [{"role": "user", "content": "I got promoted to senior engineer."}],
    }
    run_pipeline(session2)

    # Session 3: Tech lead
    session3 = {
        "session_id": "test-supersede-job-3",
        "user_id": "alex",
        "started_at": "2024-03-10T11:00:00Z",
        "messages": [{"role": "user", "content": "I'm now a tech lead!"}],
    }
    run_pipeline(session3)

    # Verify chain of supersessions exists
    with hydradb_client._driver.session() as db_session:
        result = db_session.run("""
            MATCH (f1:Fact)-[:SUPERSEDES]->(f2:Fact)-[:SUPERSEDES]->(f3:Fact)
            WHERE f1.content CONTAINS 'software engineer'
              AND f2.content CONTAINS 'senior engineer'
              AND f3.content CONTAINS 'tech lead'
            RETURN f1, f2, f3
        """)
        assert result.single() is not None

        # Only the latest should be current
        result = db_session.run("""
            MATCH (f:Fact {is_current: true})
            WHERE f.content CONTAINS 'engineer' OR f.content CONTAINS 'tech lead'
            RETURN f.content
        """)
        contents = [r["f.content"] for r in result]
        assert any("tech lead" in c.lower() for c in contents)
        assert not any("software engineer" in c.lower() for c in contents)
        assert not any("senior engineer" in c.lower() for c in contents)


@pytest.mark.integration
def test_supersession_pet_change(hydradb_client):
    """Test pet supersession (dog Mochi -> cat Pixel)."""
    from apps.api.pipeline.graph import run_pipeline

    # Session 1: Dog Mochi
    session1 = {
        "session_id": "test-supersede-pet-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [{"role": "user", "content": "I have a dog named Mochi."}],
    }
    run_pipeline(session1)

    # Session 2: Cat Pixel (Mochi passed away)
    session2 = {
        "session_id": "test-supersede-pet-2",
        "user_id": "alex",
        "started_at": "2024-02-01T16:30:00Z",
        "messages": [{"role": "user", "content": "Mochi passed away. I adopted a cat named Pixel."}],
    }
    run_pipeline(session2)

    # Verify supersession
    with hydradb_client._driver.session() as db_session:
        result = db_session.run("""
            MATCH (old:Fact)-[:SUPERSEDES]->(new:Fact)
            WHERE old.content CONTAINS 'Mochi' AND new.content CONTAINS 'Pixel'
            RETURN old, new
        """)
        assert result.single() is not None


@pytest.mark.integration
def test_supersession_multiple_in_one_session(hydradb_client):
    """Test multiple supersessions detected in a single session."""
    from apps.api.pipeline.graph import run_pipeline

    # Session 1: Initial facts
    session1 = {
        "session_id": "test-multi-super-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [{"role": "user", "content": "I live in Rajshahi and work as a software engineer."}],
    }
    run_pipeline(session1)

    # Session 2: Multiple changes at once
    session2 = {
        "session_id": "test-multi-super-2",
        "user_id": "alex",
        "started_at": "2024-02-01T16:30:00Z",
        "messages": [{"role": "user", "content": "I moved to Dhaka and got promoted to senior engineer."}],
    }
    result2 = run_pipeline(session2)

    # Should have applied multiple supersessions
    assert result2["write_result"]["supersessions_applied"] >= 2


@pytest.mark.integration
def test_supersession_no_false_positive(hydradb_client):
    """Test compatible facts don't trigger supersession."""
    from apps.api.pipeline.graph import run_pipeline

    # Session 1: Location
    session1 = {
        "session_id": "test-no-super-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [{"role": "user", "content": "I live in Dhaka."}],
    }
    run_pipeline(session1)

    # Session 2: Job (compatible, not contradictory)
    session2 = {
        "session_id": "test-no-super-2",
        "user_id": "alex",
        "started_at": "2024-02-01T16:30:00Z",
        "messages": [{"role": "user", "content": "I work as a software engineer."}],
    }
    result2 = run_pipeline(session2)

    # Should not have supersession between location and job
    with hydradb_client._driver.session() as db_session:
        result = db_session.run("""
            MATCH (old:Fact)-[:SUPERSEDES]->(new:Fact)
            RETURN count(*) AS c
        """)
        # Only possible supersession would be if Dhaka contradicted something
        assert result.single()["c"] == 0


@pytest.mark.integration
def test_supersession_different_entities_no_cross(hydradb_client):
    """Test supersession doesn't cross different entities."""
    from apps.api.pipeline.graph import run_pipeline

    # Session 1: Alex lives in Dhaka
    session1 = {
        "session_id": "test-cross-entity-1",
        "user_id": "alex",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [{"role": "user", "content": "I'm Alex and I live in Dhaka."}],
    }
    run_pipeline(session1)

    # Session 2: Bob lives in London (different entity)
    session2 = {
        "session_id": "test-cross-entity-2",
        "user_id": "bob",
        "started_at": "2024-02-01T16:30:00Z",
        "messages": [{"role": "user", "content": "I'm Bob and I live in London."}],
    }
    run_pipeline(session2)

    # No cross-entity supersession
    with hydradb_client._driver.session() as db_session:
        result = db_session.run("""
            MATCH (old:Fact)-[:SUPERSEDES]->(new:Fact)
            WHERE old.content CONTAINS 'Dhaka' AND new.content CONTAINS 'London'
            RETURN count(*) AS c
        """)
        assert result.single()["c"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])