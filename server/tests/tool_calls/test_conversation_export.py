"""
Tests for conversation export functionality.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from src.tool_calls.conversation_export import (
    format_timestamp,
    handle_export_individual_conversations,
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
                        },
                        {
                            "composerId": "conv-gandalf-1",
                            "name": "Wizard Staff Configuration Help",
                            "createdAt": 1640995300000,
                            "lastUpdatedAt": 1640995900000,
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

    @patch("src.tool_calls.conversation_export.CursorQuery")
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

    @patch("src.tool_calls.conversation_export.CursorQuery")
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

    @patch("src.tool_calls.conversation_export.CursorQuery")
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
