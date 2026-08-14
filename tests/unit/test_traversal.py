"""Unit tests for the graph traversal module."""

import pytest
from unittest.mock import MagicMock


class TestTraversal:
    """Tests for graph traversal functions."""

    def test_traverse_for_question_current_fact(self, mock_hydradb):
        """Test traversal for current_fact question type."""
        from apps.api.pipeline.retrieval.traversal import traverse_for_question

        # Setup mock session and results
        mock_session = MagicMock()
        mock_hydradb._driver.session.return_value.__enter__.return_value = mock_session

        # Mock result for current facts
        mock_record = MagicMock()
        mock_record.__getitem__ = lambda self, key: {
            "f.id": "fact-1",
            "f.content": "Alex lives in Dhaka",
            "f.confidence": 0.9,
            "f.is_current": True,
            "f.created_at": "2024-02-01T10:00:00Z",
            "s.session_id": "session-1",
            "s.started_at": "2024-02-01T10:00:00Z",
        }[key]

        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([mock_record])
        mock_session.run.return_value = mock_result

        parsed_question = {
            "entity_name": "Alex",
            "question_type": "current_fact",
            "keywords": ["live", "location"],
        }

        facts = traverse_for_question(mock_hydradb, parsed_question)

        assert len(facts) == 1
        assert facts[0]["content"] == "Alex lives in Dhaka"
        assert facts[0]["is_current"] is True
        assert facts[0]["session_id"] == "session-1"

    def test_traverse_for_question_historical_fact(self, mock_hydradb):
        """Test traversal for historical_fact question type."""
        from apps.api.pipeline.retrieval.traversal import traverse_for_question

        mock_session = MagicMock()
        mock_hydradb._driver.session.return_value.__enter__.return_value = mock_session

        # Mock results for both current and historical facts
        mock_current = MagicMock()
        mock_current.__getitem__ = lambda self, key: {
            "f.id": "fact-1",
            "f.content": "Alex lives in Dhaka",
            "f.confidence": 0.9,
            "f.is_current": True,
            "f.created_at": "2024-02-01T10:00:00Z",
            "s.session_id": "session-1",
            "s.started_at": "2024-02-01T10:00:00Z",
        }[key]

        mock_historical = MagicMock()
        mock_historical.__getitem__ = lambda self, key: {
            "f.id": "fact-2",
            "f.content": "Alex lives in Rajshahi",
            "f.confidence": 0.8,
            "f.is_current": False,
            "f.created_at": "2024-01-15T10:00:00Z",
            "s.session_id": "session-2",
            "s.started_at": "2024-01-15T10:00:00Z",
            "superseded_by": "fact-1",
        }[key]

        mock_result1 = MagicMock()
        mock_result1.__iter__ = lambda self: iter([mock_current])
        mock_result2 = MagicMock()
        mock_result2.__iter__ = lambda self: iter([mock_historical])

        mock_session.run.side_effect = [mock_result1, mock_result2]

        parsed_question = {
            "entity_name": "Alex",
            "question_type": "historical_fact",
            "keywords": ["live", "before"],
        }

        facts = traverse_for_question(mock_hydradb, parsed_question)

        assert len(facts) == 2
        # Should have both current and historical
        current_facts = [f for f in facts if f["is_current"]]
        historical_facts = [f for f in facts if not f["is_current"]]
        assert len(current_facts) == 1
        assert len(historical_facts) == 1
        assert historical_facts[0]["superseded_by"] == "fact-1"

    def test_traverse_for_question_multi_session_synthesis(self, mock_hydradb):
        """Test traversal for multi_session_synthesis question type."""
        from apps.api.pipeline.retrieval.traversal import traverse_for_question

        mock_session = MagicMock()
        mock_hydradb._driver.session.return_value.__enter__.return_value = mock_session

        # Mock summary result
        mock_summary = MagicMock()
        mock_summary.__getitem__ = lambda self, key: {
            "sum.content": "Alex introduced himself. He lives in Dhaka and works as a software engineer.",
            "sum.created_at": "2024-02-01T10:00:00Z",
        }[key]

        mock_fact = MagicMock()
        mock_fact.__getitem__ = lambda self, key: {
            "f.id": "fact-1",
            "f.content": "Alex lives in Dhaka",
            "f.confidence": 0.9,
            "f.is_current": True,
            "f.created_at": "2024-02-01T10:00:00Z",
            "s.session_id": "session-1",
            "s.started_at": "2024-02-01T10:00:00Z",
        }[key]

        mock_result1 = MagicMock()
        mock_result1.__iter__ = lambda self: iter([mock_summary])
        mock_result2 = MagicMock()
        mock_result2.__iter__ = lambda self: iter([mock_fact])

        mock_session.run.side_effect = [mock_result1, mock_result2]

        parsed_question = {
            "entity_name": "Alex",
            "question_type": "multi_session_synthesis",
            "keywords": ["jobs", "work"],
        }

        facts = traverse_for_question(mock_hydradb, parsed_question)

        # Should return current facts
        assert len(facts) == 1
        assert facts[0]["content"] == "Alex lives in Dhaka"

    def test_traverse_for_question_empty_entity(self, mock_hydradb):
        """Test traversal returns empty list when entity_name is missing."""
        from apps.api.pipeline.retrieval.traversal import traverse_for_question

        parsed_question = {
            "entity_name": None,
            "question_type": "current_fact",
            "keywords": ["live"],
        }

        facts = traverse_for_question(mock_hydradb, parsed_question)

        assert facts == []

    def test_traverse_for_question_keyword_filtering(self, mock_hydradb):
        """Test traversal filters by keywords when provided."""
        from apps.api.pipeline.retrieval.traversal import traverse_for_question

        mock_session = MagicMock()
        mock_hydradb._driver.session.return_value.__enter__.return_value = mock_session

        # Two facts, only one matches keyword
        mock_fact1 = MagicMock()
        mock_fact1.__getitem__ = lambda self, key: {
            "f.id": "fact-1",
            "f.content": "Alex lives in Dhaka",
            "f.confidence": 0.9,
            "f.is_current": True,
            "f.created_at": "2024-02-01T10:00:00Z",
            "s.session_id": "session-1",
            "s.started_at": "2024-02-01T10:00:00Z",
        }[key]

        mock_fact2 = MagicMock()
        mock_fact2.__getitem__ = lambda self, key: {
            "f.id": "fact-2",
            "f.content": "Alex works as a software engineer",
            "f.confidence": 0.8,
            "f.is_current": True,
            "f.created_at": "2024-02-01T10:00:00Z",
            "s.session_id": "session-1",
            "s.started_at": "2024-02-01T10:00:00Z",
        }[key]

        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([mock_fact1, mock_fact2])
        mock_session.run.return_value = mock_result

        parsed_question = {
            "entity_name": "Alex",
            "question_type": "current_fact",
            "keywords": ["live", "location"],
        }

        facts = traverse_for_question(mock_hydradb, parsed_question)

        # Should only return fact about living (matches "live")
        assert len(facts) == 1
        assert "lives" in facts[0]["content"].lower()

    def test_traverse_for_question_keyword_filter_removes_all(self, mock_hydradb):
        """Test traversal keeps all facts when keyword filtering removes all."""
        from apps.api.pipeline.retrieval.traversal import traverse_for_question

        mock_session = MagicMock()
        mock_hydradb._driver.session.return_value.__enter__.return_value = mock_session

        mock_fact = MagicMock()
        mock_fact.__getitem__ = lambda self, key: {
            "f.id": "fact-1",
            "f.content": "Alex works as a software engineer",
            "f.confidence": 0.9,
            "f.is_current": True,
            "f.created_at": "2024-02-01T10:00:00Z",
            "s.session_id": "session-1",
            "s.started_at": "2024-02-01T10:00:00Z",
        }[key]

        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([mock_fact])
        mock_session.run.return_value = mock_result

        # Keywords that don't match any fact
        parsed_question = {
            "entity_name": "Alex",
            "question_type": "current_fact",
            "keywords": ["live", "location"],
        }

        facts = traverse_for_question(mock_hydradb, parsed_question)

        # Should keep original fact since filtering removed all
        assert len(facts) == 1
        assert facts[0]["content"] == "Alex works as a software engineer"

    def test_get_all_facts_for_entity(self, mock_hydradb):
        """Test get_all_facts_for_entity returns all facts including historical."""
        from apps.api.pipeline.retrieval.traversal import get_all_facts_for_entity

        mock_session = MagicMock()
        mock_hydradb._driver.session.return_value.__enter__.return_value = mock_session

        mock_fact1 = MagicMock()
        mock_fact1.__getitem__ = lambda self, key: {
            "f.id": "fact-1",
            "f.content": "Alex lives in Dhaka",
            "f.confidence": 0.9,
            "f.is_current": True,
            "f.created_at": "2024-02-01T10:00:00Z",
            "s.session_id": "session-1",
            "s.started_at": "2024-02-01T10:00:00Z",
        }[key]

        mock_fact2 = MagicMock()
        mock_fact2.__getitem__ = lambda self, key: {
            "f.id": "fact-2",
            "f.content": "Alex lives in Rajshahi",
            "f.confidence": 0.8,
            "f.is_current": False,
            "f.created_at": "2024-01-15T10:00:00Z",
            "s.session_id": "session-2",
            "s.started_at": "2024-01-15T10:00:00Z",
        }[key]

        mock_result = MagicMock()
        mock_result.__iter__ = lambda self: iter([mock_fact1, mock_fact2])
        mock_session.run.return_value = mock_result

        facts = get_all_facts_for_entity(mock_hydradb, "Alex")

        assert len(facts) == 2
        current_facts = [f for f in facts if f["is_current"]]
        historical_facts = [f for f in facts if not f["is_current"]]
        assert len(current_facts) == 1
        assert len(historical_facts) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])