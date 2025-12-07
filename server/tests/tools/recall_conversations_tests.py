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
    MAX_PHRASES,
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
        assert MAX_PHRASES is not None
        assert INCLUDE_PROMPTS_DEFAULT is not None
        assert INCLUDE_GENERATIONS_DEFAULT is not None
        assert MAX_SUMMARY_LENGTH is not None

    def test_recall_conversations_queries_structure(self) -> None:
        """Test that RECALL_CONVERSATIONS_QUERIES has expected structure."""
        assert "PROMPTS_KEY" in RECALL_CONVERSATIONS_QUERIES
        assert "GENERATIONS_KEY" in RECALL_CONVERSATIONS_QUERIES
        assert "HISTORY_KEY" in RECALL_CONVERSATIONS_QUERIES

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
        assert "phrases" in schema["properties"]

    def test_input_schema_uses_constants(self) -> None:
        """Test that input schema uses the constants."""
        schema = self.tool.input_schema
        assert (
            schema["properties"]["include_prompts"]["default"]
            == INCLUDE_PROMPTS_DEFAULT
        )
        assert (
            schema["properties"]["include_generations"]["default"]
            == INCLUDE_GENERATIONS_DEFAULT
        )

    def test_build_search_conditions_empty_phrases(self) -> None:
        """Test build_search_conditions with empty phrases."""
        conditions, params = self.db_manager.build_search_conditions([])

        assert conditions == []
        assert params == []

    def test_build_search_conditions_single_phrase(self) -> None:
        """Test build_search_conditions with single phrase."""
        conditions, params = self.db_manager.build_search_conditions(["python"])

        assert len(conditions) == 1
        assert conditions[0] == "value LIKE ?"
        assert len(params) == 1
        assert params[0] == "%python%"

    def test_build_search_conditions_multiple_phrases(self) -> None:
        """Test build_search_conditions with multiple phrases."""
        conditions, params = self.db_manager.build_search_conditions(
            ["python programming", "follow the rules"]
        )

        assert len(conditions) == 2
        assert all(condition == "value LIKE ?" for condition in conditions)
        assert len(params) == 2
        assert "%python programming%" in params
        assert "%follow the rules%" in params

    def test_build_search_conditions_multi_word_phrase(self) -> None:
        """Test build_search_conditions with multi-word phrase."""
        conditions, params = self.db_manager.build_search_conditions(
            ["the python and programming"]
        )

        # Entire phrase should be preserved
        assert len(conditions) == 1
        assert "%the python and programming%" in params

    def test_extract_conversation_data_without_phrases(self) -> None:
        """Test extract_conversation_data without phrases filtering."""
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

    def test_extract_conversation_data_with_phrases(self) -> None:
        """Test extract_conversation_data with phrases filtering."""
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
                temp_db.name, 50, ["python"]
            )

            assert "prompts" in result
            assert "database_path" in result

    def test_extract_conversation_data_database_error(self) -> None:
        """Test extract_conversation_data handles database errors."""
        # Test with non-existent database
        result = self.db_manager.extract_conversation_data("/nonexistent/path.db", 50)

        assert "error" in result
        assert result["error"] is not None

    def test_process_database_files_empty_registry(self) -> None:
        """Test process_database_files with empty registry."""
        registry_data: Dict[str, Any] = {}
        conversations, paths, total_files, file_counts = (
            self.db_manager.process_database_files(registry_data, 50)
        )

        assert conversations == []
        assert paths == []
        assert total_files == 0
        assert file_counts == {}

    def test_process_database_files_with_phrases(self) -> None:
        """Test process_database_files with phrases parameter."""
        registry_data: Dict[str, Any] = {}
        conversations, paths, total_files, file_counts = (
            self.db_manager.process_database_files(registry_data, 50, ["python"])
        )

        # Should handle phrases parameter gracefully even with empty registry
        assert conversations == []
        assert paths == []
        assert total_files == 0
        assert file_counts == {}

    def test_process_database_files_nonexistent_paths(self) -> None:
        """Test process_database_files with nonexistent paths."""
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
        """Test that format_conversation_entry returns expected structure."""
        # Test with error data
        error_data = {
            "database_path": "/test/path.db",
            "error": "Test error",
            "prompts": [],
            "generations": [],
            "history_entries": [],
        }

        result = self.db_manager.format_conversation_entry(error_data, True, True)

        # Error case returns flattened structure
        assert "status" in result
        assert "error" in result
        assert "conversations" in result
        assert result["status"] == "error"
        assert result["error"] == "Test error"
        assert result["conversations"] == []

    def test_format_conversation_entry_success(self) -> None:
        """Test that format_conversation_entry handles success case."""
        # Test with successful data
        success_data = {
            "database_path": "/test/path.db",
            "prompts": [{"text": "test prompt", "commandType": 1}],
            "generations": [{"textDescription": "test generation", "type": "response"}],
            "history_entries": [{"entry": "test"}],
        }

        result = self.db_manager.format_conversation_entry(success_data, True, True)

        assert result["status"] == "success"
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
            # Flattened structure with conversations list
            assert data["status"] == "success"
            assert data["conversations"] == []
            assert data["search_info"]["databases_searched"] == 0
            assert data["search_info"]["total_found"] == 0

    @pytest.mark.asyncio
    async def test_execute_with_phrases_parameter(self) -> None:
        """Test execute method with phrases parameter."""
        registry_data: Dict[str, Any] = {"cursor": [], "claude": []}

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=json.dumps(registry_data))),
        ):
            result = await self.tool.execute({"phrases": ["python programming"]})

            assert len(result) == 1
            assert result[0].type == "text"

            data = json.loads(result[0].text)
            assert data["search_info"]["phrases"] == ["python programming"]

    @pytest.mark.asyncio
    async def test_execute_without_phrases_parameter(self) -> None:
        """Test execute method without phrases parameter."""
        registry_data: Dict[str, Any] = {"cursor": [], "claude": []}

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=json.dumps(registry_data))),
        ):
            result = await self.tool.execute({})

            assert len(result) == 1
            assert result[0].type == "text"

            data = json.loads(result[0].text)
            assert data["search_info"]["phrases"] is None

    @pytest.mark.asyncio
    async def test_execute_with_arguments(self) -> None:
        """Test execute method with various arguments."""
        registry_data: Dict[str, Any] = {"cursor": [], "claude": []}
        test_args = {
            "phrases": ["test"],
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
            assert data["search_info"]["phrases"] == ["test"]

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
        # Test with potentially malicious phrases
        malicious_phrases = ["'; DROP TABLE ItemTable; --"]
        conditions, params = self.db_manager.build_search_conditions(malicious_phrases)

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

            # Test extraction with phrases
            result = self.db_manager.extract_conversation_data(
                temp_db.name, 50, ["python"]
            )

            # Cleanup
            Path(temp_db.name).unlink()

            # Should have returned data (exact matching depends on SQLite LIKE behavior)
            assert "prompts" in result
            assert "database_path" in result

    def test_create_conversation_summary(self) -> None:
        """Test create_conversation_summary method."""
        # Test with normal conversation
        conversation = {"text": "This is a test conversation about python programming"}
        summary = self.db_manager.create_conversation_summary(conversation)

        assert isinstance(summary, str)
        assert len(summary) <= MAX_SUMMARY_LENGTH
        assert "python programming" in summary

    def test_create_conversation_summary_long_text(self) -> None:
        """Test create_conversation_summary with text longer than MAX_SUMMARY_LENGTH."""
        long_text = "a" * (MAX_SUMMARY_LENGTH + 100)
        conversation = {"text": long_text}
        summary = self.db_manager.create_conversation_summary(conversation)

        assert len(summary) == MAX_SUMMARY_LENGTH
        assert "..." in summary

    def test_create_conversation_summary_empty(self) -> None:
        """Test create_conversation_summary with empty conversation."""
        summary = self.db_manager.create_conversation_summary({})
        assert summary == ""

    def test_create_conversation_summary_non_dict(self) -> None:
        """Test create_conversation_summary with non-dict input."""
        summary = self.db_manager.create_conversation_summary({"text": "test string"})
        assert summary == "test string"

    def test_score_conversation_relevance(self) -> None:
        """Test score_conversation_relevance method with phrase matching."""
        conversation = {"text": "python programming tutorial"}

        # Test with matching phrase
        score = self.db_manager.score_conversation_relevance(conversation, ["python"])
        assert score == 1.0  # Exact phrase match

        # Test with non-matching phrase
        score = self.db_manager.score_conversation_relevance(
            conversation, ["javascript"]
        )
        assert score == 0.0  # No match

        # Test with multiple phrases (OR logic)
        score = self.db_manager.score_conversation_relevance(
            conversation, ["java", "python"]
        )
        assert score == 1.0  # "python" matches

    def test_score_conversation_relevance_empty_phrases(self) -> None:
        """Test score_conversation_relevance with empty phrases."""
        conversation = {"text": "test"}
        score = self.db_manager.score_conversation_relevance(conversation, [])
        # With no phrases, should use recency scoring
        assert score >= 0.0

    def test_format_conversation_entry_with_phrases(self) -> None:
        """Test format_conversation_entry with phrases."""
        conversation_data = {
            "database_path": "/test/path.db",
            "prompts": [{"text": "test prompt"}],
            "generations": [{"textDescription": "test generation"}],
            "history_entries": [{"entry": "test history"}],
        }

        result = self.db_manager.format_conversation_entry(
            conversation_data, True, True, ["test"]
        )

        assert "conversations" in result
        assert result["status"] == "success"
        # Conversations should have relevance truncated to 4 decimal places
        for conv in result["conversations"]:
            if "relevance" in conv:
                relevance_str = str(conv["relevance"])
                if "." in relevance_str:
                    decimals = len(relevance_str.split(".")[1])
                    assert decimals <= 4

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

            # Should have flattened structure
            assert "status" in data
            assert "conversations" in data
            assert "search_info" in data
            # Should not have verbose metadata
            assert "metadata" not in data
            assert "found_paths" not in data

    @pytest.mark.asyncio
    async def test_execute_with_smart_filtering(self) -> None:
        """Test execute method with smart filtering."""
        registry_data: Dict[str, Any] = {"cursor": [], "claude": []}

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=json.dumps(registry_data))),
        ):
            result = await self.tool.execute({"phrases": ["test"]})

            assert len(result) == 1
            data = json.loads(result[0].text)

            # Should have search info
            assert data["search_info"]["phrases"] == ["test"]
            assert data["search_info"]["databases_searched"] == 0
            assert data["search_info"]["total_found"] == 0
