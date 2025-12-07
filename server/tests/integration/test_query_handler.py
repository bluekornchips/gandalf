"""
Integration tests for query handler.
"""

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.query_handler import QueryHandler


class TestQueryHandler:
    """Test suite for QueryHandler class."""

    def setup_method(self) -> None:
        self.handler = QueryHandler()

    def test_load_query_file_success(self) -> None:
        query_data = {"search": "test", "limit": 5}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(query_data, f)
            temp_path = f.name
        try:
            result = self.handler.load_query_file(temp_path)
            assert result == query_data
        finally:
            Path(temp_path).unlink()

    def test_load_query_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            self.handler.load_query_file("/nonexistent/file.json")

    def test_load_query_file_invalid_json(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json")
            temp_path = f.name
        try:
            with pytest.raises(ValueError, match="Invalid JSON"):
                self.handler.load_query_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_validate_query_valid(self) -> None:
        query_data = {"search": "test", "limit": 5}
        self.handler.validate_query(query_data)

    def test_validate_query_missing_search(self) -> None:
        with pytest.raises(ValueError, match="Missing required field: search"):
            self.handler.validate_query({"limit": 5})

    def test_validate_query_missing_limit(self) -> None:
        with pytest.raises(ValueError, match="Missing required field: limit"):
            self.handler.validate_query({"search": "test"})

    def test_validate_query_invalid_search_type(self) -> None:
        with pytest.raises(ValueError, match="Search must be a string"):
            self.handler.validate_query({"search": 123, "limit": 5})

    def test_validate_query_invalid_limit(self) -> None:
        with pytest.raises(ValueError, match="Limit must be a positive integer"):
            self.handler.validate_query({"search": "test", "limit": 0})

    def test_validate_query_adds_defaults(self) -> None:
        query_data = {"search": "test", "limit": 5}
        self.handler.validate_query(query_data)
        assert query_data["include_prompts"] is True
        assert query_data["include_generations"] is False
        assert query_data["count_matches"] is False
        assert query_data["regex"] is False

    def test_find_matches_substring(self) -> None:
        matches = self.handler.find_matches("hello world hello", "hello")
        assert len(matches) == 2
        assert all(m == "hello" for m in matches)

    def test_find_matches_case_insensitive(self) -> None:
        matches = self.handler.find_matches("Hello HELLO hello", "hello")
        assert len(matches) == 3

    def test_find_matches_regex(self) -> None:
        matches = self.handler.find_matches("test123 test456", r"test\d+", regex=True)
        assert len(matches) == 2
        assert "test123" in matches
        assert "test456" in matches

    def test_find_matches_empty(self) -> None:
        assert self.handler.find_matches("hello", "") == []
        assert self.handler.find_matches("", "hello") == []

    @patch("src.query_handler.open")
    def test_execute_query_registry_not_found(self, mock_open: Any) -> None:
        mock_open.side_effect = FileNotFoundError()
        result = self.handler.execute_query({"search": "test", "limit": 5})
        assert result["status"] == "error"
        assert result["error"] == "Registry file not found"

    @patch("src.query_handler.json.load")
    @patch("src.query_handler.open")
    def test_execute_query_success(self, mock_open: Any, mock_json_load: Any) -> None:
        mock_json_load.return_value = {"test_tool": ["/test/path"]}

        mock_formatted = {
            "status": "success",
            "conversations": [
                {"summary": "test prompt", "type": "prompt", "relevance": 0.5}
            ],
        }

        with patch.object(
            self.handler.db_manager, "process_database_files"
        ) as mock_process:
            with patch.object(
                self.handler.db_manager, "format_conversation_entry"
            ) as mock_format:
                mock_process.return_value = ([{}], ["/test/path"], 1, {"test.db": 1})
                mock_format.return_value = mock_formatted

                result = self.handler.execute_query({"search": "test", "limit": 5})

                assert result["status"] == "success"
                assert result["query"]["search"] == "test"
                assert result["results"]["total_found"] == 1

    def test_process_query_file_success(self) -> None:
        query_data = {"search": "test", "limit": 5}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(query_data, f)
            temp_path = f.name
        try:
            with patch.object(self.handler, "execute_query") as mock_execute:
                mock_execute.return_value = {"status": "success"}
                result = self.handler.process_query_file(temp_path)
                assert result["status"] == "success"
        finally:
            Path(temp_path).unlink()

    def test_process_query_file_error(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid")
            temp_path = f.name
        try:
            result = self.handler.process_query_file(temp_path)
            assert result["status"] == "error"
        finally:
            Path(temp_path).unlink()
