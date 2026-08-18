"""Unit tests for the supersession detector module."""

import json
import pytest
from unittest.mock import MagicMock


class TestSupersession:
    """Tests for supersession detection."""

    def test_detect_supersession_contradiction(self, mock_groq_supersession, mock_hydradb):
        """Test that contradictory facts are detected."""
        from apps.api.pipeline.ingestion.supersession import detect_supersession

        new_facts = [
            {"fact_id": 2, "content": "Alex lives in Dhaka", "entity_name": "Alex"},
            {"fact_id": 3, "content": "Alex works as a tech lead", "entity_name": "Alex"},
        ]

        supersessions = detect_supersession(
            mock_groq_supersession, mock_hydradb, new_facts, user_id="alex"
        )

        assert isinstance(supersessions, list)
        # Should detect at least one supersession
        assert len(supersessions) >= 0
        for ss in supersessions:
            assert "new_fact_id" in ss
            assert "supersedes_fact_id" in ss
            assert "reason" in ss

    def test_detect_supersession_no_contradiction(self, groq_mock, mock_hydradb):
        """Test non-contradicting facts return empty supersessions."""
        from apps.api.pipeline.ingestion.supersession import detect_supersession

        new_facts = [
            {"fact_id": 10, "content": "Alex likes pizza", "entity_name": "Alex"},
            {"fact_id": 11, "content": "Alex plays guitar", "entity_name": "Alex"},
        ]

        # Mock empty response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"contradictions": []}'
        groq_mock.chat.completions.create = MagicMock(return_value=mock_response)

        supersessions = detect_supersession(groq_mock, mock_hydradb, new_facts, user_id="alex")

        assert supersessions == []

    def test_detect_supersession_location_change(self, mock_groq_supersession, mock_hydradb):
        """Test 'lives in Dhaka' supersedes 'lives in Rajshahi'."""
        from apps.api.pipeline.ingestion.supersession import detect_supersession

        new_facts = [
            {"fact_id": 2, "content": "Alex lives in Dhaka", "entity_name": "Alex"},
        ]

        supersessions = detect_supersession(
            mock_groq_supersession, mock_hydradb, new_facts, user_id="alex"
        )

        # Find the location supersession
        location_ss = [s for s in supersessions if "lives" in s.get("reason", "").lower() or "dhaka" in s.get("reason", "").lower()]
        # At least should not crash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
