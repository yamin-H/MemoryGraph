"""Unit tests for evaluation baseline implementations."""

import pytest
from unittest.mock import MagicMock, patch
import numpy as np


class TestVectorBaseline:
    """Tests for VectorBaseline."""

    def test_init(self):
        """Test baseline initializes correctly."""
        from apps.api.eval.baselines.vector_baseline import VectorBaseline

        with patch("apps.api.eval.baselines.vector_baseline.psycopg.connect") as mock_connect:
            mock_connect.return_value = MagicMock()
            b = VectorBaseline(groq_api_key="test-key")
            assert b.postgres_url is not None
            assert b.groq_api_key == "test-key"
            assert b._conn is None

    def test_init_default_env_fallback(self):
        """Test baseline falls back to environment variables."""
        from apps.api.eval.baselines.vector_baseline import VectorBaseline

        with patch("apps.api.eval.baselines.vector_baseline.psycopg.connect") as mock_connect:
            mock_connect.return_value = MagicMock()
            with patch.dict("os.environ", {"GROQ_API_KEY": "env-key", "POSTGRES_URL": "postgresql://test:5432/db"}):
                b = VectorBaseline()
                assert b.groq_api_key == "env-key"
                assert b.postgres_url == "postgresql://test:5432/db"

    def test_add_sessions(self):
        """Test add_sessions extracts facts and stores embeddings."""
        from apps.api.eval.baselines.vector_baseline import VectorBaseline

        with patch("apps.api.eval.baselines.vector_baseline.psycopg.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.closed = False

            b = VectorBaseline(groq_api_key="test-key")

            # Mock the encoder
            with patch.object(b, "_get_encoder") as mock_get_encoder:
                mock_encoder = MagicMock()
                mock_encoder.encode.return_value = np.array([0.1, 0.2, 0.3])
                mock_get_encoder.return_value = mock_encoder

                sessions = [
                    {
                        "session_id": "test-1",
                        "user_id": "alex",
                        "messages": [
                            {"role": "user", "content": "I'm Alex. I live in Dhaka. I work as a software engineer."},
                            {"role": "assistant", "content": "Nice to meet you!"},
                        ],
                    }
                ]

                b.add_sessions(sessions)

                # Verify encoder was called for user messages
                assert mock_encoder.encode.called
                # Verify INSERT was called
                mock_conn.cursor.return_value.__enter__.return_value.execute.assert_called()

    def test_query_with_results(self):
        """Test query returns answer when facts found."""
        from apps.api.eval.baselines.vector_baseline import VectorBaseline

        with patch("apps.api.eval.baselines.vector_baseline.psycopg.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.closed = False

            b = VectorBaseline(groq_api_key="test-key")

            # Mock encoder
            with patch.object(b, "_get_encoder") as mock_get_encoder:
                mock_encoder = MagicMock()
                mock_encoder.encode.return_value = np.array([0.1, 0.2, 0.3])
                mock_get_encoder.return_value = mock_encoder

                # Mock Groq
                mock_groq = MagicMock()
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message.content = "Alex lives in Dhaka."
                mock_groq.chat.completions.create.return_value = mock_response

                with patch.object(b, "_get_groq", return_value=mock_groq):
                    # Mock DB query result
                    mock_cursor = MagicMock()
                    mock_cursor.fetchall.return_value = [("Alex lives in Dhaka", 0.95)]
                    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

                    result = b.query("Where does Alex live?", "alex")

                    assert result["answer"] == "Alex lives in Dhaka."
                    assert result["abstained"] is False
                    assert result["confidence"] == 0.7
                    assert result["latency_ms"] >= 0

    def test_query_no_results(self):
        """Test query returns abstention when no facts found."""
        from apps.api.eval.baselines.vector_baseline import VectorBaseline

        with patch("apps.api.eval.baselines.vector_baseline.psycopg.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.closed = False

            b = VectorBaseline(groq_api_key="test-key")

            # Mock encoder
            with patch.object(b, "_get_encoder") as mock_get_encoder:
                mock_encoder = MagicMock()
                mock_encoder.encode.return_value = np.array([0.1, 0.2, 0.3])
                mock_get_encoder.return_value = mock_encoder

                mock_cursor = MagicMock()
                mock_cursor.fetchall.return_value = []
                mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

                result = b.query("Where does Bob live?", "bob")

                assert result["abstained"] is True
                assert result["confidence"] == 0.1
                assert "don't have" in result["answer"].lower()

    def test_query_fallback_no_groq(self):
        """Test query falls back to raw facts when Groq unavailable."""
        from apps.api.eval.baselines.vector_baseline import VectorBaseline

        with patch("apps.api.eval.baselines.vector_baseline.psycopg.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.closed = False

            b = VectorBaseline(groq_api_key="test-key")

            # Mock encoder
            with patch.object(b, "_get_encoder") as mock_get_encoder:
                mock_encoder = MagicMock()
                mock_encoder.encode.return_value = np.array([0.1, 0.2, 0.3])
                mock_get_encoder.return_value = mock_encoder

                with patch.object(b, "_get_groq", return_value=None):
                    mock_cursor = MagicMock()
                    mock_cursor.fetchall.return_value = [("Alex lives in Dhaka", 0.95)]
                    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

                    result = b.query("Where does Alex live?", "alex")

                    assert "Alex lives in Dhaka" in result["answer"]
                    assert result["abstained"] is False

    def test_clear(self):
        """Test clear deletes all facts."""
        from apps.api.eval.baselines.vector_baseline import VectorBaseline

        with patch("apps.api.eval.baselines.vector_baseline.psycopg.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.closed = False

            b = VectorBaseline(groq_api_key="test-key")
            b.clear()
            mock_conn.cursor.return_value.__enter__.return_value.execute.assert_called_with("DELETE FROM facts")

    def test_close(self):
        """Test close properly closes connection."""
        from apps.api.eval.baselines.vector_baseline import VectorBaseline

        with patch("apps.api.eval.baselines.vector_baseline.psycopg.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.closed = False

            b = VectorBaseline(groq_api_key="test-key")
            b.close()
            assert b._conn is None


class TestLongContextBaseline:
    """Tests for LongContextBaseline."""

    def test_init(self):
        """Test baseline initializes correctly."""
        from apps.api.eval.baselines.longcontext_baseline import LongContextBaseline

        b = LongContextBaseline(groq_api_key="test-key")
        assert b.groq_api_key == "test-key"
        assert b.model == "llama-3.3-70b-versatile"
        assert b._groq_client is None
        assert b._user_sessions == {}

    def test_init_default_model(self):
        """Test default model is set."""
        from apps.api.eval.baselines.longcontext_baseline import LongContextBaseline

        b = LongContextBaseline(groq_api_key="test-key", model="llama-3.1-8b-instant")
        assert b.model == "llama-3.1-8b-instant"

    def test_add_sessions(self):
        """Test add_sessions stores sessions by user_id."""
        from apps.api.eval.baselines.longcontext_baseline import LongContextBaseline

        b = LongContextBaseline(groq_api_key="test-key")
        sessions = [
            {
                "session_id": "test-1",
                "user_id": "alex",
                "messages": [{"role": "user", "content": "Hello"}],
            },
            {
                "session_id": "test-2",
                "user_id": "alex",
                "messages": [{"role": "user", "content": "World"}],
            },
        ]
        b.add_sessions(sessions)

        assert "alex" in b._user_sessions
        assert len(b._user_sessions["alex"]) == 2

    def test_query_no_sessions(self):
        """Test query returns abstention with no sessions."""
        from apps.api.eval.baselines.longcontext_baseline import LongContextBaseline

        b = LongContextBaseline(groq_api_key="test-key")
        result = b.query("Where does Alex live?", "alex")

        assert result["abstained"] is True
        assert result["confidence"] == 0.1
        assert result["context_exceeded"] is False

    def test_query_with_groq(self):
        """Test query generates answer with Groq."""
        from apps.api.eval.baselines.longcontext_baseline import LongContextBaseline

        b = LongContextBaseline(groq_api_key="test-key")
        b.add_sessions([{
            "session_id": "test-1",
            "user_id": "alex",
            "messages": [{"role": "user", "content": "I live in Dhaka."}],
        }])

        mock_groq = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Alex lives in Dhaka."
        mock_groq.chat.completions.create.return_value = mock_response

        with patch.object(b, "_get_groq", return_value=mock_groq):
            result = b.query("Where does Alex live?", "alex")

        assert result["answer"] == "Alex lives in Dhaka."
        assert result["abstained"] is False
        assert result["source_sessions"] == ["test-1"]

    def test_query_no_groq(self):
        """Test query handles missing Groq client."""
        from apps.api.eval.baselines.longcontext_baseline import LongContextBaseline

        b = LongContextBaseline(groq_api_key=None)
        b.add_sessions([{
            "session_id": "test-1",
            "user_id": "alex",
            "messages": [{"role": "user", "content": "I live in Dhaka."}],
        }])

        with patch.object(b, "_get_groq", return_value=None):
            result = b.query("Where does Alex live?", "alex")

        assert result["abstained"] is True
        assert result["confidence"] == 0.0

    def test_query_context_exceeded_detection(self):
        """Test query detects context exceeded."""
        from apps.api.eval.baselines.longcontext_baseline import LongContextBaseline

        b = LongContextBaseline(groq_api_key="test-key")
        # Add a very large session
        big_content = "word " * 200000  # ~400k chars ≈ 100k tokens
        b.add_sessions([{
            "session_id": "test-1",
            "user_id": "alex",
            "messages": [{"role": "user", "content": big_content}],
        }])

        mock_groq = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Answer"
        mock_groq.chat.completions.create.return_value = mock_response

        with patch.object(b, "_get_groq", return_value=mock_groq):
            result = b.query("Question?", "alex")

        assert result["context_exceeded"] is True

    def test_query_api_error(self):
        """Test query handles Groq API error."""
        from apps.api.eval.baselines.longcontext_baseline import LongContextBaseline

        b = LongContextBaseline(groq_api_key="test-key")
        b.add_sessions([{
            "session_id": "test-1",
            "user_id": "alex",
            "messages": [{"role": "user", "content": "I live in Dhaka."}],
        }])

        mock_groq = MagicMock()
        mock_groq.chat.completions.create.side_effect = Exception("API error")

        with patch.object(b, "_get_groq", return_value=mock_groq):
            result = b.query("Where does Alex live?", "alex")

        assert "Error" in result["answer"]
        assert result["latency_ms"] >= 0

    def test_clear(self):
        """Test clear removes all sessions."""
        from apps.api.eval.baselines.longcontext_baseline import LongContextBaseline

        b = LongContextBaseline(groq_api_key="test-key")
        b.add_sessions([{
            "session_id": "test-1",
            "user_id": "alex",
            "messages": [{"role": "user", "content": "Hi"}],
        }])
        b.clear()
        assert b._user_sessions == {}


class TestMem0Baseline:
    """Tests for Mem0Baseline."""

    def test_init(self):
        """Test baseline initializes correctly."""
        from apps.api.eval.baselines.mem0_baseline import Mem0Baseline

        b = Mem0Baseline(groq_api_key="test-key")
        assert b.groq_api_key == "test-key"
        assert b._memory is None

    @patch("apps.api.eval.baselines.mem0_baseline.Mem0Baseline._get_memory")
    def test_add_sessions_skips_when_memory_unavailable(self, mock_get_memory):
        """Test add_sessions handles None memory gracefully."""
        from apps.api.eval.baselines.mem0_baseline import Mem0Baseline

        mock_get_memory.return_value = None
        b = Mem0Baseline(groq_api_key="test-key")
        # Should not raise
        b.add_sessions([{
            "session_id": "test-1",
            "user_id": "alex",
            "messages": [{"role": "user", "content": "Hi"}],
        }])

    @patch("apps.api.eval.baselines.mem0_baseline.Mem0Baseline._get_memory")
    def test_add_sessions_calls_memory_add(self, mock_get_memory):
        """Test add_sessions calls memory.add."""
        from apps.api.eval.baselines.mem0_baseline import Mem0Baseline

        mock_memory = MagicMock()
        mock_get_memory.return_value = mock_memory
        b = Mem0Baseline(groq_api_key="test-key")

        sessions = [{
            "session_id": "test-1",
            "user_id": "alex",
            "messages": [
                {"role": "user", "content": "I live in Dhaka."},
                {"role": "assistant", "content": "Nice!"},
            ],
        }]
        b.add_sessions(sessions)

        mock_memory.add.assert_called_once()
        call_args = mock_memory.add.call_args
        assert call_args[0][0] == [{"role": "user", "content": "I live in Dhaka."}, {"role": "assistant", "content": "Nice!"}]
        assert call_args[1]["user_id"] == "alex"

    @patch("apps.api.eval.baselines.mem0_baseline.Mem0Baseline._get_memory")
    def test_query_no_memory(self, mock_get_memory):
        """Test query returns abstention when memory unavailable."""
        from apps.api.eval.baselines.mem0_baseline import Mem0Baseline

        mock_get_memory.return_value = None
        b = Mem0Baseline(groq_api_key="test-key")
        result = b.query("Where does Alex live?", "alex")

        assert result["abstained"] is True
        assert result["confidence"] == 0.0

    @patch("apps.api.eval.baselines.mem0_baseline.Mem0Baseline._get_memory")
    def test_query_no_results(self, mock_get_memory):
        """Test query returns abstention when no search results."""
        from apps.api.eval.baselines.mem0_baseline import Mem0Baseline

        mock_memory = MagicMock()
        mock_memory.search.return_value = {"results": []}
        mock_get_memory.return_value = mock_memory

        b = Mem0Baseline(groq_api_key="test-key")
        result = b.query("Where does Alex live?", "alex")

        assert result["abstained"] is True
        assert result["confidence"] == 0.1

    @patch("apps.api.eval.baselines.mem0_baseline.Mem0Baseline._get_memory")
    def test_query_with_results(self, mock_get_memory):
        """Test query returns answer from mem0."""
        from apps.api.eval.baselines.mem0_baseline import Mem0Baseline

        mock_memory = MagicMock()
        mock_memory.search.return_value = {
            "results": [{"memory": "Alex lives in Dhaka"}]
        }
        mock_response = {"answer": "Alex lives in Dhaka"}
        mock_memory.query.return_value = mock_response
        mock_get_memory.return_value = mock_memory

        b = Mem0Baseline(groq_api_key="test-key")
        result = b.query("Where does Alex live?", "alex")

        assert result["answer"] == "Alex lives in Dhaka"
        assert result["abstained"] is False
        assert result["confidence"] == 0.7

    @patch("apps.api.eval.baselines.mem0_baseline.Mem0Baseline._get_memory")
    def test_query_search_exception(self, mock_get_memory):
        """Test query handles search exception."""
        from apps.api.eval.baselines.mem0_baseline import Mem0Baseline

        mock_memory = MagicMock()
        mock_memory.search.side_effect = Exception("Search failed")
        mock_get_memory.return_value = mock_memory

        b = Mem0Baseline(groq_api_key="test-key")
        result = b.query("Where does Alex live?", "alex")

        assert "Error" in result["answer"]

    @patch("apps.api.eval.baselines.mem0_baseline.Mem0Baseline._get_memory")
    def test_query_fallback_when_query_fails(self, mock_get_memory):
        """Test query falls back to facts context when memory.query fails."""
        from apps.api.eval.baselines.mem0_baseline import Mem0Baseline

        mock_memory = MagicMock()
        mock_memory.search.return_value = {
            "results": [{"memory": "Alex lives in Dhaka"}]
        }
        mock_memory.query.side_effect = Exception("Query failed")
        mock_get_memory.return_value = mock_memory

        b = Mem0Baseline(groq_api_key="test-key")
        result = b.query("Where does Alex live?", "alex")

        assert "Alex lives in Dhaka" in result["answer"]
        assert result["abstained"] is False

    def test_clear(self):
        """Test clear resets memory instance."""
        from apps.api.eval.baselines.mem0_baseline import Mem0Baseline

        b = Mem0Baseline(groq_api_key="test-key")
        b._memory = MagicMock()
        # Should not raise even if memory.close not available
        b.clear()
        assert b._memory is None


class TestBaselineIntegration:
    """Integration-style tests comparing baselines."""

    def test_all_baselines_have_same_interface(self):
        """Test all baselines implement common interface."""
        from apps.api.eval.baselines.vector_baseline import VectorBaseline
        from apps.api.eval.baselines.longcontext_baseline import LongContextBaseline
        from apps.api.eval.baselines.mem0_baseline import Mem0Baseline

        with patch("apps.api.eval.baselines.vector_baseline.psycopg.connect") as mock_connect:
            mock_connect.return_value = MagicMock()
            baseline_classes = [VectorBaseline, LongContextBaseline, Mem0Baseline]
            for cls in baseline_classes:
                b = cls(groq_api_key="test-key")
                assert hasattr(b, "add_sessions")
                assert hasattr(b, "query")
                assert hasattr(b, "clear")
                assert hasattr(b, "close")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])