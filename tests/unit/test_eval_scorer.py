"""Unit tests for evaluation scorer module."""

import pytest
from apps.api.eval.scorer import (
    normalize_answer,
    exact_match,
    contains_answer,
    score_example,
    compute_metrics,
    compute_metrics_by_type,
    generate_comparison_table,
    score_benchmark_results,
)


class TestNormalizeAnswer:
    """Tests for normalize_answer function."""

    def test_normalize_lowercase(self):
        """Test normalization converts to lowercase."""
        assert normalize_answer("HELLO WORLD") == "hello world"

    def test_normalize_strips_whitespace(self):
        """Test normalization strips leading/trailing whitespace."""
        assert normalize_answer("  hello  ") == "hello"

    def test_normalize_removes_punctuation(self):
        """Test normalization removes punctuation."""
        assert normalize_answer("Hello, World!") == "hello world"
        assert normalize_answer("What's up?") == "whats up"

    def test_normalize_collapses_whitespace(self):
        """Test normalization collapses multiple spaces."""
        assert normalize_answer("hello    world") == "hello world"

    def test_normalize_empty_string(self):
        """Test normalization handles empty string."""
        assert normalize_answer("") == ""
        assert normalize_answer("   ") == ""

    def test_normalize_none(self):
        """Test normalization handles None."""
        assert normalize_answer(None) == ""

    def test_normalize_numbers_preserved(self):
        """Test normalization preserves numbers."""
        assert normalize_answer("Version 1.2.3") == "version 123"


class TestExactMatch:
    """Tests for exact_match function."""

    def test_exact_match_identical(self):
        """Test exact match for identical strings."""
        assert exact_match("Alex lives in Dhaka", "Alex lives in Dhaka") is True

    def test_exact_match_case_insensitive(self):
        """Test exact match is case insensitive."""
        assert exact_match("ALEX LIVES IN DHAKA", "alex lives in dhaka") is True

    def test_exact_match_ignores_punctuation(self):
        """Test exact match ignores punctuation."""
        assert exact_match("Alex lives in Dhaka!", "Alex lives in Dhaka") is True

    def test_exact_match_different(self):
        """Test exact match for different strings."""
        assert exact_match("Alex lives in Dhaka", "Alex lives in London") is False

    def test_exact_match_empty(self):
        """Test exact match with empty strings."""
        assert exact_match("", "") is True
        assert exact_match("hello", "") is False


class TestContainsAnswer:
    """Tests for contains_answer function."""

    def test_contains_exact(self):
        """Test contains when exact match."""
        assert contains_answer("Alex lives in Dhaka", "Alex lives in Dhaka") is True

    def test_contains_partial(self):
        """Test contains when ground truth is substring."""
        assert contains_answer("Alex lives in Dhaka, Bangladesh", "Dhaka") is True

    def test_contains_reverse(self):
        """Test contains when prediction is substring of ground truth."""
        assert contains_answer("Dhaka", "Alex lives in Dhaka, Bangladesh") is True

    def test_contains_not_found(self):
        """Test contains when no match."""
        assert contains_answer("Alex lives in London", "Dhaka") is False

    def test_contains_case_insensitive(self):
        """Test contains is case insensitive."""
        assert contains_answer("ALEX LIVES IN DHAKA", "dhaka") is True


class TestScoreExample:
    """Tests for score_example function."""

    def test_score_correct_exact_match(self):
        """Test scoring correct exact match."""
        result = score_example("Alex lives in Dhaka", "Alex lives in Dhaka", False)

        assert result["exact_match"] is True
        assert result["contains_answer"] is True
        assert result["is_correct"] is True
        assert result["abstained"] is False
        assert result["false_abstention"] is False
        assert result["missed_abstention"] is False

    def test_score_correct_contains(self):
        """Test scoring correct partial match."""
        result = score_example("Alex lives in Dhaka, Bangladesh", "Dhaka", False)

        assert result["exact_match"] is False
        assert result["contains_answer"] is True
        assert result["is_correct"] is True
        assert result["abstained"] is False

    def test_score_incorrect(self):
        """Test scoring incorrect answer."""
        result = score_example("Alex lives in London", "Dhaka", False)

        assert result["exact_match"] is False
        assert result["contains_answer"] is False
        assert result["is_correct"] is False
        assert result["abstained"] is False

    def test_score_abstained_correct(self):
        """Test scoring when abstained but answer was correct."""
        result = score_example("Alex lives in Dhaka", "Alex lives in Dhaka", True)

        assert result["abstained"] is True
        assert result["false_abstention"] is True  # Shouldn't have abstained

    def test_score_abstained_incorrect(self):
        """Test scoring when abstained and answer was incorrect."""
        result = score_example("Alex lives in London", "Dhaka", True)

        assert result["abstained"] is True
        assert result["false_abstention"] is False

    def test_score_missed_abstention(self):
        """Test scoring missed abstention (should have abstained)."""
        # Model gave an answer but ground truth says "I don't know" - should have abstained
        result = score_example("Some random answer", "I don't know", False)

        assert result["abstained"] is False
        assert result["missed_abstention"] is True

    def test_score_missed_abstention_unknown(self):
        """Test missed abstention with 'unknown' ground truth."""
        result = score_example("Some answer", "unknown", False)

        assert result["missed_abstention"] is True

    def test_score_missed_abstention_no_info(self):
        """Test missed abstention with 'no information' ground truth."""
        result = score_example("Some answer", "no information", False)

        assert result["missed_abstention"] is True


class TestComputeMetrics:
    """Tests for compute_metrics function."""

    def test_compute_empty(self):
        """Test metrics for empty results."""
        metrics = compute_metrics([])

        assert metrics == {}

    def test_compute_all_correct(self):
        """Test metrics when all answers correct."""
        results = [
            {"is_correct": True, "exact_match": True, "contains_answer": True, "abstained": False, "latency_ms": 100},
            {"is_correct": True, "exact_match": True, "contains_answer": True, "abstained": False, "latency_ms": 200},
        ]
        metrics = compute_metrics(results)

        assert metrics["total_examples"] == 2
        assert metrics["exact_match_accuracy"] == 1.0
        assert metrics["contains_accuracy"] == 1.0
        assert metrics["overall_accuracy"] == 1.0
        assert metrics["abstention_rate"] == 0.0
        assert metrics["avg_latency_ms"] == 150.0

    def test_compute_some_correct(self):
        """Test metrics with mixed correct/incorrect."""
        results = [
            {"is_correct": True, "exact_match": True, "contains_answer": True, "abstained": False, "latency_ms": 100},
            {"is_correct": False, "exact_match": False, "contains_answer": False, "abstained": False, "latency_ms": 200},
            {"is_correct": True, "exact_match": False, "contains_answer": True, "abstained": False, "latency_ms": 300},
        ]
        metrics = compute_metrics(results)

        assert metrics["total_examples"] == 3
        assert metrics["exact_match_accuracy"] == 1/3
        assert metrics["contains_accuracy"] == 2/3
        assert metrics["overall_accuracy"] == 2/3

    def test_compute_with_abstentions(self):
        """Test metrics with abstentions."""
        results = [
            {"is_correct": True, "exact_match": True, "contains_answer": True, "abstained": False, "latency_ms": 100, "ground_truth": "Dhaka"},
            {"is_correct": False, "exact_match": False, "contains_answer": False, "abstained": True, "latency_ms": 0, "ground_truth": "I don't know"},
            {"is_correct": False, "exact_match": False, "contains_answer": False, "abstained": True, "latency_ms": 0, "ground_truth": "unknown"},
        ]
        metrics = compute_metrics(results)

        assert metrics["total_examples"] == 3
        assert metrics["abstention_rate"] == 2/3
        # Both abstentions were for questions that should abstain
        assert metrics["abstention_accuracy"] == 1.0
        assert metrics["false_abstention_rate"] == 0.0

    def test_compute_false_abstention(self):
        """Test metrics with false abstention."""
        # Use score_example to generate proper results
        results = [
            score_example("Dhaka", "Dhaka", True),  # Correct answer but abstained = false abstention
        ]
        metrics = compute_metrics(results)

        assert metrics["false_abstention_rate"] == 1.0

    def test_compute_missed_abstention(self):
        """Test metrics with missed abstention."""
        # Use score_example to generate proper results
        results = [
            score_example("Some answer", "I don't know", False),  # Wrong answer, should have abstained
        ]
        metrics = compute_metrics(results)

        assert metrics["missed_abstention_rate"] == 1.0

    def test_compute_avg_latency_excludes_zero(self):
        """Test average latency excludes zero values."""
        results = [
            {"is_correct": True, "exact_match": True, "contains_answer": True, "abstained": False, "latency_ms": 100},
            {"is_correct": True, "exact_match": True, "contains_answer": True, "abstained": True, "latency_ms": 0},
        ]
        metrics = compute_metrics(results)

        assert metrics["avg_latency_ms"] == 100.0

    def test_compute_context_exceeded_rate(self):
        """Test context exceeded rate calculation."""
        results = [
            {"is_correct": True, "exact_match": True, "contains_answer": True, "abstained": False, "latency_ms": 100, "context_exceeded": True},
            {"is_correct": True, "exact_match": True, "contains_answer": True, "abstained": False, "latency_ms": 200, "context_exceeded": False},
        ]
        metrics = compute_metrics(results)

        assert metrics["context_exceeded_rate"] == 0.5


class TestComputeMetricsByType:
    """Tests for compute_metrics_by_type function."""

    def test_compute_by_type_groups_correctly(self):
        """Test metrics grouped by question type."""
        results = [
            {"question_type": "current_fact", "is_correct": True, "exact_match": True, "contains_answer": True, "abstained": False, "latency_ms": 100},
            {"question_type": "current_fact", "is_correct": False, "exact_match": False, "contains_answer": False, "abstained": False, "latency_ms": 200},
            {"question_type": "historical_fact", "is_correct": True, "exact_match": True, "contains_answer": True, "abstained": False, "latency_ms": 150},
        ]
        metrics = compute_metrics_by_type(results)

        assert "current_fact" in metrics
        assert "historical_fact" in metrics
        assert metrics["current_fact"]["count"] == 2
        assert metrics["historical_fact"]["count"] == 1
        assert metrics["current_fact"]["overall_accuracy"] == 0.5
        assert metrics["historical_fact"]["overall_accuracy"] == 1.0

    def test_compute_by_type_handles_unknown(self):
        """Test handles unknown question type."""
        results = [
            {"question_type": "unknown", "is_correct": True, "exact_match": True, "contains_answer": True, "abstained": False, "latency_ms": 100},
        ]
        metrics = compute_metrics_by_type(results)

        assert "unknown" in metrics


class TestGenerateComparisonTable:
    """Tests for generate_comparison_table function."""

    def test_generate_basic_table(self):
        """Test basic table generation."""
        all_results = {
            "systems": ["system_a", "system_b"],
            "datasets": ["dataset_1"],
            "results": {
                "dataset_1": {
                    "system_a": [
                        {"question_id": "q1", "is_correct": True, "exact_match": True, "contains_answer": True, "abstained": False, "latency_ms": 100, "question_type": "current_fact"},
                    ],
                    "system_b": [
                        {"question_id": "q1", "is_correct": False, "exact_match": False, "contains_answer": False, "abstained": False, "latency_ms": 200, "question_type": "current_fact"},
                    ],
                }
            }
        }

        # Mock dataset loaders to avoid downloading
        with pytest.MonkeyPatch().context() as mp:
            class MockDataset:
                def load(self):
                    return [{"question_id": "q1", "question_type": "current_fact"}]
            mp.setattr("apps.api.eval.datasets.longmemeval.LongMemEvalDataset", MockDataset)
            mp.setattr("apps.api.eval.datasets.longmemeval_v2.LongMemEvalV2Dataset", MockDataset)
            mp.setattr("apps.api.eval.datasets.beam.BEAMDataset", MockDataset)

            table = generate_comparison_table(all_results)

        assert "dataset_1" in table
        assert "system_a" in table
        assert "system_b" in table
        assert "current_fact" in table
        assert "100.0%" in table  # system_a accuracy
        assert "0.0%" in table    # system_b accuracy


class TestScoreBenchmarkResults:
    """Tests for score_benchmark_results function."""

    def test_score_benchmark_results_file(self, tmp_path):
        """Test scoring benchmark results from file."""
        import json

        results_file = tmp_path / "benchmark_results.json"
        results_data = {
            "systems": ["system_a"],
            "datasets": ["dataset_1"],
            "results": {
                "dataset_1": {
                    "system_a": [
                        {"question_id": "q1", "predicted": "Alex lives in Dhaka", "ground_truth": "Dhaka", "abstained": False, "latency_ms": 100},
                    ]
                }
            }
        }
        results_file.write_text(json.dumps(results_data))

        output_file = tmp_path / "report.md"

        with pytest.MonkeyPatch().context() as mp:
            class MockDataset:
                def load(self):
                    return [{"question_id": "q1", "question_type": "current_fact"}]
            mp.setattr("apps.api.eval.datasets.longmemeval.LongMemEvalDataset", MockDataset)
            mp.setattr("apps.api.eval.datasets.longmemeval_v2.LongMemEvalV2Dataset", MockDataset)
            mp.setattr("apps.api.eval.datasets.beam.BEAMDataset", MockDataset)

            scored = score_benchmark_results(str(results_file), str(output_file))

        assert "scored_results" in scored
        assert output_file.exists()
        assert output_file.with_suffix(".json").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])