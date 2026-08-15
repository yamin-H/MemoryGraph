"""Unit tests for the fact extractor module."""

import json
import pytest
from unittest.mock import MagicMock


class TestExtractor:
    """Tests for fact extraction from sessions."""

    def test_extract_facts_returns_correct_structure(self, mock_groq_facts):
        """Test that extract_facts returns facts with correct structure."""
        from apps.api.pipeline.ingestion.extractor import extract_facts

        sample_session = {
            "session_id": "test-1",
            "user_id": "alex",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [
                {"role": "user", "content": "I'm Alex. I live in Rajshahi and work as a software engineer."},
                {"role": "assistant", "content": "Nice to meet you!"},
            ],
        }

        facts = extract_facts(mock_groq_facts, sample_session)

        assert isinstance(facts, list)
        assert len(facts) == 3
        for fact in facts:
            assert "fact_id" in fact
            assert "content" in fact
            assert "entity_name" in fact
            assert "entity_type" in fact
            assert "confidence" in fact
            assert "session_id" in fact
            assert fact["session_id"] == "test-1"
            assert isinstance(fact["confidence"], (int, float))
            assert 0 <= fact["confidence"] <= 1

    def test_extract_facts_empty_session(self, groq_mock):
        """Test empty session returns empty facts list."""
        from apps.api.pipeline.ingestion.extractor import extract_facts

        empty_session = {
            "session_id": "empty-1",
            "user_id": "alex",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [],
        }

        facts = extract_facts(groq_mock, empty_session)
        assert facts == []

    def test_extract_facts_malformed_session(self, groq_mock):
        """Test malformed session is handled gracefully."""
        from apps.api.pipeline.ingestion.extractor import extract_facts

        malformed_session = {
            "session_id": "malformed-1",
            "user_id": "alex",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [
                {"role": "user"},  # missing content
                {"role": "assistant", "content": "response"},
            ],
        }

        facts = extract_facts(groq_mock, malformed_session)
        assert isinstance(facts, list)  # Should not crash

    def test_extract_facts_returns_uuids(self, mock_groq_facts):
        """Test that fact IDs are UUID strings."""
        from apps.api.pipeline.ingestion.extractor import extract_facts

        sample_session = {
            "session_id": "test-deterministic",
            "user_id": "alex",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [
                {"role": "user", "content": "I'm Alex. I live in Rajshahi."},
            ],
        }

        facts = extract_facts(mock_groq_facts, sample_session)

        # fact_id should be a UUID string (36 chars with hyphens)
        for fact in facts:
            assert isinstance(fact["fact_id"], str)
            assert len(fact["fact_id"]) == 36  # UUID format

    def test_extract_facts_falls_back_to_session_text_when_llm_returns_empty(self):
        """When the LLM is silent, the extractor should still recover core facts from the conversation text."""
        from apps.api.pipeline.ingestion.extractor import extract_facts

        client = MagicMock()
        client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"facts": []}'))]
        )

        session = {
            "session_id": "fallback-1",
            "user_id": "alex",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [
                {"role": "user", "content": "I'm Alex. I live in Rajshahi and work as a software engineer."},
                {"role": "user", "content": "I have a dog named Mochi and I enjoy hiking on weekends."},
            ],
        }

        facts = extract_facts(client, session)

        assert len(facts) >= 3
        texts = {fact["content"] for fact in facts}
        assert any("Alex lives in Rajshahi" in text for text in texts)
        assert any("Alex works as a software engineer" in text for text in texts)
        assert any("Alex has a dog named Mochi" in text for text in texts)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])