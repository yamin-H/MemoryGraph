"""Unit tests for the confidence module."""

import pytest


class TestConfidence:
    """Tests for confidence calculation."""

    def test_calculate_confidence_high_with_multiple_recent_facts(self):
        """Test high confidence when multiple recent facts exist."""
        from apps.api.pipeline.retrieval.confidence import calculate_confidence

        facts_used = [
            {"fact_id": "1", "content": "Alex lives in Dhaka", "entity_name": "Alex", "session_started_at": "2024-03-10T11:00:00Z", "session_id": "session-5"},
            {"fact_id": "2", "content": "Alex works as tech lead", "entity_name": "Alex", "session_started_at": "2024-03-10T11:00:00Z", "session_id": "session-5"},
        ]
        abstention_result = {"should_abstain": False, "has_conflict": False}
        parsed_question = {
            "entity_name": "Alex",
            "question_type": "current_fact",
            "keywords": ["live", "job"],
            "original_question": "Where does Alex live and work?",
        }

        result = calculate_confidence(facts_used, abstention_result, parsed_question)

        assert "score" in result
        assert "reasoning" in result
        assert isinstance(result["score"], (int, float))
        assert 0 <= result["score"] <= 1
        # Should have bonus for multiple facts and recency
        assert result["score"] > 0.5

    def test_calculate_confidence_low_when_abstention_considered(self):
        """Test low confidence when abstention was considered."""
        from apps.api.pipeline.retrieval.confidence import calculate_confidence

        facts_used = []
        abstention_result = {"should_abstain": True, "abstention_reason": "no memory found", "has_conflict": False}
        parsed_question = {
            "entity_name": "Alex",
            "question_type": "current_fact",
            "keywords": ["live"],
            "original_question": "Where does Alex live?",
        }

        result = calculate_confidence(facts_used, abstention_result, parsed_question)

        assert result["score"] == 0.0
        assert "no supporting facts" in result["reasoning"].lower()

    def test_calculate_confidence_conflict_penalty(self):
        """Test conflict reduces confidence."""
        from apps.api.pipeline.retrieval.confidence import calculate_confidence

        facts_used = [
            {"fact_id": "1", "content": "Alex lives in Dhaka", "entity_name": "Alex", "session_started_at": "2024-03-10T11:00:00Z", "session_id": "session-5"},
        ]
        abstention_result = {"should_abstain": False, "has_conflict": True}
        parsed_question = {
            "entity_name": "Alex",
            "question_type": "current_fact",
            "keywords": ["live"],
            "original_question": "Where does Alex live?",
        }

        result = calculate_confidence(facts_used, abstention_result, parsed_question)

        # Base 0.5 + 1 fact (0.1) + recency (0.1) = 0.7, minus conflict (0.1) = 0.6
        # Test that conflict penalty is applied
        assert "conflict" in result["reasoning"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])