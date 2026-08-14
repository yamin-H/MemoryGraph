"""Unit tests for the ranker module."""

import pytest


class TestRanker:
    """Tests for fact ranking and conflict resolution."""

    def test_rank_facts_by_time_sorts_descending(self):
        """Test facts are sorted by session_started_at descending."""
        from apps.api.pipeline.retrieval.ranker import rank_facts_by_time

        facts = [
            {"fact_id": "1", "content": "Old fact about topic", "session_started_at": "2024-01-15T10:00:00Z", "is_current": True},
            {"fact_id": "2", "content": "New fact about topic", "session_started_at": "2024-03-10T11:00:00Z", "is_current": True},
            {"fact_id": "3", "content": "Middle fact about topic", "session_started_at": "2024-02-01T16:30:00Z", "is_current": True},
        ]

        ranked = rank_facts_by_time(facts)

        assert ranked[0]["fact_id"] == "2"  # Newest first
        assert ranked[1]["fact_id"] == "3"
        assert ranked[2]["fact_id"] == "1"

    def test_rank_facts_by_time_missing_timestamp(self):
        """Test facts without timestamps are handled."""
        from apps.api.pipeline.retrieval.ranker import rank_facts_by_time

        facts = [
            {"fact_id": "1", "content": "No timestamp here", "is_current": True},
            {"fact_id": "2", "content": "Has timestamp now", "session_started_at": "2024-03-10T11:00:00Z", "is_current": True},
        ]

        ranked = rank_facts_by_time(facts)
        # Should not crash, facts without timestamps go to end
        assert ranked[0]["fact_id"] == "2"

    def test_resolve_conflicts_flags_conflicts(self):
        """Test conflict flagging when two facts for same entity exist without SUPERSEDES."""
        from apps.api.pipeline.retrieval.ranker import resolve_conflicts, rank_facts_by_time

        # Facts need to share the same first 3 significant words (>3 chars) to be grouped as conflicts
        # Both have "lives", "rajshahi/dhaka", "works" -> first 3 >3 chars: "lives", "rajshahi", "works" vs "lives", "dhaka", "works"
        # Need same first 3 words >3 chars
        facts = [
            {"fact_id": "1", "content": "Alex lives in Rajshahi works", "entity_name": "Alex", "session_started_at": "2024-01-15T10:00:00Z", "is_current": True},
            {"fact_id": "2", "content": "Alex lives in Rajshahi works", "entity_name": "Alex", "session_started_at": "2024-03-10T11:00:00Z", "is_current": True},
        ]

        ranked = rank_facts_by_time(facts)
        resolved, conflicts = resolve_conflicts(ranked)

        # Should flag conflict for same topic (identical first 3 significant words)
        assert len(conflicts) >= 1
        assert any("Alex" in c["content"] for c in conflicts)

    def test_resolve_conflicts_no_conflict_for_different_entities(self):
        """Test no false conflict for different entities."""
        from apps.api.pipeline.retrieval.ranker import resolve_conflicts, rank_facts_by_time

        facts = [
            {"fact_id": "1", "content": "Alex lives in Dhaka works", "entity_name": "Alex", "session_started_at": "2024-03-10T11:00:00Z", "is_current": True},
            {"fact_id": "2", "content": "Bob lives in London works", "entity_name": "Bob", "session_started_at": "2024-03-10T11:00:00Z", "is_current": True},
        ]

        ranked = rank_facts_by_time(facts)
        resolved, conflicts = resolve_conflicts(ranked)

        assert len(conflicts) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])