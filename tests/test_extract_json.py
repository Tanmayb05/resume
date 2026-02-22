"""Tests for extract_json() utility in src/llm/utils.py."""
import pytest

from src.llm.utils import extract_json


class TestExtractJsonFences:
    """Tests for code fence stripping variants."""

    def test_json_fence(self):
        """Parses JSON wrapped in ```json ... ``` fences."""
        text = '```json\n{"key": "value"}\n```'
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_bare_fence(self):
        """Parses JSON wrapped in bare ``` ... ``` fences."""
        text = '```\n{"status": "ok"}\n```'
        result = extract_json(text)
        assert result == {"status": "ok"}

    def test_no_fence_direct_json(self):
        """Parses direct JSON with no fences."""
        text = '{"result": 42}'
        result = extract_json(text)
        assert result == {"result": 42}

    def test_surrounding_text_with_fence(self):
        """Parses JSON from text with surrounding prose and a fence."""
        text = 'Here is the result:\n```json\n{"score": 0.9}\n```\nDone.'
        result = extract_json(text)
        assert result == {"score": 0.9}


class TestExtractJsonRepair:
    """Tests for malformed/incomplete JSON repair."""

    def test_malformed_json_missing_brace(self):
        """Repairs and parses incomplete JSON missing closing brace."""
        text = '{"key": "value"'
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_malformed_json_in_fence(self):
        """Repairs and parses malformed JSON inside a fence."""
        text = '```json\n{"a": 1, "b": 2'
        result = extract_json(text)
        assert result == {"a": 1, "b": 2}


class TestExtractJsonErrors:
    """Tests for ValueError on completely unextractable input."""

    def test_completely_invalid_text(self):
        """Raises ValueError with input text in message for non-JSON input."""
        text = "This is just plain text with no JSON"
        with pytest.raises(ValueError) as exc_info:
            extract_json(text)
        error_message = str(exc_info.value)
        assert "Could not extract valid JSON" in error_message
        # The raw input text (or first 300 chars) must be in the error message
        assert "This is just plain text" in error_message

    def test_empty_string(self):
        """Raises ValueError for empty string input."""
        with pytest.raises(ValueError):
            extract_json("")
