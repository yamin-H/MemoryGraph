"""Metrics routes for MemoryGraph API."""

from typing import Any

from fastapi import APIRouter
import redis.asyncio as redis

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
        Metrics including query counts, latency, token usage
    """
    metrics = {
        "total_queries": 0,
        "total_ingestions": 0,
        "avg_query_latency_ms": 0.0,
        "total_groq_tokens_used": 0,
        "total_facts_stored": 0,
        "abstention_rate": 0.0,
    }

    redis_client = await get_redis()

    try:
        # Get metrics from Redis
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

        total_facts = await redis_client.get("metrics:total_facts_stored")
        if total_facts:
            metrics["total_facts_stored"] = int(total_facts)

        # Calculate abstention rate
        total_abstained = await redis_client.get("metrics:total_abstained")
        if total_abstained and total_queries:
            metrics["abstention_rate"] = int(total_abstained) / int(total_queries)

    except Exception:
        pass
    finally:
        await redis_client.close()

    return metrics
