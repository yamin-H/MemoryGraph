"""Unit tests for the invalidator module."""

import json
import pytest
from unittest.mock import MagicMock


class TestInvalidator:
    """Tests for invalidation detection."""

    def test_detect_invalidations_time_bound_fact(self, mock_groq_invalidation, mock_hydradb):
        """Test that time-bound fact 'meeting tomorrow' gets flagged."""
        from apps.api.pipeline.ingestion.invalidator import detect_invalidations

        invalidations = detect_invalidations(
            mock_groq_invalidation,
            mock_hydradb,
            "alex-session-3",
            user_id="alex",
            current_timestamp="2024-03-10T11:00:00Z",
        )

        assert isinstance(invalidations, list)
        for inv in invalidations:
            assert "fact_id" in inv
            assert "reason" in inv
            assert "invalidated_at_session" in inv

    def test_detect_invalidations_permanent_fact_not_invalidated(self, groq_mock, mock_hydradb):
        """Test permanent fact 'name is Alex' never gets invalidated."""
        from apps.api.pipeline.ingestion.invalidator import detect_invalidations

        # Mock empty response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"invalidations": []}'
        groq_mock.chat.completions.create = MagicMock(return_value=mock_response)

        invalidations = detect_invalidations(
            groq_mock,
            mock_hydradb,
            "alex-session-5",
            user_id="alex",
            current_timestamp="2024-03-10T11:00:00Z",
        )

        assert invalidations == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
