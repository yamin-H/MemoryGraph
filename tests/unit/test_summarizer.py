"""Unit tests for the session summarizer module."""

import json
import re
import pytest
from unittest.mock import MagicMock


class TestSummarizer:
    """Tests for session summarization."""

    def test_summarize_session_returns_correct_structure(self, mock_groq_summary):
        """Test that summarize_session returns summary with correct structure."""
        from apps.api.pipeline.ingestion.summarizer import summarize_session

        sample_session = {
            "session_id": "test-1",
            "user_id": "alex",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [
                {"role": "user", "content": "I'm Alex. I live in Rajshahi."},
                {"role": "assistant", "content": "Nice to meet you!"},
            ],
        }

        summary = summarize_session(mock_groq_summary, sample_session)

        assert isinstance(summary, dict)
        assert "summary_id" in summary
        assert "session_id" in summary
        assert "content" in summary
        assert "generated_at" in summary
        assert summary["session_id"] == "test-1"
        assert isinstance(summary["content"], str)
        assert len(summary["content"]) > 0

    def test_summarize_session_max_two_sentences(self, mock_groq_summary):
        """Test that summary is at most 2 sentences."""
        from apps.api.pipeline.ingestion.summarizer import summarize_session

        sample_session = {
            "session_id": "test-2",
            "user_id": "alex",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [
                {"role": "user", "content": "Long story here."},
            ],
        }

        summary = summarize_session(mock_groq_summary, sample_session)

        if summary is None:
            pytest.skip("Summary returned None")

        # Count sentences (simple heuristic: split by . ! ?)
        sentences = re.split(r'[.!?]+', summary["content"])
        sentences = [s.strip() for s in sentences if s.strip()]
        assert len(sentences) <= 2, f"Summary has {len(sentences)} sentences, max is 2"

    def test_summarize_session_empty_session(self, groq_mock):
        """Test empty session returns None."""
        from apps.api.pipeline.ingestion.summarizer import summarize_session

        empty_session = {
            "session_id": "empty-1",
            "user_id": "alex",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [],
        }

        summary = summarize_session(groq_mock, empty_session)
        assert summary is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])