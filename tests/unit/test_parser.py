"""Unit tests for the question parser module."""

import json
import pytest
from unittest.mock import MagicMock


class TestParser:
    """Tests for question parsing."""

    def test_parse_question_current_fact(self, mock_groq_parser):
        """Test parsing 'Where does Alex live?' as current_fact."""
        from apps.api.pipeline.retrieval.parser import parse_question

        result = parse_question(mock_groq_parser, "Where does Alex live?")

        assert result["entity_name"] == "Alex"
        assert result["question_type"] == "current_fact"
        assert "live" in result["keywords"] or "location" in result["keywords"]
        assert result["original_question"] == "Where does Alex live?"

    def test_parse_question_historical_fact(self, mock_groq_parser):
        """Test parsing 'Where did Alex live before?' as historical_fact."""
        from apps.api.pipeline.retrieval.parser import parse_question

        # Override mock for historical question
        mock_groq_parser.chat.completions.create.return_value.choices[0].message.content = json.dumps({
            "entity_name": "Alex",
            "question_type": "historical_fact",
            "keywords": ["live", "before", "previous"]
        })

        result = parse_question(mock_groq_parser, "Where did Alex live before?")

        assert result["entity_name"] == "Alex"
        assert result["question_type"] == "historical_fact"
        assert "before" in result["keywords"] or "previous" in result["keywords"]

    def test_parse_question_multi_session_synthesis(self, mock_groq_parser):
        """Test parsing 'What jobs has Alex had?' as multi_session_synthesis."""
        from apps.api.pipeline.retrieval.parser import parse_question

        mock_groq_parser.chat.completions.create.return_value.choices[0].message.content = json.dumps({
            "entity_name": "Alex",
            "question_type": "multi_session_synthesis",
            "keywords": ["jobs", "work", "career", "had"]
        })

        result = parse_question(mock_groq_parser, "What jobs has Alex had?")

        assert result["entity_name"] == "Alex"
        assert result["question_type"] == "multi_session_synthesis"
        assert "jobs" in result["keywords"] or "work" in result["keywords"]

    def test_parse_question_absent_information(self, mock_groq_parser):
        """Test parsing 'What is Alex's favorite color?' as absent_information."""
        from apps.api.pipeline.retrieval.parser import parse_question

        mock_groq_parser.chat.completions.create.return_value.choices[0].message.content = json.dumps({
            "entity_name": "Alex",
            "question_type": "absent_information",
            "keywords": ["favorite", "color"]
        })

        result = parse_question(mock_groq_parser, "What is Alex's favorite color?")

        assert result["entity_name"] == "Alex"
        assert result["question_type"] == "absent_information"

    def test_parse_question_missing_entity_name(self, groq_mock):
        """Test parsing handles missing entity_name in response."""
        from apps.api.pipeline.retrieval.parser import parse_question

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "question_type": "current_fact",
            "keywords": ["live"]
        })
        groq_mock.chat.completions.create.return_value = mock_response

        result = parse_question(groq_mock, "Where does he live?")

        assert result["entity_name"] is None
        assert result["question_type"] == "current_fact"

    def test_parse_question_missing_question_type(self, groq_mock):
        """Test parsing handles missing question_type in response."""
        from apps.api.pipeline.retrieval.parser import parse_question

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "entity_name": "Alex",
            "keywords": ["live"]
        })
        groq_mock.chat.completions.create.return_value = mock_response

        result = parse_question(groq_mock, "Where does Alex live?")

        assert result["entity_name"] == "Alex"
        assert result["question_type"] == "absent_information"

    def test_parse_question_missing_keywords(self, groq_mock):
        """Test parsing handles missing keywords in response."""
        from apps.api.pipeline.retrieval.parser import parse_question

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "entity_name": "Alex",
            "question_type": "current_fact"
        })
        groq_mock.chat.completions.create.return_value = mock_response

        result = parse_question(groq_mock, "Where does Alex live?")

        assert result["entity_name"] == "Alex"
        assert result["question_type"] == "current_fact"
        assert result["keywords"] == []

    def test_parse_question_json_decode_error(self, groq_mock):
        """Test parsing handles JSON decode error gracefully."""
        from apps.api.pipeline.retrieval.parser import parse_question

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "not valid json"
        groq_mock.chat.completions.create.return_value = mock_response

        result = parse_question(groq_mock, "Where does Alex live?")

        assert result["entity_name"] is None
        assert result["question_type"] == "absent_information"
        assert result["keywords"] == []

    def test_parse_question_empty_response(self, groq_mock):
        """Test parsing handles empty response gracefully with a real fallback entity match."""
        from apps.api.pipeline.retrieval.parser import parse_question

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        groq_mock.chat.completions.create.return_value = mock_response

        result = parse_question(groq_mock, "Where does Alex live?")

        assert result["entity_name"] == "Alex"
        assert result["question_type"] == "current_fact"
        assert any("live" in kw.lower() or "location" in kw.lower() for kw in result["keywords"])

    def test_parse_question_api_exception(self, groq_mock):
        """Test parsing handles API exception gracefully."""
        from apps.api.pipeline.retrieval.parser import parse_question

        groq_mock.chat.completions.create.side_effect = Exception("API error")

        result = parse_question(groq_mock, "Where does Alex live?")

        assert result["entity_name"] is None
        assert result["question_type"] == "absent_information"
        assert result["keywords"] == []

    def test_parse_question_original_question_preserved(self, mock_groq_parser):
        """Test that original_question is preserved in result."""
        from apps.api.pipeline.retrieval.parser import parse_question

        result = parse_question(mock_groq_parser, "Where does Alex live?")

        assert "original_question" in result
        assert result["original_question"] == "Where does Alex live?"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])