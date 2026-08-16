"""Cost tracker middleware for MemoryGraph API."""

import time
import uuid
import os
import redis.asyncio as redis


class CostTrackerMiddleware:
    """Tracks Groq token usage per request.

    Stores metrics in Redis for aggregation.
    """

    def __init__(self, app):
        """Initialize the cost and latency tracking middleware."""
        self.app = app

    async def __call__(self, scope, receive, send):
        """Intercept HTTP requests to record latency and endpoint invocation metrics."""
        # Only handle HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Generate request ID
        request_id = str(uuid.uuid4())[:8]

        # Track start time
        start_time = time.time()

        # Capture the path from scope
        path = scope["path"]

        # We need to intercept the response to calculate latency
        # Store original send to wrap it
        sent_response = False
        status_code = None

        async def send_wrapper(message):
            """ASGI send wrapper to intercept HTTP response status and body."""
            nonlocal sent_response, status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                sent_response = True

        # Process request
        await self.app(scope, receive, send_wrapper)

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        # Get Redis URL
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")

        try:
            # Connect to Redis
            redis_client = redis.from_url(redis_url)

            # Update metrics based on endpoint
            if "/query" in path:
                await redis_client.incr("metrics:total_queries")
                await redis_client.incrby("metrics:total_query_latency_ms", latency_ms)

                # Update average latency
                total_queries = await redis_client.get("metrics:total_queries")
                total_latency = await redis_client.get("metrics:total_query_latency_ms")
                if total_queries and total_latency:
                    avg_latency = int(total_latency) / int(total_queries)
                    await redis_client.set("metrics:avg_query_latency_ms", str(avg_latency))

            elif "/ingest" in path:
                await redis_client.incr("metrics:total_ingestions")

            # Store request-level metrics
            await redis_client.hset(
                f"request:{request_id}",
                mapping={
                    "path": path,
                    "latency_ms": latency_ms,
                    "timestamp": time.time(),
                },
            )
            await redis_client.expire(f"request:{request_id}", 3600)  # 1 hour TTL

            await redis_client.close()

        except Exception:
            # If Redis is unavailable, continue without tracking
            pass
