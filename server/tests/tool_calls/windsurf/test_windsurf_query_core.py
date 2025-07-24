"""
Tests for Windsurf query core functionality.

lotr-info: Tests Windsurf conversation queries using Fellowship council discussions
and Shire meeting records as sample data.
"""

import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.config.constants.database import (
    WINDSURF_KEY_CHAT_SESSION_STORE,
)
from src.tool_calls.windsurf.query import (
    TOOL_QUERY_WINDSURF_CONVERSATIONS,
    _format_response,
    handle_query_windsurf_conversations,
)
from src.tool_calls.windsurf.windsurf_query import WindsurfQuery


class TestWindsurfQuery:
    """Test Windsurf query functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_root = self.temp_dir / "project"
        self.project_root.mkdir()

    def teardown_method(self):
        """Clean up test fixtures and database connections."""
        import shutil

        from src.utils.database_pool import close_database_pool

        close_database_pool()

        # Clean up test directory
        if hasattr(self, "temp_dir") and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_mock_database(self, conversations=None):
        """Create a mock database for testing."""
        if conversations is None:
            conversations = [
                {
                    "id": "council_elrond",
                    "title": "Council of Elrond discussion",
                    "content": "How shall we destroy the One Ring?",
                    "timestamp": "2024-01-01T10:00:00Z",
                }
            ]

        db_path = self.temp_dir / "test.db"
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()

            # Create ItemTable structure like Windsurf uses
            cursor.execute(
                """
                CREATE TABLE ItemTable (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """
            )

            # Insert chat session data
            chat_data = {
                "entries": {
                    "fellowship_session": {
                        "messages": [
                            {"content": "Greetings from Rivendell", "user": "human"},
                            {
                                "content": "Welcome, friend of Elrond!",
                                "user": "assistant",
                            },
                        ],
                        "text": "This is a conversation about the Fellowship quest",
                    }
                }
            }

            cursor.execute(
                """
                INSERT INTO ItemTable (key, value)
                VALUES (?, ?)
            """,
                (WINDSURF_KEY_CHAT_SESSION_STORE[0], json.dumps(chat_data)),
            )

            conn.commit()

        return db_path

    def test_windsurf_query_initialization(self):
        """Test WindsurfQuery initialization."""
        query = WindsurfQuery()
        assert query is not None
        assert hasattr(query, "query_all_conversations")
        assert hasattr(query, "search_conversations")
        assert hasattr(query, "silent")
        assert hasattr(query, "workspace_storage")
        assert hasattr(query, "global_storage")
        assert hasattr(query, "db_reader")
        assert hasattr(query, "validator")
        assert hasattr(query, "extractor")

    def test_windsurf_query_initialization_silent(self):
        """Test WindsurfQuery initialization with silent mode."""
        query = WindsurfQuery(silent=True)
        assert query.silent is True
        assert query.db_reader.silent is True

    @patch("src.tool_calls.windsurf.query.WindsurfQuery")
    def test_handle_query_windsurf_conversations_basic(self, mock_query_class):
        """Test basic query handling."""
        mock_instance = Mock()
        mock_query_class.return_value = mock_instance
        mock_instance.query_all_conversations.return_value = {
            "conversations": [
                {
                    "id": "hobbiton_council",
                    "title": "Hobbiton harvest planning",
                    "content": "Discussing this year's pipeweed cultivation",
                }
            ],
            "total": 1,
        }

        arguments = {"format": "json"}
        result = handle_query_windsurf_conversations(arguments, self.project_root)

        assert "content" in result
        assert len(result["content"]) > 0
        mock_instance.query_all_conversations.assert_called_once()

    @patch("src.tool_calls.windsurf.query.WindsurfQuery")
    def test_handle_query_windsurf_conversations_with_summary(self, mock_query_class):
        """Test query handling with summary format."""
        mock_instance = Mock()
        mock_query_class.return_value = mock_instance
        mock_instance.query_all_conversations.return_value = {
            "conversations": [{"id": "shire_meeting", "title": "Shire governance"}],
            "total": 1,
        }

        arguments = {"format": "json", "summary": True}
        result = handle_query_windsurf_conversations(arguments, self.project_root)

        assert "content" in result
        mock_instance.query_all_conversations.assert_called_once()

    @patch("src.tool_calls.windsurf.query.WindsurfQuery")
    def test_handle_query_windsurf_conversations_exception(self, mock_query_class):
        """Test query handling with exception."""
        mock_instance = Mock()
        mock_query_class.return_value = mock_instance
        mock_instance.query_all_conversations.side_effect = ValueError(
            "Ring bearer error"
        )

        arguments = {"format": "json"}
        result = handle_query_windsurf_conversations(arguments, self.project_root)

        assert result["isError"] is True
        assert "Error querying Windsurf conversations" in result["content"][0]["text"]

    def test_handle_query_invalid_format(self):
        """Test query handling with invalid format."""
        arguments = {"format": "invalid"}
        result = handle_query_windsurf_conversations(arguments, self.project_root)

        assert result["isError"] is True
        assert "format must be one of" in result["content"][0]["text"]

    def test_windsurf_query_search_conversations_method(self):
        """Test the search_conversations method exists and can be called."""
        query = WindsurfQuery()

        # Mock the internal methods to avoid actual database operations
        with patch.object(query, "_find_workspace_databases", return_value=[]):
            result = query.search_conversations(query="test", limit=10)

            # Should return a list
            assert isinstance(result, list)

    def test_windsurf_query_query_all_conversations_method(self):
        """Test the query_all_conversations method exists and can be called."""
        query = WindsurfQuery()

        # Mock the internal methods to avoid actual database operations
        with patch.object(query, "_find_workspace_databases", return_value=[]):
            result = query.query_all_conversations()

            # Should return a dictionary with expected structure
            assert isinstance(result, dict)

    def test_tool_definition_structure(self):
        """Test that the tool definition has the correct structure."""
        tool = TOOL_QUERY_WINDSURF_CONVERSATIONS

        assert tool["name"] == "query_windsurf_conversations"
        assert "description" in tool
        assert "inputSchema" in tool
        assert "properties" in tool["inputSchema"]
        assert "format" in tool["inputSchema"]["properties"]

    @patch("src.tool_calls.windsurf.query.WindsurfQuery")
    def test_handle_query_with_different_formats(self, mock_query_class):
        """Test query handling with different output formats."""
        mock_instance = Mock()
        mock_query_class.return_value = mock_instance
        mock_instance.query_all_conversations.return_value = {
            "conversations": [
                {"id": "minas_tirith_planning", "title": "White City architecture"}
            ],
            "total": 1,
        }

        # Test markdown format
        arguments = {"format": "markdown"}
        result = handle_query_windsurf_conversations(arguments, self.project_root)
        assert "content" in result

        # Test windsurf format
        arguments = {"format": "windsurf"}
        result = handle_query_windsurf_conversations(arguments, self.project_root)
        assert "content" in result

    def test_windsurf_query_with_mock_database_operations(self):
        """Test WindsurfQuery with mocked database operations."""
        query = WindsurfQuery()

        # Mock database finding to return our test database
        mock_db_path = self.create_mock_database()

        with patch.object(
            query, "_find_workspace_databases", return_value=[mock_db_path]
        ):
            result = query.query_all_conversations()
            assert isinstance(result, dict)
            assert "conversations" in result

    def test_windsurf_query_error_handling(self):
        """Test WindsurfQuery error handling."""
        query = WindsurfQuery()

        # Test with invalid database path
        with patch.object(
            query,
            "_find_workspace_databases",
            return_value=[Path("/nonexistent/path")],
        ):
            result = query.query_all_conversations()
            # Should handle errors gracefully
            assert isinstance(result, dict)

    def test_windsurf_query_get_data_from_db(self):
        """Test get_data_from_db method."""
        query = WindsurfQuery()
        mock_db_path = self.create_mock_database()

        # Test successful data retrieval
        result = query.get_data_from_db(
            mock_db_path, WINDSURF_KEY_CHAT_SESSION_STORE[0]
        )
        assert result is not None
        assert isinstance(result, dict)
        assert "entries" in result

    def test_windsurf_query_get_data_from_db_error(self):
        """Test get_data_from_db method with error."""
        query = WindsurfQuery()

        # Test with nonexistent database
        result = query.get_data_from_db(Path("/nonexistent/path"), "test_key")
        assert result is None

    def test_windsurf_query_find_workspace_databases(self):
        """Test find_workspace_databases method."""
        query = WindsurfQuery()

        # Mock the storage paths to avoid accessing real system
        with patch.object(query, "workspace_storage", [self.temp_dir]):
            with patch.object(query, "global_storage", self.temp_dir):
                # Create mock workspace structure
                workspace_dir = self.temp_dir / "workspace1"
                workspace_dir.mkdir()
                db_file = workspace_dir / "state.vscdb"
                db_file.write_text("mock db")

                # Create global db
                global_db = self.temp_dir / "state.vscdb"
                global_db.write_text("mock global db")

                databases = query.find_workspace_databases()
                assert len(databases) >= 1

    def test_windsurf_query_search_conversations_with_data(self):
        """Test search_conversations with actual data."""
        query = WindsurfQuery()

        # Test conversations about different topics
        test_conversations = [
            {
                "id": "python_quest",
                "session_data": {"messages": [{"content": "Python spell casting"}]},
                "title": "Python Magic",
                "content": "How to use python for Ring analysis?",
            },
            {
                "id": "javascript_lore",
                "session_data": {"messages": [{"content": "JavaScript enchantments"}]},
                "title": "JS Wizardry",
                "content": "How to use javascript for palantir communication?",
            },
        ]

        with patch.object(query, "query_all_conversations") as mock_query:
            mock_query.return_value = {"conversations": test_conversations}

            # Search for "python"
            results = query.search_conversations("python", limit=10)
            assert len(results) == 1
            assert results[0]["conversation"]["id"] == "python_quest"

    def test_windsurf_query_query_conversations_from_db(self):
        """Test query_conversations_from_db method."""
        query = WindsurfQuery()
        mock_db_path = self.create_mock_database()

        result = query.query_conversations_from_db(mock_db_path)
        assert isinstance(result, dict)
        assert "conversations" in result
        assert "total_conversations" in result
        assert "database_path" in result

    def test_format_response_json(self):
        """Test _format_response with JSON format."""
        data = {
            "conversations": [
                {"id": "rohan_strategy", "workspace_id": "edoras", "source": "test"}
            ]
        }

        result = _format_response(data, "json")
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "conversations" in parsed

    def test_format_response_markdown(self):
        """Test _format_response with markdown format."""
        data = {
            "conversations": [
                {
                    "id": "gondor_plans",
                    "workspace_id": "minas_tirith",
                    "source": "test",
                    "session_data": {"content": "Defense strategy for Gondor"},
                }
            ]
        }

        result = _format_response(data, "markdown")
        assert isinstance(result, str)
        assert "# Windsurf Conversations" in result
        assert "## Conversation 1" in result

    def test_format_response_windsurf(self):
        """Test _format_response with windsurf format."""
        data = {"conversations": [{"id": "fellowship_discussion"}]}

        result = _format_response(data, "windsurf")
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "conversations" in parsed

    def test_handle_query_with_limit(self):
        """Test query handling with limit parameter."""
        with patch("src.tool_calls.windsurf.query.WindsurfQuery") as mock_query_class:
            mock_instance = Mock()
            mock_query_class.return_value = mock_instance

            # Create more conversations than the limit
            conversations = [
                {"id": f"hobbit_{i}", "title": f"Hobbit meeting {i}"} for i in range(10)
            ]
            mock_instance.query_all_conversations.return_value = {
                "conversations": conversations
            }

            arguments = {"format": "json", "limit": 5}
            result = handle_query_windsurf_conversations(arguments, self.project_root)

            assert "content" in result
            content_text = result["content"][0]["text"]
            response_data = json.loads(content_text)
            assert len(response_data["conversations"]) == 5
            assert response_data["limited_results"] is True
            assert response_data["limit_applied"] == 5
