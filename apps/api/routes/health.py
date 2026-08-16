"""Health routes for MemoryGraph API."""

import os
from typing import Any

from fastapi import APIRouter
from groq import Groq
import redis.asyncio as redis

from db.hydra import HydraDB

router = APIRouter()


def get_hydra():
    """Get HydraDB client using Neo4j username/password auth."""
    import neo4j
    from neo4j import GraphDatabase
    uri = os.environ.get("HYDRADB_URI", "neo4j://127.0.0.1:7687")
    token = os.environ.get("HYDRADB_TOKEN", "neo4j/password")
    if "/" in token:
        username, password = token.split("/", 1)
        auth = neo4j.basic_auth(username, password)
    else:
        auth = neo4j.basic_auth("neo4j", token)
    driver = GraphDatabase.driver(uri, auth=auth)
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

    facts_stored = 0
    sessions_ingested = 0
    entities_tracked = 0
    avg_query_latency_ms = 0.0

    # Check HydraDB & Fetch graph counts with single session
    hydra_db = None
    created_own = False
    try:
        try:
            from main import hydra_client
            if hydra_client and hydra_client.is_connected:
                hydra_db = hydra_client
        except Exception:
            pass

        if hydra_db is None:
            hydra_db = HydraDB()
            hydra_db.connect()
            created_own = True

        with hydra_db._driver.session() as session:
            f_res = session.run("MATCH (f:Fact) RETURN count(f)")
            facts_stored = f_res.single()[0] or 0

            s_res = session.run("MATCH (s:Session) RETURN count(s)")
            sessions_ingested = s_res.single()[0] or 0

            e_res = session.run("MATCH (e:Entity) RETURN count(e)")
            entities_tracked = e_res.single()[0] or 0
    except Exception as e:
        print(f"HydraDB health check error: {e}")
        status["hydradb"] = "error"
    finally:
        if hydra_db and created_own:
            try:
                hydra_db.close()
            except Exception:
                pass

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
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
        else:
            status["groq"] = "no_api_key"
    except Exception:
        status["groq"] = "error"

    return {
        "status": "ok" if all(v == "ok" for v in status.values()) else "degraded",
        "services": {
            "api": {"status": status.get("api", "ok")},
            "hydradb": {"status": status.get("hydradb", "ok")},
            "redis": {"status": status.get("redis", "ok")},
            "groq": {"status": status.get("groq", "ok")},
        },
        "facts_stored": facts_stored,
        "sessions_ingested": sessions_ingested,
        "entities_tracked": entities_tracked,
        "avg_query_latency_ms": avg_query_latency_ms,
    }
