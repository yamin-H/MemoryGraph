"""Test FastAPI HTTP API routes directly."""

import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "apps" / "api"))
sys.path.insert(0, str(root_dir))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_api():
    """Verify HTTP responses for health, metrics, benchmark, and graph endpoints."""
    print("Testing FastAPI HTTP Endpoints...")

    # 1. Health
    r = client.get("/health")
    print(f"GET /health -> status={r.status_code}, data={r.json().get('status')}")
    assert r.status_code == 200

    # 2. Metrics
    r = client.get("/metrics")
    print(f"GET /metrics -> status={r.status_code}, facts={r.json().get('total_facts_stored')}")
    assert r.status_code == 200

    # 3. Benchmark datasets
    r = client.get("/benchmark/datasets")
    print(f"GET /benchmark/datasets -> status={r.status_code}, datasets={len(r.json())}")
    assert r.status_code == 200
    assert len(r.json()) == 4

    # 4. Benchmark samples
    r = client.get("/benchmark/dataset/longmemeval/samples?limit=5")
    print(f"GET /benchmark/dataset/longmemeval/samples -> status={r.status_code}, total={r.json().get('total')}")
    assert r.status_code == 200

    # 5. Graph all
    r = client.get("/graph/all")
    print(f"GET /graph/all -> status={r.status_code}, nodes={len(r.json().get('nodes', []))}")
    assert r.status_code == 200

    print("\n[ALL HTTP ENDPOINTS PASSED SUCCESSFULLY!]")


if __name__ == "__main__":
    test_api()
