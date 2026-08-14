"""Health routes for MemoryGraph API."""

import os
from typing import Any

from fastapi import APIRouter
from groq import Groq
import redis.asyncio as redis

from db.hydra import HydraDB

router = APIRouter()


def get_hydra():
    """Get HydraDB client using bearer token auth."""
    import neo4j
    from neo4j import GraphDatabase
    uri = os.environ.get("HYDRADB_URI", "neo4j://127.0.0.1:7687")
    token = os.environ.get("HYDRADB_TOKEN", "local-development-token-32-bytes")
    driver = GraphDatabase.driver(uri, auth=neo4j.bearer_auth(token))
    return driver


async def get_redis():
    """Get Redis client."""
    import os
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    return redis.from_url(redis_url)


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Check health of all services.

    Returns:
        Health status and statistics
    """
    status = {
        "api": "ok",
        "hydradb": "ok",
        "redis": "ok",
        "groq": "ok",
    }

    driver = get_hydra()
    redis_client = await get_redis()

    # Check HydraDB
    try:
        with driver.session() as session:
            session.run("MATCH (f:Fact) RETURN count(*)")
    except Exception as e:
        print(f"HydraDB health check error: {e}")
        status["hydradb"] = "error"
    finally:
        driver.close()

    # Check Redis
    try:
        await redis_client.ping()
    except Exception:
        status["redis"] = "error"

    # Check Groq
    try:
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key:
            client = Groq(api_key=api_key)
            client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
        else:
            status["groq"] = "no_api_key"
    except Exception:
        status["groq"] = "error"

    # Get statistics from HydraDB
    facts_stored = 0
    sessions_ingested = 0
    entities_tracked = 0

    driver = get_hydra()
    try:
        with driver.session() as session:
            # Count facts
            result = session.run("MATCH (f:Fact) RETURN f.id")
            facts_stored = len(list(result))

            # Count sessions
            result = session.run("MATCH (s:Session) RETURN s.id")
            sessions_ingested = len(list(result))

            # Count entities
            result = session.run("MATCH (e:Entity) RETURN e.id")
            entities_tracked = len(list(result))
    except Exception:
        pass
    finally:
        driver.close()

    # Get average query latency from Redis
    avg_query_latency_ms = 0
    try:
        latency_data = await redis_client.get("metrics:avg_query_latency_ms")
        if latency_data:
            avg_query_latency_ms = float(latency_data)
    except Exception:
        pass

    return {
        **status,
        "facts_stored": facts_stored,
        "sessions_ingested": sessions_ingested,
        "entities_tracked": entities_tracked,
        "avg_query_latency_ms": avg_query_latency_ms,
    }
