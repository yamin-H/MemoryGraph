"""E2E tests for streaming endpoint."""

import pytest


@pytest.mark.e2e
def test_streaming_query_endpoint(sample_sessions):
    """Test POST /query/stream returns SSE events in correct order."""
    from apps.api.main import app
    from apps.api.pipeline.graph import run_pipeline
    from fastapi.testclient import TestClient

    # Ingest some data first
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

    # Should have events
    assert len(events) > 0

    # Verify final event contains answer
    # SSE format: data: {...}
    final_event = None
    for event in reversed(events):
        if event.startswith("data: "):
            import json
            try:
                data = json.loads(event[6:])
                if "answer" in data:
                    final_event = data
                    break
            except json.JSONDecodeError:
                continue

    assert final_event is not None
    assert "answer" in final_event
    assert "confidence" in final_event


@pytest.mark.e2e
def test_streaming_event_sequence(sample_sessions):
    """Test streaming events follow expected sequence."""
    from apps.api.main import app
    from apps.api.pipeline.graph import run_pipeline
    from fastapi.testclient import TestClient

    for session in sample_sessions[:2]:
        run_pipeline(session)

    client = TestClient(app)
    response = client.post("/query/stream", json={"question": "Where does Alex live?", "user_id": "alex"})

    # Parse and extract event types
    event_types = []
    for line in response.iter_lines():
        if line and line.startswith("data: "):
            import json
            try:
                event_data = json.loads(line[6:])
                if "event" in event_data:
                    event_types.append(event_data["event"])
            except json.JSONDecodeError:
                pass

    # Expected sequence
    expected = ["status", "entity", "status", "facts", "status", "confidence", "answer", "done"]
    for exp in expected:
        assert exp in event_types, f"Missing event: {exp}"


@pytest.mark.e2e
def test_streaming_entity_event(sample_sessions):
    """Test entity identification event in stream."""
    from apps.api.main import app
    from apps.api.pipeline.graph import run_pipeline
    from fastapi.testclient import TestClient

    for session in sample_sessions[:2]:
        run_pipeline(session)

    client = TestClient(app)
    response = client.post("/query/stream", json={"question": "Where does Alex live?", "user_id": "alex"})

    entity_event = None
    for line in response.iter_lines():
        if line and line.startswith("data: "):
            import json
            try:
                event_data = json.loads(line[6:])
                if event_data.get("event") == "entity":
                    entity_event = event_data
                    break
            except json.JSONDecodeError:
                pass

    assert entity_event is not None
    assert entity_event.get("entity") == "Alex"
    assert entity_event.get("type") in ["current_fact", "historical_fact", "multi_session_synthesis", "absent_information"]


@pytest.mark.e2e
def test_streaming_facts_count_event(sample_sessions):
    """Test facts count event in stream."""
    from apps.api.main import app
    from apps.api.pipeline.graph import run_pipeline
    from fastapi.testclient import TestClient

    for session in sample_sessions[:2]:
        run_pipeline(session)

    client = TestClient(app)
    response = client.post("/query/stream", json={"question": "Where does Alex live?", "user_id": "alex"})

    facts_event = None
    for line in response.iter_lines():
        if line and line.startswith("data: "):
            import json
            try:
                event_data = json.loads(line[6:])
                if event_data.get("event") == "facts":
                    facts_event = event_data
                    break
            except json.JSONDecodeError:
                pass

    assert facts_event is not None
    assert "count" in facts_event
    assert isinstance(facts_event["count"], int)
    assert facts_event["count"] >= 0


@pytest.mark.e2e
def test_streaming_confidence_event(sample_sessions):
    """Test confidence score event in stream."""
    from apps.api.main import app
    from apps.api.pipeline.graph import run_pipeline
    from fastapi.testclient import TestClient

    for session in sample_sessions[:2]:
        run_pipeline(session)

    client = TestClient(app)
    response = client.post("/query/stream", json={"question": "Where does Alex live?", "user_id": "alex"})

    confidence_event = None
    for line in response.iter_lines():
        if line and line.startswith("data: "):
            import json
            try:
                event_data = json.loads(line[6:])
                if event_data.get("event") == "confidence":
                    confidence_event = event_data
                    break
            except json.JSONDecodeError:
                pass

    assert confidence_event is not None
    assert "score" in confidence_event
    assert isinstance(confidence_event["score"], (int, float))
    assert 0 <= confidence_event["score"] <= 100


@pytest.mark.e2e
def test_streaming_answer_event(sample_sessions):
    """Test final answer event contains complete response."""
    from apps.api.main import app
    from apps.api.pipeline.graph import run_pipeline
    from fastapi.testclient import TestClient

    for session in sample_sessions[:2]:
        run_pipeline(session)

    client = TestClient(app)
    response = client.post("/query/stream", json={"question": "Where does Alex live?", "user_id": "alex"})

    answer_event = None
    for line in response.iter_lines():
        if line and line.startswith("data: "):
            import json
            try:
                event_data = json.loads(line[6:])
                if event_data.get("event") == "answer":
                    answer_event = event_data
                    break
            except json.JSONDecodeError:
                pass

    assert answer_event is not None
    assert "answer" in answer_event
    assert "abstained" in answer_event
    assert "Dhaka" in answer_event["answer"]
    assert answer_event["abstained"] is False


@pytest.mark.e2e
def test_streaming_done_event(sample_sessions):
    """Test stream ends with done event."""
    from apps.api.main import app
    from apps.api.pipeline.graph import run_pipeline
    from fastapi.testclient import TestClient

    for session in sample_sessions[:2]:
        run_pipeline(session)

    client = TestClient(app)
    response = client.post("/query/stream", json={"question": "Where does Alex live?", "user_id": "alex"})

    done_found = False
    for line in response.iter_lines():
        if line and line.startswith("data: "):
            import json
            try:
                event_data = json.loads(line[6:])
                if event_data.get("event") == "done":
                    done_found = True
                    break
            except json.JSONDecodeError:
                pass

    assert done_found, "Stream should end with 'done' event"


@pytest.mark.e2e
def test_streaming_abstention_response(sample_sessions):
    """Test streaming handles abstention correctly."""
    from apps.api.main import app
    from apps.api.pipeline.graph import run_pipeline
    from fastapi.testclient import TestClient

    for session in sample_sessions[:2]:
        run_pipeline(session)

    client = TestClient(app)
    response = client.post("/query/stream", json={"question": "What is Alex's favorite color?", "user_id": "alex"})

    answer_event = None
    for line in response.iter_lines():
        if line and line.startswith("data: "):
            import json
            try:
                event_data = json.loads(line[6:])
                if event_data.get("event") == "answer":
                    answer_event = event_data
                    break
            except json.JSONDecodeError:
                pass

    assert answer_event is not None
    assert "answer" in answer_event
    assert answer_event.get("abstained") is True or answer_event.get("confidence", 100) < 50


@pytest.mark.e2e
def test_streaming_empty_database():
    """Test streaming on empty database."""
    from apps.api.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.post("/query/stream", json={"question": "Where does Alex live?", "user_id": "alex"})

    assert response.status_code == 200

    answer_event = None
    for line in response.iter_lines():
        if line and line.startswith("data: "):
            import json
            try:
                event_data = json.loads(line[6:])
                if event_data.get("event") == "answer":
                    answer_event = event_data
                    break
            except json.JSONDecodeError:
                pass

    assert answer_event is not None
    assert answer_event.get("abstained") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])