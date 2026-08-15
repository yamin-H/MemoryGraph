"""Unit tests for the cost tracker middleware module."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestCostTrackerMiddleware:
    """Tests for CostTrackerMiddleware class."""

    def test_init_stores_app(self):
        """Test middleware initializes with wrapped app."""
        from apps.api.middleware.cost_tracker import CostTrackerMiddleware

        mock_app = MagicMock()
        middleware = CostTrackerMiddleware(mock_app)

        assert middleware.app == mock_app

    @pytest.mark.asyncio
    async def test_call_non_http_passes_through(self):
        """Test non-HTTP requests bypass cost tracking."""
        from apps.api.middleware.cost_tracker import CostTrackerMiddleware

        mock_app = AsyncMock()
        middleware = CostTrackerMiddleware(mock_app)

        scope = {"type": "websocket"}
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)
        mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_call_tracks_query_metrics(self):
        """Test /query endpoint updates query metrics in Redis."""
        from apps.api.middleware.cost_tracker import CostTrackerMiddleware

        mock_app = AsyncMock()
        middleware = CostTrackerMiddleware(mock_app)

        with patch("apps.api.middleware.cost_tracker.redis.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_client.get.return_value = b"10"
            mock_from_url.return_value = mock_client

            scope = {"type": "http", "path": "/query/test"}
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

            # Should increment query metrics
            mock_client.incr.assert_called_with("metrics:total_queries")
            mock_client.incrby.assert_called_with("metrics:total_query_latency_ms", pytest.approx(0, abs=10000))

    @pytest.mark.asyncio
    async def test_call_tracks_ingest_metrics(self):
        """Test /ingest endpoint updates ingestion metrics in Redis."""
        from apps.api.middleware.cost_tracker import CostTrackerMiddleware

        mock_app = AsyncMock()
        middleware = CostTrackerMiddleware(mock_app)

        with patch("apps.api.middleware.cost_tracker.redis.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_from_url.return_value = mock_client

            scope = {"type": "http", "path": "/ingest/test"}
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

            # Should increment ingestion metrics
            mock_client.incr.assert_called_with("metrics:total_ingestions")

    @pytest.mark.asyncio
    async def test_call_tracks_request_metrics(self):
        """Test all requests store request-level metrics."""
        from apps.api.middleware.cost_tracker import CostTrackerMiddleware

        mock_app = AsyncMock()
        middleware = CostTrackerMiddleware(mock_app)

        with patch("apps.api.middleware.cost_tracker.redis.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_client.get.return_value = None
            mock_from_url.return_value = mock_client

            scope = {"type": "http", "path": "/query/test"}
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

            # Should store request metrics with hset
            assert mock_client.hset.called
            hset_args = mock_client.hset.call_args
            assert hset_args[0][0].startswith("request:")

    @pytest.mark.asyncio
    async def test_call_sets_request_ttl(self):
        """Test request metrics have 1-hour TTL."""
        from apps.api.middleware.cost_tracker import CostTrackerMiddleware

        mock_app = AsyncMock()
        middleware = CostTrackerMiddleware(mock_app)

        with patch("apps.api.middleware.cost_tracker.redis.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_client.get.return_value = None
            mock_from_url.return_value = mock_client

            scope = {"type": "http", "path": "/query/test"}
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

            # Should set TTL on request key
            assert mock_client.expire.called
            expire_args = mock_client.expire.call_args
            assert expire_args[0][1] == 3600

    @pytest.mark.asyncio
    async def test_call_redis_unavailable_continues(self):
        """Test request continues when Redis is unavailable."""
        from apps.api.middleware.cost_tracker import CostTrackerMiddleware

        mock_app = AsyncMock()
        middleware = CostTrackerMiddleware(mock_app)

        with patch("apps.api.middleware.cost_tracker.redis.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_client.incr.side_effect = Exception("Redis connection failed")
            mock_from_url.return_value = mock_client

            scope = {"type": "http", "path": "/query/test"}
            receive = AsyncMock()
            send = AsyncMock()

            # Should not raise
            await middleware(scope, receive, send)

            # App should still be called (with wrapped send function)
            mock_app.assert_called_once()
            call_args = mock_app.call_args
            assert call_args[0][0] == scope
            assert call_args[0][1] == receive
            # send will be a wrapper function, not the original

    @pytest.mark.asyncio
    async def test_call_generates_request_id(self):
        """Test each request gets a unique ID."""
        from apps.api.middleware.cost_tracker import CostTrackerMiddleware

        mock_app = AsyncMock()
        middleware = CostTrackerMiddleware(mock_app)

        with patch("apps.api.middleware.cost_tracker.redis.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_client.get.return_value = None
            mock_from_url.return_value = mock_client

            scope = {"type": "http", "path": "/query/test"}
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

            # Request ID should be in hset key
            hset_args = mock_client.hset.call_args
            request_key = hset_args[0][0]
            assert request_key.startswith("request:")
            # Request ID should be 8 chars
            request_id = request_key.split(":")[1]
            assert len(request_id) == 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
