"""Metrics routes for MemoryGraph API."""

from typing import Any

from fastapi import APIRouter
import redis.asyncio as redis
import neo4j
from neo4j import GraphDatabase

from db.hydra import HydraDB

router = APIRouter()


async def get_redis():
    """Get Redis client."""
    import os
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    return redis.from_url(redis_url)


@router.get("/metrics")
async def get_metrics() -> dict[str, Any]:
    """Get API metrics.

    Returns:
        Metrics including query counts, latency, token usage, and graph stats
    """
    metrics = {
        "total_queries": 0,
        "total_ingestions": 0,
        "avg_query_latency_ms": 0.0,
        "total_groq_tokens_used": 0,
        "total_facts_stored": 0,
        "sessions_ingested": 0,
        "entities_tracked": 0,
        "abstention_rate": 0.0,
    }

    # Redis Metrics
    redis_client = None
    try:
        redis_client = await get_redis()
        total_queries = await redis_client.get("metrics:total_queries")
        if total_queries:
            metrics["total_queries"] = int(total_queries)

        total_ingestions = await redis_client.get("metrics:total_ingestions")
        if total_ingestions:
            metrics["total_ingestions"] = int(total_ingestions)

        avg_latency = await redis_client.get("metrics:avg_query_latency_ms")
        if avg_latency:
            metrics["avg_query_latency_ms"] = float(avg_latency)

        total_tokens = await redis_client.get("metrics:total_groq_tokens")
        if total_tokens:
            metrics["total_groq_tokens_used"] = int(total_tokens)

        # Calculate abstention rate
        total_abstained = await redis_client.get("metrics:total_abstained")
        if total_abstained and metrics["total_queries"] > 0:
            metrics["abstention_rate"] = round(int(total_abstained) / metrics["total_queries"], 3)
    except Exception:
        pass
    finally:
        if redis_client:
            try:
                await redis_client.close()
            except Exception:
                pass

    # Graph statistics from HydraDB
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
            metrics["total_facts_stored"] = f_res.single()[0] or 0

            s_res = session.run("MATCH (s:Session) RETURN count(s)")
            metrics["sessions_ingested"] = s_res.single()[0] or 0

            e_res = session.run("MATCH (e:Entity) RETURN count(e)")
            metrics["entities_tracked"] = e_res.single()[0] or 0
    except Exception:
        pass
    finally:
        if hydra_db and created_own:
            try:
                hydra_db.close()
            except Exception:
                pass

    return metrics
