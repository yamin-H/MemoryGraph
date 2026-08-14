"""Unit tests for the abstention module."""

import pytest


class TestAbstention:
    """Tests for abstention logic."""

    def test_check_abstention_empty_facts_triggers_abstention(self):
        """Test empty facts list triggers abstention."""
        from apps.api.pipeline.retrieval.abstention import check_abstention

        ranked_facts = []
        parsed_question = {
            "entity_name": "Alex",
            "question_type": "current_fact",
            "keywords": ["live"],
            "original_question": "Where does Alex live?",
        }

        result = check_abstention(ranked_facts, parsed_question)

        assert result["should_abstain"] is True
        assert result["abstention_reason"] == "no memory found"
        assert result["facts_to_use"] == []

    def test_check_abstention_irrelevant_facts_triggers_abstention(self):
        """Test facts unrelated to question trigger abstention (absent_information type)."""
        from apps.api.pipeline.retrieval.abstention import check_abstention

        ranked_facts = [
            {"fact_id": "1", "content": "Bob likes pizza", "entity_name": "Bob", "is_current": True, "created_at": "2024-03-10T11:00:00Z"},
        ]
        parsed_question = {
            "entity_name": "Alex",
            "question_type": "absent_information",
            "keywords": ["live"],
            "original_question": "Where does Alex live?",
        }

        result = check_abstention(ranked_facts, parsed_question)

        assert result["should_abstain"] is True
        assert result["abstention_reason"] == "memory exists but does not answer question"

    def test_check_abstention_conflicting_facts_returns_most_recent(self):
        """Test conflicting facts returns most recent with flag."""
        from apps.api.pipeline.retrieval.abstention import check_abstention

        ranked_facts = [
            {"fact_id": "2", "content": "Alex lives in Dhaka", "entity_name": "Alex", "is_current": True, "session_started_at": "2024-03-10T11:00:00Z", "has_conflict": True},
            {"fact_id": "1", "content": "Alex lives in Rajshahi", "entity_name": "Alex", "is_current": True, "session_started_at": "2024-01-15T10:00:00Z", "has_conflict": True},
        ]
        parsed_question = {
            "entity_name": "Alex",
            "question_type": "current_fact",
            "keywords": ["live"],
            "original_question": "Where does Alex live?",
        }

        result = check_abstention(ranked_facts, parsed_question)

        assert result["should_abstain"] is False
        assert result["has_conflict"] is True
        assert len(result["facts_to_use"]) == 1
        assert result["facts_to_use"][0]["fact_id"] == "2"  # Most recent

    def test_check_abstention_single_fact_no_abstention(self):
        """Test single relevant fact doesn't trigger abstention."""
        from apps.api.pipeline.retrieval.abstention import check_abstention

        ranked_facts = [
            {"fact_id": "1", "content": "Alex lives in Dhaka", "entity_name": "Alex", "is_current": True, "session_started_at": "2024-03-10T11:00:00Z"},
        ]
        parsed_question = {
            "entity_name": "Alex",
            "question_type": "current_fact",
            "keywords": ["live"],
            "original_question": "Where does Alex live?",
        }

        result = check_abstention(ranked_facts, parsed_question)

        assert result["should_abstain"] is False
        assert len(result["facts_to_use"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])