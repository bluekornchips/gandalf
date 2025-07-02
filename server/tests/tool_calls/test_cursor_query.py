"""Test cursor query functionality."""

from pathlib import Path
from unittest.mock import Mock, patch

from src.tool_calls.cursor_query import (
    handle_list_cursor_workspaces,
    handle_query_cursor_conversations,
)


class TestCursorQuery:
    """Test cursor query functionality."""

    def test_handle_query_cursor_conversations_basic(self):
        """Test basic cursor conversation querying."""
        arguments = {"format": "json", "summary": False}

        # Mock project root
        project_root = Path("/test/project")

        with patch("src.tool_calls.cursor_query.CursorQuery") as mock_cursor:
            mock_instance = Mock()
            mock_cursor.return_value = mock_instance
            mock_instance.query_all_conversations.return_value = {
                "workspaces": [],
                "query_timestamp": "2023-01-01T00:00:00Z",
            }

            result = handle_query_cursor_conversations(arguments, project_root)

            assert "content" in result
            assert len(result["content"]) > 0

    def test_handle_query_cursor_conversations_summary(self):
        """Test cursor conversation querying in summary mode."""
        arguments = {"summary": True}

        # Mock project root
        project_root = Path("/test/project")

        with patch("src.tool_calls.cursor_query.CursorQuery") as mock_cursor:
            mock_instance = Mock()
            mock_cursor.return_value = mock_instance
            mock_instance.get_conversation_summary.return_value = {
                "total_conversations": 10,
                "total_prompts": 50,
                "total_generations": 45,
                "workspaces": [],
            }

            result = handle_query_cursor_conversations(arguments, project_root)

            assert "content" in result
            assert len(result["content"]) > 0

    def test_handle_list_cursor_workspaces_basic(self):
        """Test basic cursor workspace listing."""
        arguments = {}

        project_root = Path("/test/project")

        with patch("src.tool_calls.cursor_query.CursorQuery") as mock_cursor:
            mock_instance = Mock()
            mock_cursor.return_value = mock_instance
            # Mock find_workspace_databases to return an iterable list of Path objects
            mock_db_path = Mock()
            mock_db_path.parent.name = "shadowfax123"
            mock_db_path.exists.return_value = True
            mock_instance.find_workspace_databases.return_value = [mock_db_path]

            result = handle_list_cursor_workspaces(arguments, project_root)

            assert "content" in result
            assert len(result["content"]) > 0

    def test_format_validation(self):
        """Test format parameter validation."""
        arguments = {"format": "invalid_format"}

        project_root = Path("/test/project")

        result = handle_query_cursor_conversations(arguments, project_root)

        assert "content" in result or "isError" in result
