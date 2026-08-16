"""Rate limiter middleware for MemoryGraph API."""

import time
from fastapi import Request
from fastapi.responses import JSONResponse
import redis.asyncio as redis
import os


class RateLimiterMiddleware:
    """Rate limiter middleware using Redis.

    Limits requests to 60 per minute per IP address.
    """

    def __init__(self, app):
        """Initialize the rate limiting middleware with default request thresholds."""
        self.app = app
        self.rate_limit = 60  # requests per minute
        self.window_seconds = 60  # time window

    async def __call__(self, scope, receive, send):
        """Evaluate client IP against sliding window rate limit in Redis."""
        # Only handle HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Parse request path from scope
        path = scope["path"]

        # Skip rate limiting for health/metrics endpoints
        if path in ["/health", "/metrics", "/"]:
            await self.app(scope, receive, send)
            return

        # Get Redis URL
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")

        try:
            # Connect to Redis
            redis_client = redis.from_url(redis_url)

            # Get client IP from headers or scope
            client_ip = scope.get("client", ("unknown", None))[0] if scope.get("client") else "unknown"
            key = f"rate_limit:{client_ip}"

            # Check current count
            current = await redis_client.get(key)
            current_count = int(current) if current else 0

            if current_count >= self.rate_limit:
                await redis_client.close()
                # Send 429 response
                response = JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "detail": f"Maximum {self.rate_limit} requests per minute",
                    },
                )
                await response(scope, receive, send)
                return

            # Increment counter
            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, self.window_seconds)
            await pipe.execute()

            await redis_client.close()

        except Exception:
            # If Redis is unavailable, allow the request
            pass

        await self.app(scope, receive, send)
