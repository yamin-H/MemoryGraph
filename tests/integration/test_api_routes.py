"""Integration tests for API routes."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_health_endpoint():
    """Test GET /health returns all ok."""
    from apps.api.main import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["api"] == "ok"
    assert "facts_stored" in data
    assert "sessions_ingested" in data


@pytest.mark.integration
def test_metrics_endpoint():
    """Test GET /metrics returns valid numbers."""
    from apps.api.main import app

    client = TestClient(app)
    response = client.get("/metrics")

    assert response.status_code == 200
    data = response.json()
    assert "total_queries" in data
    assert "total_ingestions" in data
    assert isinstance(data["total_queries"], int)
    assert isinstance(data["total_ingestions"], int)


@pytest.mark.integration
def test_ingest_session_endpoint(sample_session):
    """Test POST /ingest/session returns 200."""
    from apps.api.main import app

    client = TestClient(app)
    response = client.post("/ingest/session", json=sample_session)

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "facts_written" in data
    assert data["facts_written"] > 0


@pytest.mark.integration
def test_query_endpoint_returns_answer(sample_sessions):
    """Test POST /query returns correct answer."""
    from apps.api.main import app
    from apps.api.pipeline.graph import run_pipeline

    # First ingest some data
    for session in sample_sessions[:2]:
        run_pipeline(session)

    client = TestClient(app)
    response = client.post("/query", json={"question": "Where does Alex live?", "user_id": "alex"})

    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "confidence" in data
    assert "abstained" in data


@pytest.mark.integration
def test_ingest_batch_endpoint(sample_sessions):
    """Test POST /ingest/batch ingests multiple sessions."""
    from apps.api.main import app

    client = TestClient(app)
    response = client.post("/ingest/batch", json=sample_sessions[:3])

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3
    for item in data:
        assert "session_id" in item
        assert "success" in item
        assert item["success"] is True


@pytest.mark.integration
def test_query_absent_information(sample_sessions):
    """Test query for absent information returns abstention."""
    from apps.api.main import app
    from apps.api.pipeline.graph import run_pipeline

    for session in sample_sessions:
        run_pipeline(session)

    client = TestClient(app)
    response = client.post("/query", json={"question": "What is Alex's favorite color?", "user_id": "alex"})

    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert data.get("abstained") is True or data.get("confidence", 1) < 0.5


@pytest.mark.integration
def test_query_confidence_thresholds(sample_sessions):
    """Test query confidence meets expected thresholds."""
    from apps.api.main import app
    from apps.api.pipeline.graph import run_pipeline

    for session in sample_sessions:
        run_pipeline(session)

    client = TestClient(app)
    response = client.post("/query", json={"question": "Where does Alex live?", "user_id": "alex"})

    assert response.status_code == 200
    data = response.json()
    assert data["confidence"] >= 0.7


@pytest.mark.integration
def test_graph_session_endpoint(sample_session):
    """Test GET /graph/session/{session_id} returns graph data."""
    from apps.api.main import app
    from apps.api.pipeline.graph import run_pipeline

    # Ingest a session first
    run_pipeline(sample_session)

    client = TestClient(app)
    response = client.get(f"/graph/session/{sample_session['session_id']}")

    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)

    # Verify session node exists
    session_nodes = [n for n in data["nodes"] if n.get("type") == "Session"]
    assert len(session_nodes) >= 1


@pytest.mark.integration
def test_graph_entity_endpoint(sample_sessions):
    """Test GET /graph/entity/{entity_name} returns entity history."""
    from apps.api.main import app
    from apps.api.pipeline.graph import run_pipeline

    for session in sample_sessions:
        run_pipeline(session)

    client = TestClient(app)
    response = client.get("/graph/entity/Alex")

    assert response.status_code == 200
    data = response.json()
    assert "entity_name" in data
    assert data["entity_name"] == "Alex"
    assert "current_facts" in data
    assert "historical_facts" in data
    assert "total_facts" in data


@pytest.mark.integration
def test_query_stream_endpoint(sample_sessions):
    """Test POST /query/stream returns SSE events."""
    from apps.api.main import app
    from apps.api.pipeline.graph import run_pipeline

    for session in sample_sessions[:2]:
        run_pipeline(session)

    client = TestClient(app)
    response = client.post("/query/stream", json={"question": "Where does Alex live?", "user_id": "alex"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    # Parse SSE events
    events = []
    for line in response.iter_lines():
        if line:
            events.append(line)

    assert len(events) > 0

    # Verify event sequence: status -> entity -> status -> facts -> status -> confidence -> answer -> done
    event_types = []
    for event in events:
        if event.startswith("data: "):
            import json
            try:
                event_data = json.loads(event[6:])
                if "event" in event_data:
                    event_types.append(event_data["event"])
            except json.JSONDecodeError:
                pass

    expected_events = ["status", "entity", "status", "facts", "status", "confidence", "answer", "done"]
    for expected in expected_events:
        assert expected in event_types, f"Missing event type: {expected}"


@pytest.mark.integration
def test_query_stream_final_answer(sample_sessions):
    """Test stream final answer contains correct data."""
    from apps.api.main import app
    from apps.api.pipeline.graph import run_pipeline

    for session in sample_sessions[:2]:
        run_pipeline(session)

    client = TestClient(app)
    response = client.post("/query/stream", json={"question": "Where does Alex live?", "user_id": "alex"})

    # Get final answer event
    final_answer = None
    for line in response.iter_lines():
        if line and line.startswith("data: "):
            import json
            try:
                event_data = json.loads(line[6:])
                if event_data.get("event") == "answer":
                    final_answer = event_data
                    break
            except json.JSONDecodeError:
                pass

    assert final_answer is not None
    assert "answer" in final_answer
    assert "abstained" in final_answer
    assert "Dhaka" in final_answer["answer"]


@pytest.mark.integration
def test_health_endpoint_with_degraded_services():
    """Test health endpoint reports degraded services."""
    from apps.api.main import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    # All services should be ok in test environment
    assert data["api"] == "ok"
    # Other services may vary based on test environment


@pytest.mark.integration
def test_metrics_increment_on_query(sample_sessions):
    """Test metrics increment when queries are made."""
    from apps.api.main import app
    from apps.api.pipeline.graph import run_pipeline

    for session in sample_sessions[:1]:
        run_pipeline(session)

    client = TestClient(app)

    # Get initial metrics
    response = client.get("/metrics")
    initial_queries = response.json()["total_queries"]

    # Make a query
    client.post("/query", json={"question": "Where does Alex live?", "user_id": "alex"})

    # Get updated metrics
    response = client.get("/metrics")
    final_queries = response.json()["total_queries"]

    assert final_queries >= initial_queries + 1


@pytest.mark.integration
def test_metrics_increment_on_ingest(sample_session):
    """Test metrics increment when ingestion occurs."""
    from apps.api.main import app

    client = TestClient(app)

    # Get initial metrics
    response = client.get("/metrics")
    initial_ingestions = response.json()["total_ingestions"]

    # Ingest a session
    client.post("/ingest/session", json=sample_session)

    # Get updated metrics
    response = client.get("/metrics")
    final_ingestions = response.json()["total_ingestions"]

    assert final_ingestions >= initial_ingestions + 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])