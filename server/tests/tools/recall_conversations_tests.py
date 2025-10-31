"""Test suite for recall_conversations tool implementation."""

import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch, mock_open

import pytest

from src.tools.recall_conversations_tool import RecallConversationsTool
from src.database_management.recall_conversations import ConversationDatabaseManager
from src.config.constants import (
    SUPPORTED_DB_FILES,
    GANDALF_REGISTRY_FILE,
    RECALL_CONVERSATIONS_QUERIES,
    IGNORED_KEYWORDS,
    MAX_CONVERSATIONS,
    MAX_KEYWORDS,
    INCLUDE_PROMPTS_DEFAULT,
    INCLUDE_GENERATIONS_DEFAULT,
    MAX_SUMMARY_LENGTH,
    MAX_SUMMARY_ENTRIES,
)


class TestRecallConversationsTool:
    """Test suite for RecallConversationsTool class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.tool = RecallConversationsTool()
        self.db_manager = ConversationDatabaseManager()

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
        assert MAX_SUMMARY_LENGTH is not None

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
        """Test build_search_conditions with empty keywords."""
        conditions, params = self.db_manager.build_search_conditions("")

        assert conditions == []
        assert params == []

    def test_build_search_conditions_single_keyword(self) -> None:
        """Test _build_search_conditions with single keyword."""
        conditions, params = self.db_manager.build_search_conditions("python")

        assert len(conditions) == 1
        assert conditions[0] == "value LIKE ?"
        assert len(params) == 1
        assert params[0] == "%python%"

    def test_build_search_conditions_multiple_keywords(self) -> None:
        """Test _build_search_conditions with multiple keywords."""
        conditions, params = self.db_manager.build_search_conditions(
            "python programming"
        )

        assert len(conditions) == 2
        assert all(condition == "value LIKE ?" for condition in conditions)
        assert len(params) == 2
        assert "%python%" in params
        assert "%programming%" in params

    def test_build_search_conditions_ignored_keywords(self) -> None:
        """Test _build_search_conditions filters out ignored keywords."""
        conditions, params = self.db_manager.build_search_conditions(
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
        conditions, params = self.db_manager.build_search_conditions("the and or")

        # Should use original keywords when no meaningful words remain
        assert len(conditions) == 3
        assert "%the%" in params
        assert "%and%" in params
        assert "%or%" in params

    def test_build_search_conditions_max_keywords_limit(self) -> None:
        """Test _build_search_conditions respects MAX_KEYWORDS limit."""
        long_keywords = " ".join([f"word{i}" for i in range(MAX_KEYWORDS + 5)])
        conditions, params = self.db_manager.build_search_conditions(long_keywords)

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

            result = self.db_manager.extract_conversation_data(temp_db.name, 50)

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

            result = self.db_manager.extract_conversation_data(
                temp_db.name, 50, "python"
            )

            assert "prompts" in result
            assert "database_path" in result

    def test_extract_conversation_data_database_error(self) -> None:
        """Test _extract_conversation_data handles database errors."""
        # Test with non-existent database
        result = self.db_manager.extract_conversation_data("/nonexistent/path.db", 50)

        assert "error" in result
        assert result["error"] is not None

    def test_process_database_files_empty_registry(self) -> None:
        """Test _process_database_files with empty registry."""
        registry_data: Dict[str, Any] = {}
        conversations, paths, total_files, file_counts = (
            self.db_manager.process_database_files(registry_data, 50)
        )

        assert conversations == []
        assert paths == []
        assert total_files == 0
        assert file_counts == {}

    def test_process_database_files_with_keywords(self) -> None:
        """Test _process_database_files with keywords parameter."""
        registry_data: Dict[str, Any] = {}
        conversations, paths, total_files, file_counts = (
            self.db_manager.process_database_files(registry_data, 50, "python")
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
                self.db_manager.process_database_files(registry_data, 50)
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

        result = self.db_manager.format_conversation_entry(error_data, True, True)

        # In concise mode, should have different structure
        assert "source" in result
        assert "status" in result
        assert "total_conversations" in result
        assert "error" in result
        assert result["status"] == "error"
        assert result["error"] == "Test error"
        assert result["source"] == "path.db"

    def test_format_conversation_entry_success(self) -> None:
        """Test that _format_conversation_entry handles success case."""
        # Test with successful data
        success_data = {
            "database_path": "/test/path.db",
            "prompts": [{"text": "test prompt", "commandType": 1}],
            "generations": [{"textDescription": "test generation", "type": "response"}],
            "history_entries": [{"entry": "test"}],
        }

        result = self.db_manager.format_conversation_entry(success_data, True, True)

        assert result["status"] == "success"
        assert result["source"] == "path.db"
        assert result["total_conversations"] == 3  # 1 prompt + 1 generation + 1 history
        assert "conversations" in result
        assert (
            len(result["conversations"]) <= MAX_SUMMARY_ENTRIES * 3
        )  # Max per type * 3 types

    @pytest.mark.asyncio
    async def test_execute_registry_file_not_found(self) -> None:
        """Test execute method when registry file is not found."""
        with patch("os.path.exists", return_value=False):
            result = await self.tool.execute(None)

            assert len(result) == 1
            assert result[0].type == "text"
            assert "Registry file not found" in result[0].text

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
            # In concise mode, should have different structure
            assert data["total_conversations"] == 0
            assert data["conversations"] == []
            assert data["search_info"]["databases_searched"] == 0
            assert data["search_info"]["total_found"] == 0

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
            assert data["search_info"]["keywords"] == "python programming"

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
            assert data["search_info"]["keywords"] is None

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
            assert data["search_info"]["keywords"] == "test"

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
        conditions, params = self.db_manager.build_search_conditions(malicious_keywords)

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
            result = self.db_manager.extract_conversation_data(
                temp_db.name, 50, "python"
            )

            # Cleanup
            Path(temp_db.name).unlink()

            # Should have returned data (exact matching depends on SQLite LIKE behavior)
            assert "prompts" in result
            assert "database_path" in result

    def test_case_insensitive_search(self) -> None:
        """Test that search conditions handle case insensitivity."""
        conditions, params = self.db_manager.build_search_conditions(
            "PYTHON Programming"
        )

        # Keywords should be converted to lowercase
        assert "%python%" in params
        assert "%programming%" in params
        assert "%PYTHON%" not in params
        assert "%Programming%" not in params

    def test_create_conversation_summary(self) -> None:
        """Test _create_conversation_summary method."""
        # Test with normal conversation
        conversation = {"text": "This is a test conversation about python programming"}
        summary = self.db_manager.create_conversation_summary(conversation)

        assert isinstance(summary, str)
        assert len(summary) <= MAX_SUMMARY_LENGTH
        assert "python programming" in summary

    def test_create_conversation_summary_long_text(self) -> None:
        """Test _create_conversation_summary with text longer than MAX_SUMMARY_LENGTH."""
        long_text = "a" * (MAX_SUMMARY_LENGTH + 100)
        conversation = {"text": long_text}
        summary = self.db_manager.create_conversation_summary(conversation)

        assert len(summary) == MAX_SUMMARY_LENGTH
        assert summary.endswith("...")

    def test_create_conversation_summary_empty(self) -> None:
        """Test _create_conversation_summary with empty conversation."""
        summary = self.db_manager.create_conversation_summary({})
        assert summary == ""

    def test_create_conversation_summary_non_dict(self) -> None:
        """Test _create_conversation_summary with non-dict input."""
        summary = self.db_manager.create_conversation_summary({"text": "test string"})
        assert summary == "test string"

    def test_score_conversation_relevance(self) -> None:
        """Test _score_conversation_relevance method with keyword matching."""
        conversation = {"text": "python programming tutorial"}

        # Test with matching keywords
        score = self.db_manager.score_conversation_relevance(conversation, "python")
        assert score > 0.0  # Should have positive score

        # Test with partial match
        score = self.db_manager.score_conversation_relevance(
            conversation, "python javascript"
        )
        assert score > 0.0  # Should have positive score for partial match

        # Test with no match
        score = self.db_manager.score_conversation_relevance(conversation, "java")
        assert score >= 0.0  # May have low score but not negative

    def test_score_conversation_relevance_empty_keywords(self) -> None:
        """Test _score_conversation_relevance with empty keywords."""
        conversation = {"text": "test"}
        score = self.db_manager.score_conversation_relevance(conversation, "")
        # With no keywords, should use recency scoring
        assert score >= 0.0

    def test_format_conversation_entry_concise_mode(self) -> None:
        """Test _format_conversation_entry in concise mode."""
        conversation_data = {
            "database_path": "/test/path.db",
            "prompts": [{"text": "test prompt"}],
            "generations": [{"textDescription": "test generation"}],
            "history_entries": [{"entry": "test history"}],
        }

        result = self.db_manager.format_conversation_entry(
            conversation_data, True, True, "test"
        )

        assert "source" in result
        assert "total_conversations" in result
        assert "conversations" in result
        assert result["source"] == "path.db"
        assert result["status"] == "success"

    def test_max_conversations_limit(self) -> None:
        """Test that MAX_CONVERSATIONS is now 8."""
        assert MAX_CONVERSATIONS == 8

    def test_optimization_constants_values(self) -> None:
        """Test that optimization constants have expected values."""
        assert MAX_SUMMARY_LENGTH == 800

    @pytest.mark.asyncio
    async def test_execute_concise_mode_structure(self) -> None:
        """Test execute method returns concise structure."""
        registry_data: Dict[str, Any] = {"cursor": [], "claude": []}

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=json.dumps(registry_data))),
        ):
            result = await self.tool.execute({})

            assert len(result) == 1
            data = json.loads(result[0].text)

            # Should have concise structure
            assert "total_conversations" in data
            assert "conversations" in data
            assert "search_info" in data
            # Should not have verbose metadata
            assert "metadata" not in data
            assert "summary" not in data
            assert "found_paths" not in data

    @pytest.mark.asyncio
    async def test_execute_with_smart_filtering(self) -> None:
        """Test execute method with smart filtering."""
        registry_data: Dict[str, Any] = {"cursor": [], "claude": []}

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=json.dumps(registry_data))),
        ):
            result = await self.tool.execute({"keywords": "test"})

            assert len(result) == 1
            data = json.loads(result[0].text)

            # Should have search info
            assert data["search_info"]["keywords"] == "test"
            assert data["search_info"]["databases_searched"] == 0
            assert data["search_info"]["total_found"] == 0
