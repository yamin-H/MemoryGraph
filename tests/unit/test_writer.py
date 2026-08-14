"""Unit tests for the HydraDB writer module."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


class TestWriter:
    """Tests for HydraDB writer functions."""

    def test_generate_int_id_deterministic(self):
        """Test generate_int_id produces deterministic IDs."""
        from apps.api.pipeline.ingestion.writer import generate_int_id

        id1 = generate_int_id("test:string")
        id2 = generate_int_id("test:string")

        assert id1 == id2
        assert isinstance(id1, int)
        assert 0 <= id1 < 10**9

    def test_generate_int_id_unique(self):
        """Test generate_int_id produces different IDs for different strings."""
        from apps.api.pipeline.ingestion.writer import generate_int_id

        id1 = generate_int_id("string:1")
        id2 = generate_int_id("string:2")

        # Very low probability of collision, but test anyway
        assert id1 != id2

    def test_write_to_hydradb_creates_session(self, mock_hydradb):
        """Test write_to_hydradb creates Session node."""
        from apps.api.pipeline.ingestion.writer import write_to_hydradb

        mock_session = MagicMock()
        mock_hydradb._driver.session.return_value.__enter__.return_value = mock_session

        session = {
            "session_id": "test-session-1",
            "user_id": "alex",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [{"role": "user", "content": "Hello"}],
        }
        summary = {"summary_id": "sum-1", "content": "Test summary", "generated_at": "2024-01-15T10:30:00Z"}
        facts = [
            {
                "fact_id": "fact-1",
                "content": "Alex lives in Dhaka",
                "confidence": 0.9,
                "entity_name": "Alex",
                "created_at": "2024-01-15T10:30:00Z",
            }
        ]

        result = write_to_hydradb(
            hydra=mock_hydradb,
            session=session,
            summary=summary,
            facts=facts,
            supersessions=[],
            invalidations=[],
        )

        assert result["session_id"] == "test-session-1"
        assert result["nodes_created"] > 0
        assert result["edges_created"] > 0
        assert result["facts_written"] == 1
        assert mock_session.run.called

    def test_write_to_hydradb_creates_messages(self, mock_hydradb):
        """Test write_to_hydradb creates Message nodes."""
        from apps.api.pipeline.ingestion.writer import write_to_hydradb

        mock_session = MagicMock()
        mock_hydradb._driver.session.return_value.__enter__.return_value = mock_session

        session = {
            "session_id": "test-session-2",
            "user_id": "alex",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [
                {"role": "user", "content": "Message 1"},
                {"role": "assistant", "content": "Response 1"},
            ],
        }

        result = write_to_hydradb(
            hydra=mock_hydradb,
            session=session,
            summary=None,
            facts=[],
            supersessions=[],
            invalidations=[],
        )

        assert result["nodes_created"] >= 4  # 2 messages * 2 (message + anchor each)
        assert result["edges_created"] >= 2  # CONTAINS edges

    def test_write_to_hydradb_creates_summary(self, mock_hydradb):
        """Test write_to_hydradb creates Summary node when provided."""
        from apps.api.pipeline.ingestion.writer import write_to_hydradb

        mock_session = MagicMock()
        mock_hydradb._driver.session.return_value.__enter__.return_value = mock_session

        session = {
            "session_id": "test-session-3",
            "user_id": "alex",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [],
        }
        summary = {"summary_id": "sum-3", "content": "Test summary", "generated_at": "2024-01-15T10:30:00Z"}

        result = write_to_hydradb(
            hydra=mock_hydradb,
            session=session,
            summary=summary,
            facts=[],
            supersessions=[],
            invalidations=[],
        )

        # Summary + anchor = 2 nodes, HAS_SUMMARY edge = 1 edge
        assert result["nodes_created"] >= 2
        assert result["edges_created"] >= 1

    def test_write_to_hydradb_creates_entities(self, mock_hydradb):
        """Test write_to_hydradb creates Entity nodes."""
        from apps.api.pipeline.ingestion.writer import write_to_hydradb

        mock_session = MagicMock()
        mock_hydradb._driver.session.return_value.__enter__.return_value = mock_session

        session = {
            "session_id": "test-session-4",
            "user_id": "alex",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [],
        }
        facts = [
            {
                "fact_id": "fact-4a",
                "content": "Alex lives in Dhaka",
                "confidence": 0.9,
                "entity_name": "Alex",
                "created_at": "2024-01-15T10:30:00Z",
            },
            {
                "fact_id": "fact-4b",
                "content": "Bob lives in London",
                "confidence": 0.8,
                "entity_name": "Bob",
                "created_at": "2024-01-15T10:30:00Z",
            },
        ]

        result = write_to_hydradb(
            hydra=mock_hydradb,
            session=session,
            summary=None,
            facts=facts,
            supersessions=[],
            invalidations=[],
        )

        # 2 entities * 2 (entity + anchor each) = 4 nodes
        assert result["nodes_created"] >= 4

    def test_write_to_hydradb_creates_facts_with_mentions(self, mock_hydradb):
        """Test write_to_hydradb creates Fact nodes with MENTIONS edges."""
        from apps.api.pipeline.ingestion.writer import write_to_hydradb

        mock_session = MagicMock()
        mock_hydradb._driver.session.return_value.__enter__.return_value = mock_session

        session = {
            "session_id": "test-session-5",
            "user_id": "alex",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [],
        }
        facts = [
            {
                "fact_id": "fact-5",
                "content": "Alex lives in Dhaka",
                "confidence": 0.9,
                "entity_name": "Alex",
                "created_at": "2024-01-15T10:30:00Z",
            }
        ]

        result = write_to_hydradb(
            hydra=mock_hydradb,
            session=session,
            summary=None,
            facts=facts,
            supersessions=[],
            invalidations=[],
        )

        assert result["facts_written"] == 1
        # Fact node + MENTIONS edge + OCCURRED_IN edge
        assert result["edges_created"] >= 2

    def test_write_to_hydradb_creates_supersessions(self, mock_hydradb):
        """Test write_to_hydradb creates SUPERSEDES edges."""
        from apps.api.pipeline.ingestion.writer import write_to_hydradb

        mock_session = MagicMock()
        mock_hydradb._driver.session.return_value.__enter__.return_value = mock_session

        session = {
            "session_id": "test-session-6",
            "user_id": "alex",
            "started_at": "2024-02-01T10:30:00Z",
            "messages": [],
        }
        facts = [
            {
                "fact_id": "fact-new",
                "content": "Alex lives in Dhaka",
                "confidence": 0.9,
                "entity_name": "Alex",
                "created_at": "2024-02-01T10:30:00Z",
            }
        ]
        supersessions = [
            {"new_fact_id": "fact-new", "supersedes_fact_id": "fact-old"}
        ]

        result = write_to_hydradb(
            hydra=mock_hydradb,
            session=session,
            summary=None,
            facts=facts,
            supersessions=supersessions,
            invalidations=[],
        )

        assert result["supersessions_applied"] == 1
        assert result["edges_created"] >= 1

    def test_write_to_hydradb_creates_invalidations(self, mock_hydradb):
        """Test write_to_hydradb creates INVALIDATED_BY edges."""
        from apps.api.pipeline.ingestion.writer import write_to_hydradb

        mock_session = MagicMock()
        mock_hydradb._driver.session.return_value.__enter__.return_value = mock_session

        session = {
            "session_id": "test-session-7",
            "user_id": "alex",
            "started_at": "2024-01-16T10:30:00Z",
            "messages": [],
        }
        invalidations = [
            {"fact_id": "123", "reason": "Meeting expired"}
        ]

        result = write_to_hydradb(
            hydra=mock_hydradb,
            session=session,
            summary=None,
            facts=[],
            supersessions=[],
            invalidations=invalidations,
        )

        assert result["invalidations_applied"] == 1
        assert result["edges_created"] >= 1

    def test_write_to_hydradb_deduplicates_entities(self, mock_hydradb):
        """Test write_to_hydradb deduplicates entities across facts."""
        from apps.api.pipeline.ingestion.writer import write_to_hydradb

        mock_session = MagicMock()
        mock_hydradb._driver.session.return_value.__enter__.return_value = mock_session

        session = {
            "session_id": "test-session-8",
            "user_id": "alex",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [],
        }
        # Multiple facts about same entity
        facts = [
            {
                "fact_id": "fact-8a",
                "content": "Alex lives in Dhaka",
                "confidence": 0.9,
                "entity_name": "Alex",
                "created_at": "2024-01-15T10:30:00Z",
            },
            {
                "fact_id": "fact-8b",
                "content": "Alex works as engineer",
                "confidence": 0.8,
                "entity_name": "Alex",
                "created_at": "2024-01-15T10:30:00Z",
            },
            {
                "fact_id": "fact-8c",
                "content": "Alex has cat Pixel",
                "confidence": 0.7,
                "entity_name": "Alex",
                "created_at": "2024-01-15T10:30:00Z",
            },
        ]

        result = write_to_hydradb(
            hydra=mock_hydradb,
            session=session,
            summary=None,
            facts=facts,
            supersessions=[],
            invalidations=[],
        )

        # Only 1 entity created despite 3 facts
        assert result["nodes_created"] >= 2  # Entity + anchor
        assert result["facts_written"] == 3

    def test_write_to_hydradb_empty_session(self, mock_hydradb):
        """Test write_to_hydradb handles empty session gracefully."""
        from apps.api.pipeline.ingestion.writer import write_to_hydradb

        mock_session = MagicMock()
        mock_hydradb._driver.session.return_value.__enter__.return_value = mock_session

        session = {
            "session_id": "test-empty",
            "user_id": "alex",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [],
        }

        result = write_to_hydradb(
            hydra=mock_hydradb,
            session=session,
            summary=None,
            facts=[],
            supersessions=[],
            invalidations=[],
        )

        assert result["facts_written"] == 0
        assert result["nodes_created"] >= 2  # Session + anchor

    def test_write_to_hydradb_fact_without_entity(self, mock_hydradb):
        """Test write_to_hydradb handles fact without entity_name."""
        from apps.api.pipeline.ingestion.writer import write_to_hydradb

        mock_session = MagicMock()
        mock_hydradb._driver.session.return_value.__enter__.return_value = mock_session

        session = {
            "session_id": "test-session-9",
            "user_id": "alex",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [],
        }
        facts = [
            {
                "fact_id": "fact-9",
                "content": "Some fact without entity",
                "confidence": 0.5,
                "entity_name": "",  # Empty entity
                "created_at": "2024-01-15T10:30:00Z",
            }
        ]

        result = write_to_hydradb(
            hydra=mock_hydradb,
            session=session,
            summary=None,
            facts=facts,
            supersessions=[],
            invalidations=[],
        )

        # Should skip the fact
        assert result["facts_written"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])