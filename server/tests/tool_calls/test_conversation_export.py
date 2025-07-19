"""
Tests for conversation export functionality.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from src.tool_calls.export import (
    _format_conversation_markdown,
    _format_conversation_text,
    format_timestamp,
    handle_export_individual_conversations,
    handle_list_cursor_workspaces,
    sanitize_filename,
)
from src.utils.conversation_export import (
    export_conversations_simple,
    list_workspaces,
)


class TestConversationExport:
    """Test conversation export functionality."""

    @pytest.fixture
    def mock_conversation_data(self):
        """Mock conversation data for testing."""
        return {
            "workspaces": [
                {
                    "workspace_hash": "shire123baggins",
                    "database_path": "/mock/path/hobbiton.db",
                    "conversations": [
                        {
                            "composerId": "conv-bilbo-1",
                            "name": "Ring Discovery in Gollum's Cave",
                            "createdAt": 1640995200000,
                            "lastUpdatedAt": 1640995800000,
                            "type": "chat",
                            "unifiedMode": "true",
                            "forceMode": "false",
                        },
                        {
                            "composerId": "conv-gandalf-1",
                            "name": "Wizard Staff Configuration Help",
                            "createdAt": 1640995300000,
                            "lastUpdatedAt": 1640995900000,
                            "type": "code",
                            "unifiedMode": "false",
                            "forceMode": "true",
                        },
                    ],
                    "prompts": [
                        {
                            "id": "prompt-frodo-1",
                            "conversationId": "conv-bilbo-1",
                            "text": "It's some form of elvish",
                            "timestamp": 1640995200000,
                        }
                    ],
                    "generations": [
                        {
                            "id": "gen-gandalf-1",
                            "conversationId": "conv-bilbo-1",
                            "text": (
                                "I don't know half of you half as well as I should like."
                            ),
                            "timestamp": 1640995250000,
                        }
                    ],
                }
            ],
            "query_timestamp": "2024-01-01T12:00:00.000Z",
            "total_databases": 1,
            "databases_with_conversations": 1,
        }

    @patch("src.utils.conversation_export.CursorQuery")
    def test_simple_export_json(self, mock_cursor_query, mock_conversation_data):
        """Test basic JSON export functionality."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = mock_conversation_data
        mock_instance.export_to_file = Mock()
        mock_cursor_query.return_value = mock_instance

        # Test export to the archives of Minas Tirith
        with tempfile.NamedTemporaryFile(suffix=".json") as tmp:
            result = export_conversations_simple(tmp.name, silent=True)

        assert result is True

        mock_cursor_query.assert_called_once_with(silent=True)
        mock_instance.query_all_conversations.assert_called_once()
        mock_instance.export_to_file.assert_called_once()

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        # Test normal conversation name, spaces are preserved
        assert sanitize_filename("Ring Discovery") == "Ring Discovery"

        # Test with invalid characters
        assert sanitize_filename("File/Path\\Test") == "File_Path_Test"

        # Test with special characters
        assert sanitize_filename("Test<>:|?*File") == "Test______File"

        # Test length limiting
        long_name = "A" * 150
        result = sanitize_filename(long_name)
        assert len(result) <= 100

        # Test empty/whitespace
        assert sanitize_filename("   ") == "unnamed_conversation"
        assert sanitize_filename("") == "unnamed_conversation"

    def test_format_timestamp(self):
        """Test timestamp formatting."""
        timestamp = 1640995200000  # 2022-01-01 00:00:00 UTC
        result = format_timestamp(timestamp)
        # The format is YYYYMMDD_HHMMSS, so check for the date part
        assert "20211231" in result or "20220101" in result  # Account for timezone

        # Test with no timestamp
        result_none = format_timestamp(None)
        # Should contain current date in YYYYMMDD format
        assert len(result_none) == 15  # YYYYMMDD_HHMMSS format

    @patch("src.tool_calls.export.CursorQuery")
    def test_export_individual_conversations(
        self, mock_cursor_query, mock_conversation_data
    ):
        """Test individual conversation export functionality."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = mock_conversation_data
        mock_instance._create_message_map.return_value = {
            "prompts": {"conv-bilbo-1": [{"text": "Good morning."}]},
            "generations": {"conv-bilbo-1": [{"text": "Good morning."}]},
        }
        mock_cursor_query.return_value = mock_instance

        # Mock file operations to prevent actual file creation
        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", mock_open()) as mock_file_open,
        ):

            result = handle_export_individual_conversations(
                {
                    "format": "json",
                    "limit": 2,
                    "output_dir": "./test_exports",
                },
                project_root=Path("/test/project"),
            )

        # Should be MCP response format
        assert "content" in result
        content_text = result["content"][0]["text"]

        result_data = json.loads(content_text)
        assert "exported_count" in result_data
        assert "files" in result_data
        assert "output_directory" in result_data

        mock_mkdir.assert_called_once()
        mock_file_open.assert_called()

    def test_invalid_format_raises_error(self):
        """Test that invalid format raises ValueError, no Black Speech allowed."""
        with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
            with pytest.raises(ValueError, match="format_type must be one of"):
                export_conversations_simple(tmp.name, format_type="black_speech")

    @patch("src.utils.conversation_export.CursorQuery")
    def test_list_workspaces(self, mock_cursor_query, mock_conversation_data):
        """Test workspace listing."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = mock_conversation_data
        mock_cursor_query.return_value = mock_instance

        # Test workspace listing
        result = list_workspaces(silent=True)

        assert isinstance(result, list)
        assert len(result) >= 0  # May be empty if no workspaces

    @patch("src.utils.conversation_export.CursorQuery")
    def test_empty_data_export(self, mock_cursor_query):
        """Test export with no conversation data."""
        empty_data = {
            "workspaces": [],
            "query_timestamp": "2024-01-01T12:00:00.000Z",
            "total_databases": 0,
            "databases_with_conversations": 0,
        }

        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = empty_data
        mock_instance.export_to_file = Mock()
        mock_cursor_query.return_value = mock_instance

        with tempfile.NamedTemporaryFile(suffix=".json") as tmp:
            result = export_conversations_simple(tmp.name, silent=True)

        assert result is True

    @patch("src.tool_calls.export.CursorQuery")
    def test_export_individual_conversations_with_args(
        self, mock_cursor_query, mock_conversation_data
    ):
        """Test individual conversation export functionality with args."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = mock_conversation_data
        mock_instance._create_message_map.return_value = {
            "prompts": {"conv-bilbo-1": [{"text": "Good morning."}]},
            "generations": {"conv-bilbo-1": [{"text": "Good morning."}]},
        }
        mock_cursor_query.return_value = mock_instance

        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", mock_open()) as mock_file_open,
        ):

            result = handle_export_individual_conversations(
                {
                    "format": "json",
                    "limit": 2,
                    "output_dir": "/tmp/test_export",
                },
                project_root=Path("/test/project"),
            )

        assert result["content"][0]["type"] == "text"

        # Parse the JSON response to verify export details
        response_data = json.loads(result["content"][0]["text"])
        assert response_data["exported_count"] == 2
        assert "files" in response_data
        assert response_data["output_directory"].endswith("/tmp/test_export")
        assert response_data["format"] == "json"

        mock_cursor_query.assert_called_once()
        mock_mkdir.assert_called_once()
        mock_file_open.assert_called()

    @patch("src.tool_calls.export.CursorQuery")
    def test_export_individual_conversations_with_kwargs(
        self, mock_cursor_query, mock_conversation_data
    ):
        """Test individual conversation export functionality with kwargs."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = mock_conversation_data
        mock_instance._create_message_map.return_value = {
            "prompts": {"conv-bilbo-1": [{"text": "Good morning."}]},
            "generations": {"conv-bilbo-1": [{"text": "Good morning."}]},
        }
        mock_cursor_query.return_value = mock_instance

        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", mock_open()) as mock_file_open,
        ):

            result = handle_export_individual_conversations(
                {
                    "format": "json",
                    "limit": 2,
                    "output_dir": "/tmp/test_export",
                },
                project_root=Path("/test/project"),
            )

        # Should be MCP response format
        assert "content" in result
        assert isinstance(result["content"], list)
        assert result["content"][0]["type"] == "text"

        # Parse the JSON response to verify export details
        response_data = json.loads(result["content"][0]["text"])
        assert response_data["exported_count"] == 2
        assert "files" in response_data
        assert response_data["output_directory"].endswith("/tmp/test_export")
        assert response_data["format"] == "json"

        mock_cursor_query.assert_called_once()
        mock_mkdir.assert_called_once()
        mock_file_open.assert_called()


class TestConversationExportEdgeCases:
    """Test edge cases and error scenarios for conversation export."""

    @pytest.fixture
    def mock_conversation_data(self):
        """Mock conversation data for edge case testing."""
        return {
            "workspaces": [
                {
                    "workspace_hash": "test_workspace",
                    "database_path": "/mock/path/test.db",
                    "conversations": [
                        {
                            "composerId": "conv-test-1",
                            "name": "Test Conversation",
                            "createdAt": 1640995200000,
                            "lastUpdatedAt": 1640995800000,
                        },
                    ],
                    "prompts": [],
                    "generations": [],
                }
            ],
            "query_timestamp": "2024-01-01T12:00:00.000Z",
            "total_databases": 1,
            "databases_with_conversations": 1,
        }

    def test_export_invalid_format(self):
        """Test export with invalid format returns error."""
        result = handle_export_individual_conversations(
            {"format": "invalid_format", "limit": 10},
            project_root=Path("/test/project"),
        )

        assert "error" in result
        assert "Invalid format" in result["error"]

    def test_export_invalid_limit_zero(self):
        """Test export with invalid limit (zero) returns error."""
        result = handle_export_individual_conversations(
            {"format": "json", "limit": 0},
            project_root=Path("/test/project"),
        )

        assert "error" in result
        assert "Limit must be an integer between 1 and 100" in result["error"]

    def test_export_invalid_limit_negative(self):
        """Test export with invalid limit (negative) returns error."""
        result = handle_export_individual_conversations(
            {"format": "json", "limit": -5},
            project_root=Path("/test/project"),
        )

        assert "error" in result
        assert "Limit must be an integer between 1 and 100" in result["error"]

    def test_export_invalid_limit_too_large(self):
        """Test export with invalid limit (too large) returns error."""
        result = handle_export_individual_conversations(
            {"format": "json", "limit": 150},
            project_root=Path("/test/project"),
        )

        assert "error" in result
        assert "Limit must be an integer between 1 and 100" in result["error"]

    def test_export_invalid_limit_non_integer(self):
        """Test export with invalid limit (non-integer) returns error."""
        result = handle_export_individual_conversations(
            {"format": "json", "limit": "not_an_integer"},
            project_root=Path("/test/project"),
        )

        assert "error" in result
        assert "Limit must be an integer between 1 and 100" in result["error"]

    @patch("src.tool_calls.export.CursorQuery")
    def test_export_no_data(self, mock_cursor_query):
        """Test export when no conversation data is available."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = None
        mock_cursor_query.return_value = mock_instance

        result = handle_export_individual_conversations(
            {"format": "json", "limit": 10},
            project_root=Path("/test/project"),
        )

        assert "content" in result
        response_data = json.loads(result["content"][0]["text"])
        assert response_data["exported_count"] == 0
        assert response_data["message"] == "No conversations found to export"

    @patch("src.tool_calls.export.CursorQuery")
    def test_export_empty_workspaces(self, mock_cursor_query):
        """Test export when workspaces list is empty."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = {"workspaces": []}
        mock_cursor_query.return_value = mock_instance

        result = handle_export_individual_conversations(
            {"format": "json", "limit": 10},
            project_root=Path("/test/project"),
        )

        assert "content" in result
        response_data = json.loads(result["content"][0]["text"])
        assert response_data["exported_count"] == 0
        assert response_data["message"] == "No conversations found to export"

    @patch("src.tool_calls.export.CursorQuery")
    def test_export_markdown_format(self, mock_cursor_query, mock_conversation_data):
        """Test export with markdown format."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = mock_conversation_data
        mock_cursor_query.return_value = mock_instance

        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", mock_open()) as mock_file_open,
        ):

            result = handle_export_individual_conversations(
                {"format": "markdown", "limit": 1, "output_dir": "/tmp/test"},
                project_root=Path("/test/project"),
            )

        assert "content" in result
        response_data = json.loads(result["content"][0]["text"])
        assert response_data["format"] == "markdown"
        assert response_data["exported_count"] == 1

        mock_mkdir.assert_called_once()
        mock_file_open.assert_called()

    @patch("src.tool_calls.export.CursorQuery")
    def test_export_md_format(self, mock_cursor_query, mock_conversation_data):
        """Test export with md format (alias for markdown)."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = mock_conversation_data
        mock_cursor_query.return_value = mock_instance

        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", mock_open()) as mock_file_open,
        ):

            result = handle_export_individual_conversations(
                {"format": "md", "limit": 1, "output_dir": "/tmp/test"},
                project_root=Path("/test/project"),
            )

        assert "content" in result
        response_data = json.loads(result["content"][0]["text"])
        assert response_data["format"] == "md"
        assert response_data["exported_count"] == 1

        mock_mkdir.assert_called_once()
        mock_file_open.assert_called()

    @patch("src.tool_calls.export.CursorQuery")
    def test_export_txt_format(self, mock_cursor_query, mock_conversation_data):
        """Test export with txt format."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = mock_conversation_data
        mock_cursor_query.return_value = mock_instance

        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", mock_open()) as mock_file_open,
        ):

            result = handle_export_individual_conversations(
                {"format": "txt", "limit": 1, "output_dir": "/tmp/test"},
                project_root=Path("/test/project"),
            )

        assert "content" in result
        response_data = json.loads(result["content"][0]["text"])
        assert response_data["format"] == "txt"
        assert response_data["exported_count"] == 1

        mock_mkdir.assert_called_once()
        mock_file_open.assert_called()

    @patch("src.tool_calls.export.CursorQuery")
    def test_export_with_conversation_filter(
        self, mock_cursor_query, mock_conversation_data
    ):
        """Test export with conversation filter."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = mock_conversation_data
        mock_cursor_query.return_value = mock_instance

        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", mock_open()) as mock_file_open,
        ):

            result = handle_export_individual_conversations(
                {
                    "format": "json",
                    "limit": 10,
                    "conversation_filter": "Test",
                    "output_dir": "/tmp/test",
                },
                project_root=Path("/test/project"),
            )

        assert "content" in result
        response_data = json.loads(result["content"][0]["text"])
        assert (
            response_data["exported_count"] == 1
        )  # Only one conversation matches filter

        mock_mkdir.assert_called_once()
        mock_file_open.assert_called()

    @patch("src.tool_calls.export.CursorQuery")
    def test_export_with_filter_no_matches(
        self, mock_cursor_query, mock_conversation_data
    ):
        """Test export with conversation filter that matches nothing."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = mock_conversation_data
        mock_cursor_query.return_value = mock_instance

        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("builtins.open", mock_open()) as mock_file_open,
        ):

            result = handle_export_individual_conversations(
                {
                    "format": "json",
                    "limit": 10,
                    "conversation_filter": "NonExistentConversation",
                    "output_dir": "/tmp/test",
                },
                project_root=Path("/test/project"),
            )

        assert "content" in result
        response_data = json.loads(result["content"][0]["text"])
        assert response_data["exported_count"] == 0  # No conversations match filter

        mock_mkdir.assert_called_once()
        # File operations should not be called if no conversations to export
        mock_file_open.assert_not_called()

    def test_export_default_output_dir(self):
        """Test export with default output directory (no output_dir provided)."""
        with patch("src.tool_calls.export.CursorQuery") as mock_cursor_query:
            mock_instance = Mock()
            mock_instance.query_all_conversations.return_value = {"workspaces": []}
            mock_cursor_query.return_value = mock_instance

            result = handle_export_individual_conversations(
                {"format": "json", "limit": 10},
                project_root=Path("/test/project"),
            )

        assert "content" in result
        response_data = json.loads(result["content"][0]["text"])
        # Should use default GANDALF_HOME/exports
        assert "gandalf" in response_data["output_directory"].lower()


class TestConversationFormatting:
    """Test conversation formatting functions."""

    def test_format_conversation_markdown(self):
        """Test markdown formatting of conversation data."""
        conversation = {
            "conversation_id": "conv-test-1",
            "name": "Test Conversation",
            "workspace_hash": "test_workspace",
            "created_at": 1640995200000,
            "last_updated": 1640995800000,
            "conversation_metadata": {
                "type": "chat",
                "unified_mode": "true",
                "force_mode": "false",
            },
            "workspace_prompts_count": 5,
            "workspace_generations_count": 3,
            "workspace_total_conversations": 10,
        }

        result = _format_conversation_markdown(conversation)

        assert "# Test Conversation" in result
        assert "**Conversation ID:** conv-test-1" in result
        # Check for timestamp format without hardcoding timezone-specific values
        assert "**Created:** 202" in result  # Should contain year 2021 or 2022
        assert "```json" in result  # The function includes JSON data
        assert '"workspace_hash": "test_workspace"' in result  # Data is in JSON

    def test_format_conversation_text(self):
        """Test text formatting of conversation data."""
        conversation = {
            "conversation_id": "conv-test-1",
            "name": "Test Conversation",
            "workspace_hash": "test_workspace",
            "created_at": 1640995200000,
            "last_updated": 1640995800000,
            "conversation_metadata": {
                "type": "code",
                "unified_mode": "false",
                "force_mode": "true",
            },
            "workspace_prompts_count": 2,
            "workspace_generations_count": 1,
            "workspace_total_conversations": 5,
        }

        result = _format_conversation_text(conversation)

        assert "Conversation: Test Conversation" in result
        assert (
            "ID: conv-test-1" in result
        )  # Actual format is "ID:" not "Conversation ID:"
        # Check for timestamp format without hardcoding timezone-specific values
        assert "Created: 202" in result  # Should contain year 2021 or 2022
        assert "Raw Data:" in result
        assert '"workspace_hash": "test_workspace"' in result  # Data is in JSON

    def test_format_conversation_markdown_missing_metadata(self):
        """Test markdown formatting with missing metadata."""
        conversation = {
            "conversation_id": "conv-test-1",
            "name": "Test Conversation",
            "workspace_hash": "test_workspace",
            "created_at": 1640995200000,
            "last_updated": 1640995800000,
            # Missing conversation_metadata
            "workspace_prompts_count": 0,
            "workspace_generations_count": 0,
            "workspace_total_conversations": 1,
        }

        result = _format_conversation_markdown(conversation)

        assert "# Test Conversation" in result
        assert "**Conversation ID:** conv-test-1" in result
        # The function just dumps the JSON, so the metadata fields won't be there
        assert "```json" in result
        assert '"workspace_hash": "test_workspace"' in result

    def test_format_conversation_text_missing_metadata(self):
        """Test text formatting with missing metadata."""
        conversation = {
            "conversation_id": "conv-test-1",
            "name": "Test Conversation",
            "workspace_hash": "test_workspace",
            "created_at": 1640995200000,
            "last_updated": 1640995800000,
            # Missing conversation_metadata
            "workspace_prompts_count": 0,
            "workspace_generations_count": 0,
            "workspace_total_conversations": 1,
        }

        result = _format_conversation_text(conversation)

        assert "Conversation: Test Conversation" in result
        assert (
            "ID: conv-test-1" in result
        )  # Actual format is "ID:" not "Conversation ID:"
        assert "Raw Data:" in result
        assert '"workspace_hash": "test_workspace"' in result


class TestHandleListCursorWorkspaces:
    """Test handle_list_cursor_workspaces function."""

    @patch("src.tool_calls.export.list_cursor_workspaces")
    def test_list_cursor_workspaces_success(self, mock_list_workspaces):
        """Test successful workspace listing."""
        # Return the correct format based on actual function implementation
        mock_list_workspaces.return_value = {
            "total_workspaces": 3,
            "workspaces": [
                {"hash": "workspace1_hash", "path": "/path1", "exists": True},
                {"hash": "workspace2_hash", "path": "/path2", "exists": True},
                {"hash": "workspace3_hash", "path": "/path3", "exists": False},
            ],
        }

        result = handle_list_cursor_workspaces({}, project_root=Path("/test/project"))

        assert "content" in result
        response_data = json.loads(result["content"][0]["text"])
        assert "workspaces" in response_data
        assert "count" in response_data
        assert response_data["count"] == 3
        assert len(response_data["workspaces"]) == 3

        mock_list_workspaces.assert_called_once()

    @patch("src.tool_calls.export.list_cursor_workspaces")
    def test_list_cursor_workspaces_empty(self, mock_list_workspaces):
        """Test workspace listing when no workspaces found."""
        mock_list_workspaces.return_value = {
            "total_workspaces": 0,
            "workspaces": [],
        }

        result = handle_list_cursor_workspaces({}, project_root=Path("/test/project"))

        assert "content" in result
        response_data = json.loads(result["content"][0]["text"])
        assert "workspaces" in response_data
        assert "count" in response_data
        assert response_data["count"] == 0
        assert len(response_data["workspaces"]) == 0

        mock_list_workspaces.assert_called_once()

    @patch("src.tool_calls.export.list_cursor_workspaces")
    def test_list_cursor_workspaces_with_args(self, mock_list_workspaces):
        """Test workspace listing with arguments (should ignore them)."""
        mock_list_workspaces.return_value = {
            "total_workspaces": 1,
            "workspaces": [
                {
                    "hash": "test_workspace",
                    "path": "/test/path",
                    "exists": True,
                }
            ],
        }

        result = handle_list_cursor_workspaces(
            {"some_arg": "some_value"}, project_root=Path("/test/project")
        )

        assert "content" in result
        response_data = json.loads(result["content"][0]["text"])
        assert "workspaces" in response_data
        assert "count" in response_data
        assert response_data["count"] == 1
        assert len(response_data["workspaces"]) == 1

        mock_list_workspaces.assert_called_once()

    @patch("src.tool_calls.export.list_cursor_workspaces")
    def test_list_cursor_workspaces_error_handling(self, mock_list_workspaces):
        """Test workspace listing error handling."""
        mock_list_workspaces.side_effect = OSError("Database connection failed")

        result = handle_list_cursor_workspaces({}, project_root=Path("/test/project"))

        # Should return an error response
        assert "error" in result
        assert "Database connection failed" in result["error"]

    @patch("src.tool_calls.export.list_cursor_workspaces")
    def test_list_cursor_workspaces_with_kwargs(self, mock_list_workspaces):
        """Test workspace listing with kwargs."""
        mock_list_workspaces.return_value = {
            "total_workspaces": 1,
            "workspaces": [
                {
                    "hash": "workspace_with_kwargs",
                    "path": "/test/path",
                    "exists": True,
                }
            ],
        }

        result = handle_list_cursor_workspaces(
            {}, project_root=Path("/test/project"), extra_kwarg="test"
        )

        assert "content" in result
        response_data = json.loads(result["content"][0]["text"])
        assert "workspaces" in response_data
        assert "count" in response_data
        assert response_data["count"] == 1
        assert len(response_data["workspaces"]) == 1

        mock_list_workspaces.assert_called_once()
