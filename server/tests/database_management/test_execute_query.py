"""
Tests for execute_query module.
"""

import json
import sqlite3
import tempfile

import pytest

from src.database_management.execute_query import QueryExecutor
from src.config.constants import RECALL_CONVERSATIONS_QUERIES


class TestQueryExecutor:
    """Test suite for QueryExecutor class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.query_executor = QueryExecutor()

    def test_execute_conversation_query_without_keywords(self) -> None:
        """Test execute_conversation_query without keywords."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            # Create a test database
            conn = sqlite3.connect(temp_db.name)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE ItemTable (key TEXT, value TEXT)")
            cursor.execute(
                "INSERT INTO ItemTable VALUES (?, ?)",
                (RECALL_CONVERSATIONS_QUERIES["PROMPTS_KEY"], "[]"),
            )
            conn.commit()
            conn.close()

            result = self.query_executor.execute_conversation_query(temp_db.name, 50)

            assert "prompts" in result
            assert "generations" in result
            assert "history_entries" in result
            assert "database_path" in result
            assert result["database_path"] == temp_db.name
            assert result["error"] is None

    def test_execute_conversation_query_with_keywords(self) -> None:
        """Test execute_conversation_query with keywords."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            # Create a test database
            conn = sqlite3.connect(temp_db.name)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE ItemTable (key TEXT, value TEXT)")
            cursor.execute(
                "INSERT INTO ItemTable VALUES (?, ?)",
                (
                    RECALL_CONVERSATIONS_QUERIES["PROMPTS_KEY"],
                    json.dumps([{"text": "python programming tutorial"}]),
                ),
            )
            conn.commit()
            conn.close()

            result = self.query_executor.execute_conversation_query(
                temp_db.name, 50, ["python"]
            )

            assert "prompts" in result
            assert "generations" in result
            assert "history_entries" in result
            assert "database_path" in result
            assert result["database_path"] == temp_db.name
            assert result["error"] is None

    def test_execute_conversation_query_database_error(self) -> None:
        """Test execute_conversation_query handles database errors."""
        # Test with non-existent database
        result = self.query_executor.execute_conversation_query(
            "/nonexistent/path.db", 50
        )

        assert "error" in result
        assert result["error"] is not None

    def test_execute_single_query_success(self) -> None:
        """Test _execute_single_query with successful execution."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            conn = sqlite3.connect(temp_db.name)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE ItemTable (key TEXT, value TEXT)")
            cursor.execute(
                "INSERT INTO ItemTable VALUES (?, ?)",
                (
                    RECALL_CONVERSATIONS_QUERIES["PROMPTS_KEY"],
                    json.dumps([{"text": "test prompt 1"}, {"text": "test prompt 2"}]),
                ),
            )
            conn.commit()

            result = self.query_executor._execute_single_query(
                cursor,
                "SELECT value FROM ItemTable WHERE key = ?",
                "SELECT value FROM ItemTable WHERE key = ?",
                [],
                [],
                RECALL_CONVERSATIONS_QUERIES["PROMPTS_KEY"],
                2,
            )

            assert len(result) == 2
            assert result[0]["text"] == "test prompt 1"
            assert result[1]["text"] == "test prompt 2"

            conn.close()

    def test_execute_single_query_json_error(self) -> None:
        """Test _execute_single_query with JSON decode error."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            conn = sqlite3.connect(temp_db.name)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE ItemTable (key TEXT, value TEXT)")
            cursor.execute(
                "INSERT INTO ItemTable VALUES (?, ?)",
                (RECALL_CONVERSATIONS_QUERIES["PROMPTS_KEY"], "invalid json"),
            )
            conn.commit()

            with pytest.raises(ValueError, match="Error parsing"):
                self.query_executor._execute_single_query(
                    cursor,
                    "SELECT value FROM ItemTable WHERE key = ?",
                    "SELECT value FROM ItemTable WHERE key = ?",
                    [],
                    [],
                    RECALL_CONVERSATIONS_QUERIES["PROMPTS_KEY"],
                    2,
                )

            conn.close()

    def test_execute_single_query_empty_result(self) -> None:
        """Test _execute_single_query with empty result."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            conn = sqlite3.connect(temp_db.name)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE ItemTable (key TEXT, value TEXT)")
            conn.commit()

            result = self.query_executor._execute_single_query(
                cursor,
                "SELECT value FROM ItemTable WHERE key = ?",
                "SELECT value FROM ItemTable WHERE key = ?",
                [],
                [],
                RECALL_CONVERSATIONS_QUERIES["PROMPTS_KEY"],
                2,
            )

            assert result == []

            conn.close()

    def test_execute_single_query_limit_application(self) -> None:
        """Test _execute_single_query applies limit correctly."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            conn = sqlite3.connect(temp_db.name)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE ItemTable (key TEXT, value TEXT)")
            cursor.execute(
                "INSERT INTO ItemTable VALUES (?, ?)",
                (
                    RECALL_CONVERSATIONS_QUERIES["PROMPTS_KEY"],
                    json.dumps([{"text": f"prompt {i}"} for i in range(10)]),
                ),
            )
            conn.commit()

            result = self.query_executor._execute_single_query(
                cursor,
                "SELECT value FROM ItemTable WHERE key = ?",
                "SELECT value FROM ItemTable WHERE key = ?",
                [],
                [],
                RECALL_CONVERSATIONS_QUERIES["PROMPTS_KEY"],
                3,
            )

            # Should return only the last 3 items (most recent)
            assert len(result) == 3
            assert result[0]["text"] == "prompt 7"
            assert result[1]["text"] == "prompt 8"
            assert result[2]["text"] == "prompt 9"

            conn.close()
