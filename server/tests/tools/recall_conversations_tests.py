"""Test suite for recall_conversations tool implementation."""

import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch, mock_open

import pytest

from src.tools.recall_conversations_tool import RecallConversationsTool
from src.config.constants import (
    SUPPORTED_DB_FILES,
    GANDALF_REGISTRY_FILE,
    RECALL_CONVERSATIONS_QUERIES,
    IGNORED_KEYWORDS,
    MAX_CONVERSATIONS,
    MAX_KEYWORDS,
    INCLUDE_PROMPTS_DEFAULT,
    INCLUDE_GENERATIONS_DEFAULT,
)


class TestRecallConversationsTool:
    """Test suite for RecallConversationsTool class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.tool = RecallConversationsTool()

    def test_constants_import(self) -> None:
        """Test that required constants are properly imported."""
        assert SUPPORTED_DB_FILES is not None
        assert GANDALF_REGISTRY_FILE is not None
        assert RECALL_CONVERSATIONS_QUERIES is not None
        assert IGNORED_KEYWORDS is not None
        assert MAX_CONVERSATIONS is not None
        assert MAX_KEYWORDS is not None
        assert INCLUDE_PROMPTS_DEFAULT is not None
        assert INCLUDE_GENERATIONS_DEFAULT is not None

    def test_recall_conversations_queries_structure(self) -> None:
        """Test that RECALL_CONVERSATIONS_QUERIES has expected structure."""
        assert "PROMPTS_KEY" in RECALL_CONVERSATIONS_QUERIES
        assert "GENERATIONS_KEY" in RECALL_CONVERSATIONS_QUERIES
        assert "HISTORY_KEY" in RECALL_CONVERSATIONS_QUERIES

    def test_ignored_keywords_structure(self) -> None:
        """Test that IGNORED_KEYWORDS contains expected categories."""
        assert "the" in IGNORED_KEYWORDS  # Articles
        assert "in" in IGNORED_KEYWORDS  # Prepositions
        assert "and" in IGNORED_KEYWORDS  # Conjunctions
        assert "i" in IGNORED_KEYWORDS  # Pronouns
        assert "is" in IGNORED_KEYWORDS  # Common verbs
        assert "this" in IGNORED_KEYWORDS  # Demonstratives
        assert "what" in IGNORED_KEYWORDS  # Interrogatives
        assert "all" in IGNORED_KEYWORDS  # Quantifiers

    def test_tool_name(self) -> None:
        """Test tool name property."""
        assert self.tool.name == "recall_conversations"

    def test_tool_description(self) -> None:
        """Test tool description property."""
        assert (
            self.tool.description
            == "Extract and analyze conversation history from database files in the Gandalf registry"
        )

    def test_input_schema(self) -> None:
        """Test tool input schema structure."""
        schema = self.tool.input_schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "limit" in schema["properties"]
        assert "include_prompts" in schema["properties"]
        assert "include_generations" in schema["properties"]
        assert "keywords" in schema["properties"]

    def test_input_schema_uses_constants(self) -> None:
        """Test that input schema uses the constants."""
        schema = self.tool.input_schema
        assert schema["properties"]["limit"]["default"] == MAX_CONVERSATIONS
        assert (
            schema["properties"]["include_prompts"]["default"]
            == INCLUDE_PROMPTS_DEFAULT
        )
        assert (
            schema["properties"]["include_generations"]["default"]
            == INCLUDE_GENERATIONS_DEFAULT
        )

    def test_build_search_conditions_empty_keywords(self) -> None:
        """Test _build_search_conditions with empty keywords."""
        conditions, params = self.tool._build_search_conditions("")

        assert conditions == []
        assert params == []

    def test_build_search_conditions_single_keyword(self) -> None:
        """Test _build_search_conditions with single keyword."""
        conditions, params = self.tool._build_search_conditions("python")

        assert len(conditions) == 1
        assert conditions[0] == "value LIKE ?"
        assert len(params) == 1
        assert params[0] == "%python%"

    def test_build_search_conditions_multiple_keywords(self) -> None:
        """Test _build_search_conditions with multiple keywords."""
        conditions, params = self.tool._build_search_conditions("python programming")

        assert len(conditions) == 2
        assert all(condition == "value LIKE ?" for condition in conditions)
        assert len(params) == 2
        assert "%python%" in params
        assert "%programming%" in params

    def test_build_search_conditions_ignored_keywords(self) -> None:
        """Test _build_search_conditions filters out ignored keywords."""
        conditions, params = self.tool._build_search_conditions(
            "the python and programming"
        )

        # Should filter out "the" and "and"
        assert len(conditions) == 2
        assert "%python%" in params
        assert "%programming%" in params
        assert "%the%" not in params
        assert "%and%" not in params

    def test_build_search_conditions_only_ignored_keywords(self) -> None:
        """Test _build_search_conditions with only ignored keywords."""
        conditions, params = self.tool._build_search_conditions("the and or")

        # Should use original keywords when no meaningful words remain
        assert len(conditions) == 3
        assert "%the%" in params
        assert "%and%" in params
        assert "%or%" in params

    def test_build_search_conditions_max_keywords_limit(self) -> None:
        """Test _build_search_conditions respects MAX_KEYWORDS limit."""
        long_keywords = " ".join([f"word{i}" for i in range(MAX_KEYWORDS + 5)])
        conditions, params = self.tool._build_search_conditions(long_keywords)

        # Should limit to MAX_KEYWORDS
        assert len(conditions) <= MAX_KEYWORDS
        assert len(params) <= MAX_KEYWORDS

    def test_extract_conversation_data_without_keywords(self) -> None:
        """Test _extract_conversation_data without keywords filtering."""
        with tempfile.NamedTemporaryFile(suffix=".db") as temp_db:
            # Create test database
            conn = sqlite3.connect(temp_db.name)
            cursor = conn.cursor()

            # Create test table and data
            cursor.execute("CREATE TABLE ItemTable (key TEXT, value TEXT)")
            cursor.execute(
                "INSERT INTO ItemTable VALUES (?, ?)",
                (RECALL_CONVERSATIONS_QUERIES["PROMPTS_KEY"], "[]"),
            )
            conn.commit()
            conn.close()

            result = self.tool._extract_conversation_data(temp_db.name, 50)

            assert "prompts" in result
            assert "generations" in result
            assert "history_entries" in result
            assert "database_path" in result
            assert result["database_path"] == temp_db.name

    def test_extract_conversation_data_with_keywords(self) -> None:
        """Test _extract_conversation_data with keywords filtering."""
        with tempfile.NamedTemporaryFile(suffix=".db") as temp_db:
            # Create test database
            conn = sqlite3.connect(temp_db.name)
            cursor = conn.cursor()

            # Create test table and data with searchable content
            cursor.execute("CREATE TABLE ItemTable (key TEXT, value TEXT)")
            test_prompts = '[{"text": "python programming tutorial"}]'
            cursor.execute(
                "INSERT INTO ItemTable VALUES (?, ?)",
                (RECALL_CONVERSATIONS_QUERIES["PROMPTS_KEY"], test_prompts),
            )
            conn.commit()
            conn.close()

            result = self.tool._extract_conversation_data(temp_db.name, 50, "python")

            assert "prompts" in result
            assert "database_path" in result

    def test_extract_conversation_data_database_error(self) -> None:
        """Test _extract_conversation_data handles database errors."""
        # Test with non-existent database
        result = self.tool._extract_conversation_data("/nonexistent/path.db", 50)

        assert "error" in result
        assert result["error"] is not None

    def test_process_database_files_empty_registry(self) -> None:
        """Test _process_database_files with empty registry."""
        registry_data: Dict[str, Any] = {}
        conversations, paths, total_files, file_counts = (
            self.tool._process_database_files(registry_data, 50)
        )

        assert conversations == []
        assert paths == []
        assert total_files == 0
        assert file_counts == {}

    def test_process_database_files_with_keywords(self) -> None:
        """Test _process_database_files with keywords parameter."""
        registry_data: Dict[str, Any] = {}
        conversations, paths, total_files, file_counts = (
            self.tool._process_database_files(registry_data, 50, "python")
        )

        # Should handle keywords parameter gracefully even with empty registry
        assert conversations == []
        assert paths == []
        assert total_files == 0
        assert file_counts == {}

    def test_process_database_files_nonexistent_paths(self) -> None:
        """Test _process_database_files with nonexistent paths."""
        registry_data = {
            "cursor": ["/nonexistent/path"],
            "claude": ["/another/nonexistent/path"],
        }

        with patch("os.path.exists", return_value=False):
            conversations, paths, total_files, file_counts = (
                self.tool._process_database_files(registry_data, 50)
            )

            assert conversations == []
            assert paths == []
            assert total_files == 0
            assert file_counts == {}

    def test_format_conversation_entry_structure(self) -> None:
        """Test that _format_conversation_entry returns expected structure."""
        # Test with error data
        error_data = {
            "database_path": "/test/path.db",
            "error": "Test error",
            "prompts": [],
            "generations": [],
            "history_entries": [],
        }

        result = self.tool._format_conversation_entry(error_data, True, True)

        assert "database_path" in result
        assert "status" in result
        assert "counts" in result
        assert "error" in result
        assert result["status"] == "error"
        assert result["error"] == "Test error"

    def test_format_conversation_entry_success(self) -> None:
        """Test that _format_conversation_entry handles success case."""
        # Test with successful data
        success_data = {
            "database_path": "/test/path.db",
            "prompts": [{"text": "test prompt", "commandType": 1}],
            "generations": [{"textDescription": "test generation", "type": "response"}],
            "history_entries": [{"entry": "test"}],
        }

        result = self.tool._format_conversation_entry(success_data, True, True)

        assert result["status"] == "success"
        assert result["counts"]["prompts"] == 1
        assert result["counts"]["generations"] == 1
        assert result["counts"]["history_entries"] == 1
        assert "sample_prompts" in result
        assert "sample_generations" in result

    @pytest.mark.asyncio
    async def test_execute_registry_file_not_found(self) -> None:
        """Test execute method when registry file is not found."""
        with patch("os.path.exists", return_value=False):
            result = await self.tool.execute(None)

            assert len(result) == 1
            assert result[0].type == "text"
            assert "Error: Registry file not found" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_invalid_json(self) -> None:
        """Test execute method with invalid JSON in registry file."""
        invalid_json = "invalid json content"

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=invalid_json)),
        ):
            result = await self.tool.execute(None)

            assert len(result) == 1
            assert result[0].type == "text"
            assert "Error reading registry file" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_empty_registry(self) -> None:
        """Test execute method with empty registry."""
        empty_registry = "{}"

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=empty_registry)),
        ):
            result = await self.tool.execute(None)

            assert len(result) == 1
            assert result[0].type == "text"

            data = json.loads(result[0].text)
            assert data["metadata"]["total_db_files_found"] == 0
            assert data["metadata"]["db_file_counts"] == {}
            assert data["found_paths"] == []
            assert data["metadata"]["supported_db_files"] == SUPPORTED_DB_FILES
            assert data["metadata"]["registry_file"] == GANDALF_REGISTRY_FILE

    @pytest.mark.asyncio
    async def test_execute_with_keywords_parameter(self) -> None:
        """Test execute method with keywords parameter."""
        registry_data: Dict[str, Any] = {"cursor": [], "claude": []}

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=json.dumps(registry_data))),
        ):
            result = await self.tool.execute({"keywords": "python programming"})

            assert len(result) == 1
            assert result[0].type == "text"

            data = json.loads(result[0].text)
            assert data["metadata"]["search_keywords"] == "python programming"
            assert data["metadata"]["filtered_by_keywords"] is True

    @pytest.mark.asyncio
    async def test_execute_without_keywords_parameter(self) -> None:
        """Test execute method without keywords parameter."""
        registry_data: Dict[str, Any] = {"cursor": [], "claude": []}

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=json.dumps(registry_data))),
        ):
            result = await self.tool.execute({})

            assert len(result) == 1
            assert result[0].type == "text"

            data = json.loads(result[0].text)
            assert data["metadata"]["search_keywords"] is None
            assert data["metadata"]["filtered_by_keywords"] is False

    @pytest.mark.asyncio
    async def test_execute_with_arguments(self) -> None:
        """Test execute method with various arguments."""
        registry_data: Dict[str, Any] = {"cursor": [], "claude": []}
        test_args = {
            "keywords": "test",
            "limit": 25,
            "include_prompts": False,
            "include_generations": True,
        }

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=json.dumps(registry_data))),
        ):
            result = await self.tool.execute(test_args)

            assert len(result) == 1
            assert result[0].type == "text"

            data = json.loads(result[0].text)
            assert data["metadata"]["search_keywords"] == "test"
            assert data["metadata"]["filtered_by_keywords"] is True

    @pytest.mark.asyncio
    async def test_execute_io_error(self) -> None:
        """Test execute method handles IO errors gracefully."""
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", side_effect=IOError("Permission denied")),
        ):
            result = await self.tool.execute(None)

            assert len(result) == 1
            assert result[0].type == "text"
            assert "Error reading registry file" in result[0].text
            assert "Permission denied" in result[0].text

    def test_sql_injection_protection(self) -> None:
        """Test that SQL queries are protected against injection attacks."""
        # Test with potentially malicious keywords
        malicious_keywords = "'; DROP TABLE ItemTable; --"
        conditions, params = self.tool._build_search_conditions(malicious_keywords)

        # Should be safely parameterized
        assert all(condition == "value LIKE ?" for condition in conditions)
        assert all(
            isinstance(param, str) and param.startswith("%") and param.endswith("%")
            for param in params
        )

    @pytest.mark.asyncio
    async def test_sql_filtering_integration(self) -> None:
        """Test integration of SQL-based filtering."""
        # Create a temporary database with test data
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            conn = sqlite3.connect(temp_db.name)
            cursor = conn.cursor()

            # Create test table and data
            cursor.execute("CREATE TABLE ItemTable (key TEXT, value TEXT)")

            # Insert test data with searchable content
            test_prompts = json.dumps(
                [
                    {"text": "How to learn python programming?"},
                    {"text": "JavaScript frameworks comparison"},
                    {"text": "Database design patterns"},
                ]
            )

            cursor.execute(
                "INSERT INTO ItemTable VALUES (?, ?)",
                (RECALL_CONVERSATIONS_QUERIES["PROMPTS_KEY"], test_prompts),
            )
            conn.commit()
            conn.close()

            # Test extraction with keywords
            result = self.tool._extract_conversation_data(temp_db.name, 50, "python")

            # Cleanup
            Path(temp_db.name).unlink()

            # Should have returned data (exact matching depends on SQLite LIKE behavior)
            assert "prompts" in result
            assert "database_path" in result

    def test_case_insensitive_search(self) -> None:
        """Test that search conditions handle case insensitivity."""
        conditions, params = self.tool._build_search_conditions("PYTHON Programming")

        # Keywords should be converted to lowercase
        assert "%python%" in params
        assert "%programming%" in params
        assert "%PYTHON%" not in params
        assert "%Programming%" not in params
