"""Integration tests for HydraDB connection."""

import pytest


@pytest.mark.integration
def test_hydradb_connect_write_read(hydradb_client):
    """Test connect, write, read, verify, cleanup."""
    db = hydradb_client

    # Write a test fact
    test_fact_id = 999999
    test_content = "Integration test fact"
    db.write_fact(test_fact_id, test_content)

    # Read it back
    fact = db.read_fact(test_fact_id)

    assert fact is not None
    assert fact["id"] == test_fact_id
    assert fact["content"] == test_content

    # Clean up
    db.clear_all()


@pytest.mark.integration
def test_hydradb_multiple_facts(hydradb_client):
    """Test writing multiple facts."""
    db = hydradb_client

    for i in range(5):
        db.write_fact(900000 + i, f"Fact number {i}")

    # Read them all back
    for i in range(5):
        fact = db.read_fact(900000 + i)
        assert fact is not None
        assert fact["content"] == f"Fact number {i}"

    db.clear_all()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])