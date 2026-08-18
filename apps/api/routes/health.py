"""Health routes for MemoryGraph API."""

import os
from typing import Any

from fastapi import APIRouter, Request
from groq import Groq
import redis.asyncio as redis

from db.hydra import HydraDB

router = APIRouter()


async def get_redis():
    """Get Redis client."""
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    return redis.from_url(redis_url)


@router.get("/health")
async def health_check(request: Request) -> dict[str, Any]:
    """Check health of all services."""
    status = {
        "api": "ok",
        "hydradb": "ok",
        "redis": "ok",
        "groq": "ok",
    }

    facts_stored = 0
    sessions_ingested = 0
    entities_tracked = 0
    avg_query_latency_ms = 0.0
    hydradb_details: dict[str, Any] = HydraDB.engine_info()

    # Check HydraDB — use shared client from app.state
    hydra_db = getattr(request.app.state, "hydra", None)

    try:
        if hydra_db and hydra_db.is_connected:
            hydradb_details = hydra_db.health_details()
            with hydra_db._driver.session() as session:
                facts_stored = session.run(
                    "MATCH (f:Fact) RETURN count(*) AS cnt"
                ).single()["cnt"] or 0

                sessions_ingested = session.run(
                    "MATCH (s:Session) RETURN count(*) AS cnt"
                ).single()["cnt"] or 0

                entities_tracked = session.run(
                    "MATCH (e:Entity) RETURN count(*) AS cnt"
                ).single()["cnt"] or 0

            # Dual-protocol verification: also probe HydraDB HTTP REST API
            http_result = hydra_db.query_via_http("RETURN 1 AS ok")
            hydradb_details["http_api"] = http_result
        else:
            status["hydradb"] = "error"
            hydradb_details["connected"] = False
            hydradb_details["error"] = "HydraDB client not available on app.state"
    except Exception as e:
        print(f"HydraDB health check error: {e}")
        status["hydradb"] = "error"
        hydradb_details["connected"] = False
        hydradb_details["error"] = str(e)

    # Check Redis
    redis_client = None
    try:
        redis_client = await get_redis()
        await redis_client.ping()
        latency_data = await redis_client.get("metrics:avg_query_latency_ms")
        if latency_data:
            avg_query_latency_ms = float(latency_data)
    except Exception:
        status["redis"] = "error"
    finally:
        if redis_client:
            try:
                await redis_client.close()
            except Exception:
                pass

    # Check Groq
    try:
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key:
            client = Groq(api_key=api_key)
            client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
        else:
            status["groq"] = "no_api_key"
    except Exception:
        status["groq"] = "error"

    hydra_service = {
        "status": status.get("hydradb", "ok"),
        **hydradb_details,
    }

    return {
        "status": "ok" if all(v == "ok" for k, v in status.items() if not k.endswith("_error")) else "degraded",
        "services": {
            "api": {"status": status.get("api", "ok")},
            "hydradb": hydra_service,
            "redis": {"status": status.get("redis", "ok")},
            "groq": {"status": status.get("groq", "ok")},
        },
        "facts_stored": facts_stored,
        "sessions_ingested": sessions_ingested,
        "entities_tracked": entities_tracked,
        "avg_query_latency_ms": avg_query_latency_ms,
    }
