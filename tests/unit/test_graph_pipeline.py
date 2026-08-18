"""Unit tests for the pipeline graph module."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone


class TestIngestionPipeline:
    """Tests for the ingestion pipeline graph."""

    def test_pipeline_state_typeddict(self):
        """Test PipelineState TypedDict structure."""
        from apps.api.pipeline.graph import PipelineState

        state: PipelineState = {
            "session": {},
            "facts": [],
            "summary": None,
            "supersessions": [],
            "invalidations": [],
            "write_result": None,
            "error": None,
            "failed_step": None,
        }

        assert "session" in state
        assert "facts" in state
        assert "error" in state

    def test_retrieval_state_typeddict(self):
        """Test RetrievalState TypedDict structure."""
        from apps.api.pipeline.graph import RetrievalState

        state: RetrievalState = {
            "question": "",
            "parsed_question": {},
            "retrieved_facts": [],
            "ranked_facts": [],
            "abstention_result": {},
            "confidence_result": {},
            "answer": None,
            "error": None,
            "failed_step": None,
        }

        assert "question" in state
        assert "parsed_question" in state
        assert "answer" in state

    @pytest.mark.asyncio
    async def test_load_session_node_valid(self):
        """Test load_session_node passes valid session."""
        from apps.api.pipeline.graph import load_session_node

        state = {
            "session": {
                "session_id": "test-1",
                "user_id": "alex",
                "started_at": "2024-01-15T10:30:00Z",
                "messages": [{"role": "user", "content": "Hello"}],
            }
        }

        result = load_session_node(state)

        assert result == {}

    @pytest.mark.asyncio
    async def test_load_session_node_missing(self):
        """Test load_session_node returns error for missing session."""
        from apps.api.pipeline.graph import load_session_node

        state = {"session": None}

        result = load_session_node(state)

        assert result["error"] == "No session provided"
        assert result["failed_step"] == "load_session"

    @pytest.mark.asyncio
    async def test_load_session_node_empty(self):
        """Test load_session_node returns error for empty session."""
        from apps.api.pipeline.graph import load_session_node

        state = {"session": {}}

        result = load_session_node(state)

        assert result["error"] == "No session provided"
        assert result["failed_step"] == "load_session"

    def test_check_error_continues(self):
        """Test check_error returns 'continue' when no error."""
        from apps.api.pipeline.graph import check_error

        state = {"error": None}

        result = check_error(state)

        assert result == "continue"

    def test_check_error_ends(self):
        """Test check_error returns 'end' when error present."""
        from apps.api.pipeline.graph import check_error

        state = {"error": "Some error"}

        result = check_error(state)

        assert result == "end"

    @pytest.mark.asyncio
    async def test_extract_facts_node_no_api_key(self):
        """Test extract_facts_node gracefully uses rule-based fallback when GROQ_API_KEY missing."""
        from apps.api.pipeline.graph import extract_facts_node

        state = {"session": {"session_id": "test", "messages": [{"role": "user", "content": "I live in Berlin."}]}}

        with patch.dict("os.environ", {}, clear=True):
            result = extract_facts_node(state)

        assert "facts" in result
        assert isinstance(result["facts"], list)

    @pytest.mark.asyncio
    async def test_summarize_session_node_no_api_key(self):
        """Test summarize_session_node gracefully returns rule-based summary when GROQ_API_KEY missing."""
        from apps.api.pipeline.graph import summarize_session_node

        state = {"session": {"session_id": "test", "messages": [{"role": "user", "content": "Hello"}]}}

        with patch("apps.api.pipeline.graph.os.environ.get", return_value=""):
            result = summarize_session_node(state)

        assert "summary" in result
        assert result["summary"]["topic"] == "General Dialogue"

    @pytest.mark.asyncio
    async def test_resolve_entities_node_placeholder(self):
        """Test resolve_entities_node is a placeholder."""
        from apps.api.pipeline.graph import resolve_entities_node

        state = {"facts": [{"content": "fact1"}, {"content": "fact2"}]}

        result = resolve_entities_node(state)

        assert result == {}

    @pytest.mark.asyncio
    async def test_confirm_ingestion_node_success(self):
        """Test confirm_ingestion_node passes with write_result."""
        from apps.api.pipeline.graph import confirm_ingestion_node

        state = {
            "write_result": {
                "session_id": "test-1",
                "facts_written": 5,
                "nodes_created": 10,
                "edges_created": 8,
            }
        }

        result = confirm_ingestion_node(state)

        assert result == {}

    @pytest.mark.asyncio
    async def test_confirm_ingestion_node_failure(self):
        """Test confirm_ingestion_node returns error when no write_result."""
        from apps.api.pipeline.graph import confirm_ingestion_node

        state = {"write_result": None}

        result = confirm_ingestion_node(state)

        assert result["error"] == "No write result"
        assert result["failed_step"] == "confirm_ingestion"

    def test_check_retrieval_error_continues(self):
        """Test check_retrieval_error returns 'continue' when no error."""
        from apps.api.pipeline.graph import check_retrieval_error

        state = {"error": None}

        result = check_retrieval_error(state)

        assert result == "continue"

    def test_check_retrieval_error_ends(self):
        """Test check_retrieval_error returns 'end' when error present."""
        from apps.api.pipeline.graph import check_retrieval_error

        state = {"error": "Some error"}

        result = check_retrieval_error(state)

        assert result == "end"

    @pytest.mark.asyncio
    async def test_parse_question_node_no_api_key(self):
        """Test parse_question_node returns error when GROQ_API_KEY missing."""
        from apps.api.pipeline.graph import parse_question_node

        state = {"question": "Where does Alex live?"}

        with patch.dict("os.environ", {}, clear=True):
            result = parse_question_node(state)

        assert result["error"] == "GROQ_API_KEY not set"
        assert result["failed_step"] == "parse_question"

    @pytest.mark.asyncio
    async def test_rank_by_time_node(self):
        """Test rank_by_time_node calls rank_facts_by_time."""
        from apps.api.pipeline.graph import rank_by_time_node

        facts = [
            {"content": "Fact 1", "created_at": "2024-01-15T10:00:00Z", "is_current": True},
            {"content": "Fact 2", "created_at": "2024-01-10T10:00:00Z", "is_current": False},
        ]
        state = {"retrieved_facts": facts}

        result = rank_by_time_node(state)

        assert "ranked_facts" in result
        assert len(result["ranked_facts"]) == 2

    @pytest.mark.asyncio
    async def test_abstention_check_node(self):
        """Test abstention_check_node calls check_abstention."""
        from apps.api.pipeline.graph import abstention_check_node

        state = {
            "ranked_facts": [
                {"content": "Alex lives in Dhaka", "is_current": True}
            ],
            "parsed_question": {
                "entity_name": "Alex",
                "question_type": "current_fact",
                "keywords": ["live"]
            }
        }

        result = abstention_check_node(state)

        assert "abstention_result" in result
        assert "should_abstain" in result["abstention_result"]

    @pytest.mark.asyncio
    async def test_score_confidence_node(self):
        """Test score_confidence_node calls calculate_confidence."""
        from apps.api.pipeline.graph import score_confidence_node

        state = {
            "abstention_result": {
                "should_abstain": False,
                "facts_to_use": [{"content": "Alex lives in Dhaka", "confidence": 0.9, "is_current": True}],
            },
            "parsed_question": {
                "entity_name": "Alex",
                "question_type": "current_fact",
                "keywords": ["live"]
            }
        }

        with patch("apps.api.pipeline.graph.HydraDB") as mock_hydra_cls:
            mock_hydra = MagicMock()
            mock_hydra_cls.return_value = mock_hydra
            with patch("apps.api.pipeline.graph.get_confidence_evidence", return_value={"Alex": {"in_degree": 2, "out_degree": 1}}):
                result = score_confidence_node(state)

        assert "confidence_result" in result
        assert "score" in result["confidence_result"]
        assert "reasoning" in result["confidence_result"]

    def test_build_pipeline_structure(self):
        """Test build_pipeline creates correct graph structure."""
        from apps.api.pipeline.graph import build_pipeline

        graph = build_pipeline()

        assert graph is not None
        # Check nodes exist
        node_names = list(graph.nodes.keys())
        expected_nodes = [
            "load_session",
            "extract_facts",
            "summarize_session",
            "resolve_entities",
            "detect_supersessions",
            "detect_invalidations",
            "write_to_hydradb",
            "confirm_ingestion",
        ]
        for node in expected_nodes:
            assert node in node_names

    def test_build_retrieval_pipeline_structure(self):
        """Test build_retrieval_pipeline creates correct graph structure."""
        from apps.api.pipeline.graph import build_retrieval_pipeline

        graph = build_retrieval_pipeline()

        assert graph is not None
        # Check nodes exist
        node_names = list(graph.nodes.keys())
        expected_nodes = [
            "parse_question",
            "graph_traversal",
            "rank_by_time",
            "abstention_check",
            "score_confidence",
            "generate_answer",
        ]
        for node in expected_nodes:
            assert node in node_names

    @pytest.mark.asyncio
    async def test_with_retry_success(self):
        """Test with_retry returns result on first try."""
        from apps.api.pipeline.graph import with_retry

        def success_func():
            return "success"

        result = with_retry(success_func)

        assert result == "success"

    @pytest.mark.asyncio
    async def test_with_retry_retries(self):
        """Test with_retry retries on failure."""
        from apps.api.pipeline.graph import with_retry

        call_count = 0

        def fail_twice_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"

        result = with_retry(fail_twice_then_succeed, max_retries=3)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_with_retry_exhausted(self):
        """Test with_retry raises after max retries exhausted."""
        from apps.api.pipeline.graph import with_retry

        def always_fail():
            raise ValueError("Permanent error")

        with pytest.raises(ValueError, match="Permanent error"):
            with_retry(always_fail, max_retries=2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])