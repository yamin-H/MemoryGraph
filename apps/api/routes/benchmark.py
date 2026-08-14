"""Benchmark routes for MemoryGraph API."""

import asyncio
import time
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks
import redis.asyncio as redis

from pipeline.graph import run_pipeline, run_retrieval

router = APIRouter()


async def get_redis():
    """Get Redis client."""
    import os
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    return redis.from_url(redis_url)

# Store benchmark results in memory (would use Redis in production)
benchmark_results: dict[str, dict[str, Any]] = {}


async def run_benchmark_job(job_id: str, redis_client: redis.Redis):
    """Run benchmark in background."""
    results = {
        "job_id": job_id,
        "status": "running",
        "start_time": time.time(),
        "tests": [],
    }

    # Test 1: Ingestion performance
    test_session = {
        "session_id": f"benchmark-{job_id}",
        "user_id": "benchmark-user",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [
            {"role": "user", "content": "Hello, I'm testing the benchmark."},
            {"role": "assistant", "content": "I'll help you test the benchmark."},
            {"role": "user", "content": "I work as a test engineer."},
            {"role": "assistant", "content": "Testing is important!"},
        ],
    }

    start = time.time()
    ingestion_result = run_pipeline(test_session)
    ingestion_time = time.time() - start

    results["tests"].append({
        "name": "ingestion",
        "duration_ms": int(ingestion_time * 1000),
        "success": not ingestion_result.get("error"),
    })

    # Test 2: Query performance
    start = time.time()
    query_result = run_retrieval("What is the test engineer's job?")
    query_time = time.time() - start

    results["tests"].append({
        "name": "query",
        "duration_ms": int(query_time * 1000),
        "success": not query_result.get("error"),
    })

    # Test 3: Batch ingestion (5 sessions)
    batch_start = time.time()
    for i in range(5):
        session = {
            "session_id": f"benchmark-{job_id}-{i}",
            "user_id": f"benchmark-user-{i}",
            "started_at": "2024-01-15T10:30:00Z",
            "messages": [
                {"role": "user", "content": f"Test message {i}"},
                {"role": "assistant", "content": f"Response {i}"},
            ],
        }
        run_pipeline(session)
    batch_time = time.time() - batch_start

    results["tests"].append({
        "name": "batch_ingestion_5",
        "duration_ms": int(batch_time * 1000),
        "success": True,
    })

    # Finalize results
    results["status"] = "completed"
    results["end_time"] = time.time()
    results["total_duration_ms"] = int((results["end_time"] - results["start_time"]) * 1000)

    # Store results
    benchmark_results[job_id] = results

    # Update Redis metrics
    await redis_client.set("benchmark:last_job_id", job_id)


@router.get("/results")
async def get_benchmark_results() -> dict[str, Any]:
    """Get cached benchmark results.

    Returns:
        Last benchmark results or empty if not run
    """
    if not benchmark_results:
        return {
            "status": "no_results",
            "message": "No benchmark has been run yet",
        }

    # Return most recent results
    last_job_id = max(benchmark_results.keys())
    return benchmark_results[last_job_id]


@router.post("/run")
async def run_benchmark(background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Trigger a benchmark run.

    Returns:
        Job ID for tracking
    """
    job_id = str(uuid.uuid4())[:8]
    redis_client = await get_redis()

    # Start benchmark in background
    background_tasks.add_task(run_benchmark_job, job_id, redis_client)

    return {
        "status": "started",
        "job_id": job_id,
        "message": "Benchmark running in background",
    }
