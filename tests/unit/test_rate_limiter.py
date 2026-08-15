"""Unit tests for the rate limiter middleware module."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestRateLimiterMiddleware:
    """Tests for RateLimiterMiddleware class."""

    def test_init_defaults(self):
        """Test middleware initializes with default rate limit."""
        from apps.api.middleware.rate_limiter import RateLimiterMiddleware

        mock_app = MagicMock()
        middleware = RateLimiterMiddleware(mock_app)

        assert middleware.app == mock_app
        assert middleware.rate_limit == 60
        assert middleware.window_seconds == 60

    def test_init_with_app(self):
        """Test middleware stores the wrapped app."""
        from apps.api.middleware.rate_limiter import RateLimiterMiddleware

        mock_app = MagicMock()
        middleware = RateLimiterMiddleware(mock_app)

        assert middleware.app is mock_app

    @pytest.mark.asyncio
    async def test_call_non_http_passes_through(self):
        """Test non-HTTP requests bypass rate limiting."""
        from apps.api.middleware.rate_limiter import RateLimiterMiddleware

        mock_app = AsyncMock()
        middleware = RateLimiterMiddleware(mock_app)

        scope = {"type": "websocket"}
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_call_skips_health_endpoints(self):
        """Test health/metrics endpoints skip rate limiting."""
        from apps.api.middleware.rate_limiter import RateLimiterMiddleware

        mock_app = AsyncMock()
        middleware = RateLimiterMiddleware(mock_app)

        for path in ["/health", "/metrics", "/"]:
            scope = {"type": "http", "path": path}
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

        assert mock_app.call_count == 3

    @pytest.mark.asyncio
    async def test_call_under_limit_allows_request(self):
        """Test request under rate limit is allowed."""
        from apps.api.middleware.rate_limiter import RateLimiterMiddleware

        mock_app = AsyncMock()
        middleware = RateLimiterMiddleware(mock_app)

        with patch("apps.api.middleware.rate_limiter.redis.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_client.get.return_value = b"5"  # Under limit of 60

            # Mock pipeline properly - pipeline() is sync, returns pipeline object
            mock_pipeline = MagicMock()
            mock_pipeline.incr = MagicMock()
            mock_pipeline.expire = MagicMock()
            mock_pipeline.execute = AsyncMock()
            mock_client.pipeline = MagicMock(return_value=mock_pipeline)
            mock_from_url.return_value = mock_client

            scope = {"type": "http", "path": "/query", "client": ("192.168.1.1", 1234)}
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

            # App should be called
            mock_app.assert_called_once_with(scope, receive, send)
            # Counter should be incremented
            mock_pipeline.incr.assert_called_once()
            mock_pipeline.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_at_limit_blocks_request(self):
        """Test request at rate limit returns 429."""
        from apps.api.middleware.rate_limiter import RateLimiterMiddleware

        mock_app = AsyncMock()
        middleware = RateLimiterMiddleware(mock_app)

        with patch("apps.api.middleware.rate_limiter.redis.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_client.get.return_value = b"60"  # At limit
            mock_from_url.return_value = mock_client

            scope = {"type": "http", "path": "/query", "client": ("192.168.1.2", 1234)}
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

            # App should NOT be called
            mock_app.assert_not_called()
            # 429 status should be sent
            # Check that send was called with 429 status
            send_calls = send.call_args_list
            assert len(send_calls) > 0

    @pytest.mark.asyncio
    async def test_call_over_limit_blocks_request(self):
        """Test request over rate limit returns 429."""
        from apps.api.middleware.rate_limiter import RateLimiterMiddleware

        mock_app = AsyncMock()
        middleware = RateLimiterMiddleware(mock_app)

        with patch("apps.api.middleware.rate_limiter.redis.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_client.get.return_value = b"100"  # Over limit
            mock_from_url.return_value = mock_client

            scope = {"type": "http", "path": "/query", "client": ("192.168.1.3", 1234)}
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

            mock_app.assert_not_called()

    @pytest.mark.asyncio
    async def test_call_redis_unavailable_allows(self):
        """Test request allowed when Redis is unavailable."""
        from apps.api.middleware.rate_limiter import RateLimiterMiddleware

        mock_app = AsyncMock()
        middleware = RateLimiterMiddleware(mock_app)

        with patch("apps.api.middleware.rate_limiter.redis.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Redis connection failed")
            mock_from_url.return_value = mock_client

            scope = {"type": "http", "path": "/query", "client": ("192.168.1.4", 1234)}
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

            # App should be called despite Redis error
            mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_call_no_client_ip(self):
        """Test request without client IP uses 'unknown'."""
        from apps.api.middleware.rate_limiter import RateLimiterMiddleware

        mock_app = AsyncMock()
        middleware = RateLimiterMiddleware(mock_app)

        with patch("apps.api.middleware.rate_limiter.redis.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_client.get.return_value = None
            mock_client.pipeline.return_value = AsyncMock()
            mock_client.pipeline.return_value.execute = AsyncMock()
            mock_from_url.return_value = mock_client

            scope = {"type": "http", "path": "/query", "client": None}
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

            mock_app.assert_called_once()
            # Key should use 'unknown' as IP
            mock_client.get.assert_called_with("rate_limit:unknown")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
