"""Test cursor query functionality."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

from src.tool_calls.cursor.query import (
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

        with patch("src.utils.cursor_chat_query.CursorQuery") as mock_cursor:
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

        with patch("src.utils.cursor_chat_query.CursorQuery") as mock_cursor:
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

        with patch("src.utils.cursor_chat_query.CursorQuery") as mock_cursor:
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

    def test_handle_query_cursor_conversations_markdown(self):
        """Test markdown format output."""
        arguments = {"format": "markdown"}
        project_root = Path("/test/project")
        with patch("src.utils.cursor_chat_query.CursorQuery") as mock_cursor:
            mock_instance = Mock()
            mock_cursor.return_value = mock_instance
            mock_instance.query_all_conversations.return_value = {
                "workspaces": [
                    {
                        "conversations": [{"name": "Test"}],
                        "prompts": [],
                        "generations": [],
                    }
                ],
                "query_timestamp": "2023-01-01T00:00:00Z",
            }
            mock_instance.format_as_markdown.return_value = "# Markdown Export"
            result = handle_query_cursor_conversations(arguments, project_root)
            assert "content" in result
            # Check that we get markdown-like content (starts with #)
            content_text = result["content"][0]["text"]
            assert content_text.startswith("#")

    def test_handle_query_cursor_conversations_cursor_format(self):
        """Test cursor format output."""
        arguments = {"format": "cursor"}
        project_root = Path("/test/project")
        with patch("src.utils.cursor_chat_query.CursorQuery") as mock_cursor:
            mock_instance = Mock()
            mock_cursor.return_value = mock_instance
            mock_instance.query_all_conversations.return_value = {
                "workspaces": [
                    {
                        "conversations": [{"name": "Test"}],
                        "prompts": [],
                        "generations": [],
                    }
                ],
                "query_timestamp": "2023-01-01T00:00:00Z",
            }
            mock_instance.format_as_cursor_markdown.return_value = "# Cursor Export"
            result = handle_query_cursor_conversations(arguments, project_root)
            assert "content" in result
            # Check that we get markdown-like content (starts with #)
            content_text = result["content"][0]["text"]
            assert content_text.startswith("#")

    def test_handle_query_cursor_conversations_empty_data(self):
        """Test with no workspaces or conversations."""
        arguments = {"format": "json"}
        project_root = Path("/test/project")
        with patch("src.utils.cursor_chat_query.CursorQuery") as mock_cursor:
            mock_instance = Mock()
            mock_cursor.return_value = mock_instance
            mock_instance.query_all_conversations.return_value = {
                "workspaces": [],
                "query_timestamp": "2023-01-01T00:00:00Z",
            }
            result = handle_query_cursor_conversations(arguments, project_root)
            assert "content" in result
            assert "workspaces" in result["content"][0]["text"]

    def test_handle_query_cursor_conversations_summary_edge_cases(self):
        """Test summary with missing fields and no conversations."""
        arguments = {"summary": True}
        project_root = Path("/test/project")
        with patch("src.utils.cursor_chat_query.CursorQuery") as mock_cursor:
            mock_instance = Mock()
            mock_cursor.return_value = mock_instance
            # Workspace with no conversations
            mock_instance.query_all_conversations.return_value = {
                "workspaces": [{"conversations": [], "prompts": [], "generations": []}],
                "query_timestamp": "2023-01-01T00:00:00Z",
            }
            result = handle_query_cursor_conversations(arguments, project_root)
            assert "content" in result
            # Workspace with missing fields
            mock_instance.query_all_conversations.return_value = {
                "workspaces": [{}],
                "query_timestamp": "2023-01-01T00:00:00Z",
            }
            result = handle_query_cursor_conversations(arguments, project_root)
            assert "content" in result

    def test_handle_query_cursor_conversations_oserror(self):
        """Test OSError handling in query handler."""
        arguments = {"format": "json"}
        project_root = Path("/test/project")
        with patch("src.tool_calls.cursor.query.CursorQuery") as mock_cursor:
            mock_instance = Mock()
            mock_cursor.return_value = mock_instance
            mock_instance.query_all_conversations.side_effect = OSError("DB error")
            result = handle_query_cursor_conversations(arguments, project_root)
            assert result["isError"] is True
            assert "Error querying cursor conversations" in result["error"]

    def test_handle_query_cursor_conversations_valueerror(self):
        """Test ValueError handling in query handler."""
        arguments = {"format": "json"}
        project_root = Path("/test/project")
        with patch("src.tool_calls.cursor.query.CursorQuery") as mock_cursor:
            mock_instance = Mock()
            mock_cursor.return_value = mock_instance
            mock_instance.query_all_conversations.side_effect = ValueError("bad value")
            result = handle_query_cursor_conversations(arguments, project_root)
            assert result["isError"] is True

    def test_handle_query_cursor_conversations_typeerror(self):
        """Test TypeError handling in query handler."""
        arguments = {"format": "json"}
        project_root = Path("/test/project")
        with patch("src.tool_calls.cursor.query.CursorQuery") as mock_cursor:
            mock_instance = Mock()
            mock_cursor.return_value = mock_instance
            mock_instance.query_all_conversations.side_effect = TypeError("bad type")
            result = handle_query_cursor_conversations(arguments, project_root)
            assert result["isError"] is True

    def test_handle_query_cursor_conversations_keyerror(self):
        """Test KeyError handling in query handler."""
        arguments = {"format": "json"}
        project_root = Path("/test/project")
        with patch("src.tool_calls.cursor.query.CursorQuery") as mock_cursor:
            mock_instance = Mock()
            mock_cursor.return_value = mock_instance
            mock_instance.query_all_conversations.side_effect = KeyError("missing key")
            result = handle_query_cursor_conversations(arguments, project_root)
            assert result["isError"] is True

    def test_handle_query_cursor_conversations_file_not_found(self):
        """Test FileNotFoundError handling in query handler."""
        arguments = {"format": "json"}
        project_root = Path("/test/project")
        with patch("src.tool_calls.cursor.query.CursorQuery") as mock_cursor:
            mock_instance = Mock()
            mock_cursor.return_value = mock_instance
            mock_instance.query_all_conversations.side_effect = FileNotFoundError(
                "not found"
            )
            result = handle_query_cursor_conversations(arguments, project_root)
            assert result["isError"] is True

    def test_handle_list_cursor_workspaces_oserror(self):
        """Test OSError handling in workspace listing."""
        arguments = {}
        project_root = Path("/test/project")
        with patch(
            "src.tool_calls.cursor.query.list_cursor_workspaces",
            side_effect=OSError("fail"),
        ):
            result = handle_list_cursor_workspaces(arguments, project_root)
            assert result["isError"] is True
            assert "fail" in result["error"]

    def test_handle_list_cursor_workspaces_valueerror(self):
        """Test ValueError handling in workspace listing."""
        arguments = {}
        project_root = Path("/test/project")
        with patch(
            "src.tool_calls.cursor.query.list_cursor_workspaces",
            side_effect=ValueError("fail"),
        ):
            result = handle_list_cursor_workspaces(arguments, project_root)
            assert result["isError"] is True

    def test_handle_list_cursor_workspaces_typeerror(self):
        """Test TypeError handling in workspace listing."""
        arguments = {}
        project_root = Path("/test/project")
        with patch(
            "src.tool_calls.cursor.query.list_cursor_workspaces",
            side_effect=TypeError("fail"),
        ):
            result = handle_list_cursor_workspaces(arguments, project_root)
            assert result["isError"] is True

    def test_handle_list_cursor_workspaces_keyerror(self):
        """Test KeyError handling in workspace listing."""
        arguments = {}
        project_root = Path("/test/project")
        with patch(
            "src.tool_calls.cursor.query.list_cursor_workspaces",
            side_effect=KeyError("fail"),
        ):
            result = handle_list_cursor_workspaces(arguments, project_root)
            assert result["isError"] is True

    def test_handle_list_cursor_workspaces_attributeerror(self):
        """Test AttributeError handling in workspace listing."""
        arguments = {}
        project_root = Path("/test/project")
        with patch(
            "src.tool_calls.cursor.query.list_cursor_workspaces",
            side_effect=AttributeError("fail"),
        ):
            result = handle_list_cursor_workspaces(arguments, project_root)
            assert result["isError"] is True

    def test_handle_query_cursor_conversations_error(self):
        """Test error handling in cursor query."""
        arguments = {"format": "json"}
        project_root = Path("/test/project")
        with patch("src.tool_calls.cursor.query.CursorQuery") as mock_cursor:
            mock_cursor.side_effect = OSError("Database error")
            result = handle_query_cursor_conversations(arguments, project_root)
            assert result["isError"] is True
            assert "Database error" in result["error"]
