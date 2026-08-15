"""Unit tests for evaluation benchmark runner."""

import json
import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path


class TestMemoryGraphSystem:
    """Tests for MemoryGraphSystem wrapper."""

    def test_init(self):
        """Test system initializes correctly."""
        from apps.api.eval.runner import MemoryGraphSystem

        system = MemoryGraphSystem()
        assert system._initialized is False

    @patch("apps.api.eval.runner.run_pipeline")
    def test_add_sessions(self, mock_run_pipeline):
        """Test add_sessions calls run_pipeline for each session."""
        from apps.api.eval.runner import MemoryGraphSystem

        mock_run_pipeline.return_value = {"write_result": {"facts_written": 5}}

        system = MemoryGraphSystem()
        sessions = [
            {"session_id": "1", "user_id": "alex", "messages": []},
            {"session_id": "2", "user_id": "alex", "messages": []},
        ]
        system.add_sessions(sessions)

        assert mock_run_pipeline.call_count == 2

    @patch("apps.api.eval.runner.run_pipeline")
    def test_add_sessions_logs_error(self, mock_run_pipeline):
        """Test add_sessions logs error when ingestion fails."""
        from apps.api.eval.runner import MemoryGraphSystem

        mock_run_pipeline.return_value = {"error": "Ingestion failed"}

        system = MemoryGraphSystem()
        sessions = [{"session_id": "1", "user_id": "alex", "messages": []}]

        with patch("builtins.print") as mock_print:
            system.add_sessions(sessions)
            # Should print warning
            mock_print.assert_called()

    @patch("apps.api.eval.runner.run_retrieval")
    def test_query(self, mock_run_retrieval):
        """Test query calls run_retrieval and returns formatted result."""
        from apps.api.eval.runner import MemoryGraphSystem

        mock_run_retrieval.return_value = {
            "answer": {
                "answer": "Alex lives in Dhaka",
                "confidence": 0.9,
                "abstained": False,
                "source_sessions": ["session-1"],
                "query_time_ms": 100,
            }
        }

        system = MemoryGraphSystem()
        result = system.query("Where does Alex live?", "alex")

        assert result["answer"] == "Alex lives in Dhaka"
        assert result["confidence"] == 0.9
        assert result["abstained"] is False
        assert result["source_sessions"] == ["session-1"]
        assert result["latency_ms"] == 100

    @patch("apps.api.eval.runner.run_retrieval")
    def test_query_with_error(self, mock_run_retrieval):
        """Test query handles error in retrieval."""
        from apps.api.eval.runner import MemoryGraphSystem

        mock_run_retrieval.return_value = {"error": "Retrieval failed"}

        system = MemoryGraphSystem()
        result = system.query("Where does Alex live?", "alex")

        # When error at top level, answer dict is empty, so abstained defaults to False
        assert result["answer"] == ""
        assert result["confidence"] == 0.0
        assert result["abstained"] is False  # Default when answer dict is empty
        assert result["latency_ms"] == 0

    def test_clear(self):
        """Test clear is a no-op placeholder."""
        from apps.api.eval.runner import MemoryGraphSystem

        system = MemoryGraphSystem()
        # Should not raise
        system.clear()


class TestRunBenchmark:
    """Tests for run_benchmark function."""

    def test_run_benchmark_basic(self):
        """Test basic benchmark execution."""
        from apps.api.eval.runner import run_benchmark, SYSTEMS, DATASETS

        # Create mock systems
        mock_system_a = MagicMock()
        mock_system_a.add_sessions = MagicMock()
        mock_system_a.query.return_value = {
            "answer": "Test answer",
            "confidence": 0.8,
            "abstained": False,
            "latency_ms": 100,
            "context_exceeded": False,
        }
        mock_system_a.clear = MagicMock()
        mock_system_a.close = MagicMock()

        mock_system_b = MagicMock()
        mock_system_b.add_sessions = MagicMock()
        mock_system_b.query.return_value = {
            "answer": "Test answer 2",
            "confidence": 0.7,
            "abstained": False,
            "latency_ms": 150,
            "context_exceeded": False,
        }
        mock_system_b.clear = MagicMock()
        mock_system_b.close = MagicMock()

        # Mock datasets
        mock_dataset = MagicMock()
        mock_dataset.load.return_value = [
            {
                "question_id": "q1",
                "question": "Where does Alex live?",
                "answer": "Dhaka",
                "sessions": [{"session_id": "s1", "user_id": "alex", "messages": []}],
            }
        ]

        with patch.dict("apps.api.eval.runner.SYSTEMS", {"system_a": lambda: mock_system_a, "system_b": lambda: mock_system_b}):
            with patch.dict("apps.api.eval.runner.DATASETS", {"dataset_1": lambda: mock_dataset}):
                with patch("builtins.print"):  # Suppress prints
                    results = run_benchmark(
                        systems=["system_a", "system_b"],
                        datasets=["dataset_1"],
                        max_examples_per_dataset=1,
                    )

        assert "results" in results
        assert "dataset_1" in results["results"]
        assert "system_a" in results["results"]["dataset_1"]
        assert "system_b" in results["results"]["dataset_1"]
        assert len(results["results"]["dataset_1"]["system_a"]) == 1
        assert len(results["results"]["dataset_1"]["system_b"]) == 1

    def test_run_benchmark_saves_results(self, tmp_path):
        """Test benchmark saves results to file."""
        from apps.api.eval.runner import run_benchmark, SYSTEMS, DATASETS

        mock_system = MagicMock()
        mock_system.add_sessions = MagicMock()
        mock_system.query.return_value = {
            "answer": "Test answer",
            "confidence": 0.8,
            "abstained": False,
            "latency_ms": 100,
            "context_exceeded": False,
        }
        mock_system.clear = MagicMock()
        mock_system.close = MagicMock()

        mock_dataset = MagicMock()
        mock_dataset.load.return_value = [
            {
                "question_id": "q1",
                "question": "Where does Alex live?",
                "answer": "Dhaka",
                "sessions": [{"session_id": "s1", "user_id": "alex", "messages": []}],
            }
        ]

        output_file = tmp_path / "benchmark_results.json"

        with patch.dict("apps.api.eval.runner.SYSTEMS", {"system_a": lambda: mock_system}):
            with patch.dict("apps.api.eval.runner.DATASETS", {"dataset_1": lambda: mock_dataset}):
                with patch("builtins.print"):  # Suppress prints
                    run_benchmark(
                        systems=["system_a"],
                        datasets=["dataset_1"],
                        max_examples_per_dataset=1,
                        output_file=str(output_file),
                    )

        assert output_file.exists()
        with open(output_file) as f:
            data = json.load(f)
        assert "results" in data

    def test_run_benchmark_handles_exception(self):
        """Test benchmark handles exceptions during query."""
        from apps.api.eval.runner import run_benchmark, SYSTEMS, DATASETS

        mock_system = MagicMock()
        mock_system.add_sessions = MagicMock()
        mock_system.query.side_effect = Exception("Query failed")
        mock_system.clear = MagicMock()
        mock_system.close = MagicMock()

        mock_dataset = MagicMock()
        mock_dataset.load.return_value = [
            {
                "question_id": "q1",
                "question": "Where does Alex live?",
                "answer": "Dhaka",
                "sessions": [{"session_id": "s1", "user_id": "alex", "messages": []}],
            }
        ]

        with patch.dict("apps.api.eval.runner.SYSTEMS", {"system_a": lambda: mock_system}):
            with patch.dict("apps.api.eval.runner.DATASETS", {"dataset_1": lambda: mock_dataset}):
                with patch("builtins.print"):  # Suppress prints
                    results = run_benchmark(
                        systems=["system_a"],
                        datasets=["dataset_1"],
                        max_examples_per_dataset=1,
                    )

        # Should have error in result
        system_result = results["results"]["dataset_1"]["system_a"][0]
        assert system_result["error"] == "Query failed"
        assert system_result["abstained"] is True
        assert system_result["confidence"] == 0.0

    def test_run_benchmark_clears_between_examples(self):
        """Test benchmark clears system between examples."""
        from apps.api.eval.runner import run_benchmark, SYSTEMS, DATASETS

        mock_system = MagicMock()
        mock_system.add_sessions = MagicMock()
        mock_system.query.return_value = {
            "answer": "Test answer",
            "confidence": 0.8,
            "abstained": False,
            "latency_ms": 100,
            "context_exceeded": False,
        }
        mock_system.clear = MagicMock()
        mock_system.close = MagicMock()

        mock_dataset = MagicMock()
        mock_dataset.load.return_value = [
            {"question_id": "q1", "question": "Q1?", "answer": "A1", "sessions": []},
            {"question_id": "q2", "question": "Q2?", "answer": "A2", "sessions": []},
        ]

        with patch.dict("apps.api.eval.runner.SYSTEMS", {"system_a": lambda: mock_system}):
            with patch.dict("apps.api.eval.runner.DATASETS", {"dataset_1": lambda: mock_dataset}):
                with patch("builtins.print"):
                    run_benchmark(
                        systems=["system_a"],
                        datasets=["dataset_1"],
                        max_examples_per_dataset=2,
                    )

        # Clear should be called between each example
        assert mock_system.clear.call_count == 2

    def test_run_benchmark_closes_system(self):
        """Test benchmark closes system after all examples."""
        from apps.api.eval.runner import run_benchmark, SYSTEMS, DATASETS

        mock_system = MagicMock()
        mock_system.add_sessions = MagicMock()
        mock_system.query.return_value = {
            "answer": "Test answer",
            "confidence": 0.8,
            "abstained": False,
            "latency_ms": 100,
            "context_exceeded": False,
        }
        mock_system.clear = MagicMock()
        mock_system.close = MagicMock()

        mock_dataset = MagicMock()
        mock_dataset.load.return_value = [
            {"question_id": "q1", "question": "Q1?", "answer": "A1", "sessions": []},
        ]

        with patch.dict("apps.api.eval.runner.SYSTEMS", {"system_a": lambda: mock_system}):
            with patch.dict("apps.api.eval.runner.DATASETS", {"dataset_1": lambda: mock_dataset}):
                with patch("builtins.print"):
                    run_benchmark(
                        systems=["system_a"],
                        datasets=["dataset_1"],
                        max_examples_per_dataset=1,
                    )

        mock_system.close.assert_called_once()


class TestMain:
    """Tests for main function."""

    @patch("apps.api.eval.runner.run_benchmark")
    def test_main_calls_run_benchmark(self, mock_run_benchmark):
        """Test main calls run_benchmark with parsed args."""
        from apps.api.eval.runner import main

        with patch("sys.argv", ["runner.py", "--systems", "vector", "--datasets", "longmemeval", "--max-examples", "5"]):
            main()

        mock_run_benchmark.assert_called_once_with(
            systems=["vector"],
            datasets=["longmemeval"],
            max_examples_per_dataset=5,
            output_file=None,
        )

    @patch("apps.api.eval.runner.run_benchmark")
    def test_main_default_args(self, mock_run_benchmark):
        """Test main with default args."""
        from apps.api.eval.runner import main

        with patch("sys.argv", ["runner.py"]):
            main()

        mock_run_benchmark.assert_called_once_with(
            systems=None,
            datasets=None,
            max_examples_per_dataset=None,
            output_file=None,
        )


class TestRunnerIntegration:
    """Integration-style tests for runner with real components."""

    def test_systems_dict_contains_all_systems(self):
        """Test SYSTEMS dict has all expected systems."""
        from apps.api.eval.runner import SYSTEMS

        expected = ["vector", "longcontext", "mem0", "memorygraph"]
        for sys in expected:
            assert sys in SYSTEMS

    def test_datasets_dict_contains_all_datasets(self):
        """Test DATASETS dict has all expected datasets."""
        from apps.api.eval.runner import DATASETS

        expected = ["longmemeval", "longmemeval_v2", "beam"]
        for ds in expected:
            assert ds in DATASETS

    def test_memorygraph_system_instantiates(self):
        """Test MemoryGraphSystem can be instantiated."""
        from apps.api.eval.runner import SYSTEMS

        system_class = SYSTEMS["memorygraph"]
        system = system_class()
        assert hasattr(system, "add_sessions")
        assert hasattr(system, "query")
        assert hasattr(system, "clear")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])