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
        """Set up test fixtures."""
        self.handler = QueryHandler()

    def test_load_query_file_success(self) -> None:
        """Test loading a valid query file."""
        query_data = {
            "keywords": "test",
            "limit": 5,
            "include_prompts": True,
            "include_generations": False,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(query_data, f)
            temp_path = f.name

        try:
            result = self.handler.load_query_file(temp_path)
            assert result == query_data
        finally:
            Path(temp_path).unlink()

    def test_load_query_file_not_found(self) -> None:
        """Test loading a non-existent query file."""
        with pytest.raises(FileNotFoundError):
            self.handler.load_query_file("/nonexistent/file.json")

    def test_load_query_file_invalid_json(self) -> None:
        """Test loading a file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid JSON"):
                self.handler.load_query_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_validate_query_valid(self) -> None:
        """Test validating a valid query."""
        query_data = {
            "keywords": "test",
            "limit": 5,
            "include_prompts": True,
            "include_generations": False,
        }
        # Should not raise any exception
        self.handler.validate_query(query_data)

    def test_validate_query_missing_keywords(self) -> None:
        """Test validating query missing keywords field."""
        query_data = {"limit": 5, "include_prompts": True, "include_generations": False}
        with pytest.raises(ValueError, match="Missing required field: keywords"):
            self.handler.validate_query(query_data)

    def test_validate_query_missing_limit(self) -> None:
        """Test validating query missing limit field."""
        query_data = {
            "keywords": "test",
            "include_prompts": True,
            "include_generations": False,
        }
        with pytest.raises(ValueError, match="Missing required field: limit"):
            self.handler.validate_query(query_data)

    def test_validate_query_invalid_keywords_type(self) -> None:
        """Test validating query with invalid keywords type."""
        query_data = {
            "keywords": 123,
            "limit": 5,
            "include_prompts": True,
            "include_generations": False,
        }
        with pytest.raises(ValueError, match="Keywords must be a string"):
            self.handler.validate_query(query_data)

    def test_validate_query_invalid_limit_type(self) -> None:
        """Test validating query with invalid limit type."""
        query_data = {
            "keywords": "test",
            "limit": "five",
            "include_prompts": True,
            "include_generations": False,
        }
        with pytest.raises(ValueError, match="Limit must be a positive integer"):
            self.handler.validate_query(query_data)

    def test_validate_query_invalid_limit_value(self) -> None:
        """Test validating query with invalid limit value."""
        query_data = {
            "keywords": "test",
            "limit": 0,
            "include_prompts": True,
            "include_generations": False,
        }
        with pytest.raises(ValueError, match="Limit must be a positive integer"):
            self.handler.validate_query(query_data)

    def test_validate_query_adds_defaults(self) -> None:
        """Test that validation adds default values for optional fields."""
        query_data = {"keywords": "test", "limit": 5}
        self.handler.validate_query(query_data)
        assert query_data["include_prompts"] is True
        assert query_data["include_generations"] is False

    @patch("src.query_handler.json.load")
    @patch("builtins.open")
    def test_execute_query_registry_not_found(
        self, mock_open: Any, mock_json_load: Any
    ) -> None:
        """Test execute_query when registry file is not found."""
        mock_open.side_effect = FileNotFoundError("Registry not found")

        query_data = {
            "keywords": "test",
            "limit": 5,
            "include_prompts": True,
            "include_generations": False,
        }

        result = self.handler.execute_query(query_data)

        assert result["status"] == "error"
        assert result["error"] == "Registry file not found"

    @patch("src.query_handler.json.load")
    @patch("src.query_handler.open")
    def test_execute_query_success(self, mock_open: Any, mock_json_load: Any) -> None:
        """Test successful query execution."""
        # Mock registry data
        registry_data = {"test_tool": ["/test/path"]}
        mock_json_load.return_value = registry_data

        # Mock conversation data
        mock_conversation = {
            "prompts": [{"text": "test prompt"}],
            "generations": [],
            "history_entries": [],
            "database_path": "/test/path/test.db",
            "error": None,
        }

        mock_formatted_conversation = {
            "source": "test.db",
            "status": "success",
            "total_conversations": 1,
            "conversations": [
                {
                    "id": "prompt_0",
                    "summary": "test prompt",
                    "type": "prompt",
                    "relevance": 0.5,
                }
            ],
        }

        # Mock the database manager methods
        with patch.object(
            self.handler.db_manager, "process_database_files"
        ) as mock_process:
            with patch.object(
                self.handler.db_manager, "format_conversation_entry"
            ) as mock_format:
                mock_process.return_value = (
                    [mock_conversation],
                    ["/test/path/test.db"],
                    1,
                    {"test.db": 1},
                )
                mock_format.return_value = mock_formatted_conversation

                query_data = {
                    "keywords": "test",
                    "limit": 5,
                    "include_prompts": True,
                    "include_generations": False,
                }

                result = self.handler.execute_query(query_data)

                assert result["status"] == "success"
                assert "query" in result
                assert "results" in result
                assert result["query"]["keywords"] == "test"
                assert result["query"]["limit"] == 5
                assert result["results"]["total_conversations"] == 1
                assert len(result["results"]["conversations"]) == 1

    def test_process_query_file_success(self) -> None:
        """Test processing a complete query file successfully."""
        query_data = {
            "keywords": "test",
            "limit": 5,
            "include_prompts": True,
            "include_generations": False,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(query_data, f)
            temp_path = f.name

        try:
            with patch.object(self.handler, "execute_query") as mock_execute:
                mock_execute.return_value = {"status": "success", "results": []}

                result = self.handler.process_query_file(temp_path)

                assert result["status"] == "success"
                mock_execute.assert_called_once_with(query_data)
        finally:
            Path(temp_path).unlink()

    def test_process_query_file_invalid_json(self) -> None:
        """Test processing a query file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json")
            temp_path = f.name

        try:
            result = self.handler.process_query_file(temp_path)

            assert result["status"] == "error"
            assert "Query processing error" in result["error"]
        finally:
            Path(temp_path).unlink()

    def test_process_query_file_validation_error(self) -> None:
        """Test processing a query file with validation errors."""
        query_data = {
            "keywords": "test"
            # Missing required 'limit' field
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(query_data, f)
            temp_path = f.name

        try:
            result = self.handler.process_query_file(temp_path)

            assert result["status"] == "error"
            assert "Query processing error" in result["error"]
        finally:
            Path(temp_path).unlink()
