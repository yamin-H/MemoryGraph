"""Tests for the memory service layer."""

from unittest.mock import MagicMock

from apps.api.services.memory_service import MemoryService


def test_memory_service_exposes_core_methods():
    """The service layer should provide the main backend operations."""
    service = MemoryService()

    assert hasattr(service, "ingest_session")
    assert hasattr(service, "query_memory")
    assert hasattr(service, "get_session_graph")
    assert hasattr(service, "get_entity_history")


def test_memory_service_uses_hydradb_when_present():
    """The service should keep HydraDB as the source of truth."""
    service = MemoryService()

    assert service.hydra is not None


def test_get_session_graph_builds_valid_edges():
    """Session graph edges should link back to the session node, not to the message ID itself."""
    service = MemoryService()
    service.hydra.ensure_connected = MagicMock()
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    service.hydra._driver = mock_driver

    session_record = MagicMock()
    session_record.__getitem__ = lambda self, key: {"s.id": 101, "s.session_id": "s-1", "s.user_id": "u-1", "s.started_at": "2024-01-01"}[key]
    message_record = MagicMock()
    message_record.__getitem__ = lambda self, key: {"m.id": 202, "m.role": "user", "m.content": "Hello there", "m.created_at": "2024-01-01"}[key]
    fact_record = MagicMock()
    fact_record.__getitem__ = lambda self, key: {"f.id": 303, "f.content": "Alex lives in Dhaka", "f.confidence": 0.9, "f.is_current": True}[key]

    mock_session.run.side_effect = [
        MagicMock(single=MagicMock(return_value=session_record)),
        MagicMock(__iter__=lambda self: iter([message_record])),
        MagicMock(__iter__=lambda self: iter([fact_record])),
    ]

    result = service.get_session_graph("s-1")

    assert any(edge["type"] == "CONTAINS" and edge["source"] == 101 and edge["target"] == 202 for edge in result["edges"])
    assert any(edge["type"] == "OCCURRED_IN" and edge["source"] == 303 and edge["target"] == 101 for edge in result["edges"])


def test_query_memory_accepts_user_context_and_get_entity_memory_tracks_temporal_state():
    """User-scoped queries and entity memory should expose current, historical, and invalidated facts."""
    service = MemoryService()

    payload = service.query_memory("Where does Alex live?", user_id="alex")
    assert isinstance(payload, dict)
    assert "answer" in payload
    assert "confidence" in payload

    temporal = service.get_entity_memory("Alex")
    assert set(temporal.keys()) >= {"entity_name", "current_facts", "historical_facts", "invalidated_facts"}
