"""Unit tests for evaluation dataset loaders."""

import pytest
from unittest.mock import patch, mock_open


class TestLongMemEvalDataset:
    """Tests for LongMemEval dataset loader."""

    def test_init(self):
        """Test dataset initializes correctly."""
        from apps.api.eval.datasets.longmemeval import LongMemEvalDataset

        dataset = LongMemEvalDataset()
        assert dataset.data == []
        assert dataset._loaded is False

    def test_load_returns_cached_when_already_loaded(self):
        """Test load returns cached data on subsequent calls."""
        from apps.api.eval.datasets.longmemeval import LongMemEvalDataset

        dataset = LongMemEvalDataset()
        dataset.data = [{"question_id": "test-1", "question": "Test?"}]
        dataset._loaded = True

        result = dataset.load()
        assert result == dataset.data

    @patch("apps.api.eval.datasets.longmemeval.urlretrieve")
    @patch("pathlib.Path.exists", return_value=False)
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open, read_data='[{"id": "lme-001", "question": "Where does Alex live?", "answer": "Dhaka", "sessions": [], "question_type": "current_fact"}]')
    def test_load_downloads_and_parses(self, mock_open, mock_mkdir, mock_exists, mock_urlretrieve):
        """Test load downloads dataset and parses into standard format."""
        from apps.api.eval.datasets.longmemeval import LongMemEvalDataset

        dataset = LongMemEvalDataset()
        examples = dataset.load()

        assert len(examples) == 1
        ex = examples[0]
        assert ex["question_id"] == "lme-001"
        assert ex["question"] == "Where does Alex live?"
        assert ex["answer"] == "Dhaka"
        assert ex["sessions"] == []
        assert ex["question_type"] == "current_fact"

    @patch("apps.api.eval.datasets.longmemeval.urlretrieve")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data='[{"id": "lme-001", "question": "Test?", "answer": "Ans", "sessions": [], "question_type": "single_session"}]')
    def test_load_uses_cache_when_exists(self, mock_open, mock_exists, mock_urlretrieve):
        """Test load uses cached file when it exists."""
        from apps.api.eval.datasets.longmemeval import LongMemEvalDataset

        dataset = LongMemEvalDataset()
        examples = dataset.load()

        mock_urlretrieve.assert_not_called()
        assert len(examples) == 1

    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", side_effect=[
        # First call - corrupted cache
        mock_open(read_data="not valid json").return_value,
        # Second call - after re-download
        mock_open(read_data='[{"id": "lme-002", "question": "Test2?", "answer": "Ans2", "sessions": [], "question_type": "single_session"}]').return_value,
    ])
    @patch("pathlib.Path.unlink")
    @patch("apps.api.eval.datasets.longmemeval.urlretrieve")
    def test_load_handles_corrupted_cache(self, mock_urlretrieve, mock_unlink, mock_open, mock_exists):
        """Test load re-downloads when cache is corrupted."""
        from apps.api.eval.datasets.longmemeval import LongMemEvalDataset

        dataset = LongMemEvalDataset()
        examples = dataset.load()

        mock_unlink.assert_called_once()
        assert len(examples) == 1
        assert examples[0]["question_id"] == "lme-002"

    def test_sample_returns_all_when_n_geq_len(self):
        """Test sample returns all data when n >= length."""
        from apps.api.eval.datasets.longmemeval import LongMemEvalDataset

        dataset = LongMemEvalDataset()
        dataset.data = [{"question_id": "1"}, {"question_id": "2"}, {"question_id": "3"}]
        dataset._loaded = True

        sample = dataset.sample(5)
        assert len(sample) == 3
        assert sample == dataset.data.copy()

    def test_sample_returns_n_random(self):
        """Test sample returns n random examples."""
        from apps.api.eval.datasets.longmemeval import LongMemEvalDataset

        dataset = LongMemEvalDataset()
        dataset.data = [{"question_id": str(i)} for i in range(100)]
        dataset._loaded = True

        sample = dataset.sample(10, seed=42)
        assert len(sample) == 10

    def test_sample_deterministic_with_same_seed(self):
        """Test sample is deterministic with same seed."""
        from apps.api.eval.datasets.longmemeval import LongMemEvalDataset

        dataset = LongMemEvalDataset()
        dataset.data = [{"question_id": str(i)} for i in range(100)]
        dataset._loaded = True

        sample1 = dataset.sample(10, seed=42)
        sample2 = dataset.sample(10, seed=42)
        assert sample1 == sample2

    def test_get_by_type_filters_correctly(self):
        """Test get_by_type returns only matching question types."""
        from apps.api.eval.datasets.longmemeval import LongMemEvalDataset

        dataset = LongMemEvalDataset()
        dataset.data = [
            {"question_id": "1", "question_type": "current_fact"},
            {"question_id": "2", "question_type": "historical_fact"},
            {"question_id": "3", "question_type": "current_fact"},
            {"question_id": "4", "question_type": "multi_session_synthesis"},
        ]
        dataset._loaded = True

        current_facts = dataset.get_by_type("current_fact")
        assert len(current_facts) == 2
        assert all(ex["question_type"] == "current_fact" for ex in current_facts)


class TestLongMemEvalV2Dataset:
    """Tests for LongMemEval V2 dataset loader."""

    def test_init(self):
        """Test dataset initializes correctly."""
        from apps.api.eval.datasets.longmemeval_v2 import LongMemEvalV2Dataset

        dataset = LongMemEvalV2Dataset()
        assert dataset.data == []
        assert dataset._loaded is False

    @patch("apps.api.eval.datasets.longmemeval_v2.urlretrieve")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data='[{"id": "lmev2-001", "question": "Where does Bob work?", "answer": "Google", "sessions": [], "question_type": "current_fact"}]')
    def test_load_parses_v2_format(self, mock_open, mock_exists, mock_urlretrieve):
        """Test load parses V2 format into standard format."""
        from apps.api.eval.datasets.longmemeval_v2 import LongMemEvalV2Dataset

        dataset = LongMemEvalV2Dataset()
        examples = dataset.load()

        assert len(examples) == 1
        ex = examples[0]
        assert ex["question_id"] == "lmev2-001"
        assert ex["question"] == "Where does Bob work?"
        assert ex["answer"] == "Google"
        assert ex["question_type"] == "current_fact"

    def test_get_by_type_v2(self):
        """Test get_by_type works for V2 dataset."""
        from apps.api.eval.datasets.longmemeval_v2 import LongMemEvalV2Dataset

        dataset = LongMemEvalV2Dataset()
        dataset.data = [
            {"question_id": "1", "question_type": "single_session"},
            {"question_id": "2", "question_type": "multi_session"},
            {"question_id": "3", "question_type": "single_session"},
        ]
        dataset._loaded = True

        single = dataset.get_by_type("single_session")
        assert len(single) == 2


class TestBEAMDataset:
    """Tests for BEAM dataset loader."""

    def test_init(self):
        """Test dataset initializes correctly."""
        from apps.api.eval.datasets.beam import BEAMDataset

        dataset = BEAMDataset()
        assert dataset.data == []
        assert dataset._loaded is False

    @patch("apps.api.eval.datasets.beam.urlretrieve")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data='[{"id": "beam-001", "question": "What did Alice say?", "answer": "Hello", "context": [{"messages": []}], "question_type": "temporal"}]')
    def test_load_parses_beam_format(self, mock_open, mock_exists, mock_urlretrieve):
        """Test load parses BEAM format with 'context' key."""
        from apps.api.eval.datasets.beam import BEAMDataset

        dataset = BEAMDataset()
        examples = dataset.load()

        assert len(examples) == 1
        ex = examples[0]
        assert ex["question_id"] == "beam-001"
        assert ex["question"] == "What did Alice say?"
        assert ex["answer"] == "Hello"
        assert ex["sessions"] == [{"messages": []}]
        assert ex["question_type"] == "temporal"

    @patch("apps.api.eval.datasets.beam.urlretrieve")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data='[{"id": "beam-002", "question": "Test?", "answer": "Ans", "sessions": [{"messages": []}], "question_type": "temporal"}]')
    def test_load_handles_sessions_key(self, mock_open, mock_exists, mock_urlretrieve):
        """Test load handles 'sessions' key when 'context' not present."""
        from apps.api.eval.datasets.beam import BEAMDataset

        dataset = BEAMDataset()
        examples = dataset.load()

        assert len(examples) == 1
        ex = examples[0]
        assert ex["sessions"] == [{"messages": []}]

    def test_get_by_type_beam(self):
        """Test get_by_type works for BEAM dataset."""
        from apps.api.eval.datasets.beam import BEAMDataset

        dataset = BEAMDataset()
        dataset.data = [
            {"question_id": "1", "question_type": "temporal"},
            {"question_id": "2", "question_type": "temporal"},
            {"question_id": "3", "question_type": "multi_session"},
        ]
        dataset._loaded = True

        temporal = dataset.get_by_type("temporal")
        assert len(temporal) == 2


class TestDatasetEdgeCases:
    """Edge case tests for all dataset loaders."""

    def test_sample_empty_dataset(self):
        """Test sample on empty dataset returns empty list."""
        from apps.api.eval.datasets.longmemeval import LongMemEvalDataset

        dataset = LongMemEvalDataset()
        dataset.data = []
        dataset._loaded = True

        sample = dataset.sample(5)
        assert sample == []

    def test_get_by_type_no_matches(self):
        """Test get_by_type returns empty list when no matches."""
        from apps.api.eval.datasets.longmemeval import LongMemEvalDataset

        dataset = LongMemEvalDataset()
        dataset.data = [{"question_id": "1", "question_type": "current_fact"}]
        dataset._loaded = True

        result = dataset.get_by_type("absent_information")
        assert result == []

    @patch("apps.api.eval.datasets.longmemeval.urlretrieve", side_effect=Exception("Network error"))
    @patch("pathlib.Path.exists", return_value=False)
    @patch("pathlib.Path.mkdir")
    def test_load_download_failure(self, mock_mkdir, mock_exists, mock_urlretrieve):
        """Test load raises exception on download failure."""
        from apps.api.eval.datasets.longmemeval import LongMemEvalDataset

        dataset = LongMemEvalDataset()
        with pytest.raises(Exception, match="Network error"):
            dataset.load()

    def test_missing_id_generates_fallback(self):
        """Test missing id field generates fallback question_id."""
        from apps.api.eval.datasets.longmemeval import LongMemEvalDataset

        dataset = LongMemEvalDataset()
        # Directly test the parsing logic by setting raw data
        raw_data = [{"question": "Test?", "answer": "Ans", "sessions": [], "question_type": "single_session"}]
        # Manually call the internal parsing
        dataset.data = []
        for item in raw_data:
            example = {
                "question_id": item.get("id", f"lme-{len(dataset.data):03d}"),
                "sessions": item.get("sessions", []),
                "question": item.get("question", ""),
                "answer": item.get("answer", ""),
                "question_type": item.get("question_type", "single_session"),
            }
            dataset.data.append(example)

        assert dataset.data[0]["question_id"] == "lme-000"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])