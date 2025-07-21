"""
Tests for src.utils.conversation_export.

Comprehensive test coverage for conversation export utility functions.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.utils.conversation_export import (
    export_conversations_simple,
    list_workspaces,
)


class TestConversationExportUtils:
    """Test conversation export utility functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_conversation_data = {
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
                },
                {
                    "workspace_hash": "gondor456minas",
                    "database_path": "/mock/path/minas_tirith.db",
                    "conversations": [
                        {
                            "composerId": "conv-aragorn-1",
                            "name": "Return of the King",
                            "createdAt": 1640995400000,
                            "lastUpdatedAt": 1640996000000,
                        },
                    ],
                },
            ],
            "query_timestamp": "2024-01-01T12:00:00.000Z",
            "total_databases": 2,
            "databases_with_conversations": 2,
        }

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("src.utils.conversation_export.CursorQuery")
    def test_export_conversations_simple_json_success(self, mock_cursor_query):
        """Test successful JSON export."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = self.mock_conversation_data
        mock_instance.export_to_file = Mock()
        mock_cursor_query.return_value = mock_instance

        output_path = self.temp_dir / "test_export.json"

        result = export_conversations_simple(
            output_path=str(output_path), format_type="json", silent=True
        )

        assert result is True
        mock_cursor_query.assert_called_once_with(silent=True)
        mock_instance.query_all_conversations.assert_called_once()
        mock_instance.export_to_file.assert_called_once_with(
            self.mock_conversation_data, output_path, "json"
        )

    @patch("src.utils.conversation_export.CursorQuery")
    def test_export_conversations_simple_markdown_success(self, mock_cursor_query):
        """Test successful markdown export."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = self.mock_conversation_data
        mock_instance.export_to_file = Mock()
        mock_cursor_query.return_value = mock_instance

        output_path = self.temp_dir / "test_export.md"

        result = export_conversations_simple(
            output_path=output_path, format_type="markdown", silent=False
        )

        assert result is True
        mock_cursor_query.assert_called_once_with(silent=False)
        mock_instance.export_to_file.assert_called_once_with(
            self.mock_conversation_data, output_path, "markdown"
        )

    @patch("src.utils.conversation_export.CursorQuery")
    def test_export_conversations_simple_cursor_format(self, mock_cursor_query):
        """Test cursor format export."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = self.mock_conversation_data
        mock_instance.export_to_file = Mock()
        mock_cursor_query.return_value = mock_instance

        output_path = self.temp_dir / "test_export.cursor"

        result = export_conversations_simple(
            output_path=output_path, format_type="cursor", silent=True
        )

        assert result is True
        mock_instance.export_to_file.assert_called_once_with(
            self.mock_conversation_data, output_path, "cursor"
        )

    def test_export_conversations_simple_invalid_format(self):
        """Test export with invalid format raises ValueError."""
        output_path = self.temp_dir / "test_export.txt"

        with pytest.raises(
            ValueError,
            match="format_type must be one of: json, markdown, cursor",
        ):
            export_conversations_simple(
                output_path=output_path,
                format_type="invalid_format",
                silent=True,
            )

    @patch("src.utils.conversation_export.CursorQuery")
    def test_export_conversations_simple_oserror(self, mock_cursor_query):
        """Test export handles OSError gracefully."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.side_effect = OSError("File not found")
        mock_cursor_query.return_value = mock_instance

        output_path = self.temp_dir / "test_export.json"

        result = export_conversations_simple(
            output_path=output_path, format_type="json", silent=True
        )

        assert result is False

    @patch("src.utils.conversation_export.CursorQuery")
    def test_export_conversations_simple_ioerror(self, mock_cursor_query):
        """Test export handles IOError gracefully."""
        mock_instance = Mock()
        mock_instance.export_to_file.side_effect = IOError("Permission denied")
        mock_instance.query_all_conversations.return_value = self.mock_conversation_data
        mock_cursor_query.return_value = mock_instance

        output_path = self.temp_dir / "test_export.json"

        result = export_conversations_simple(
            output_path=output_path, format_type="json", silent=True
        )

        assert result is False

    @patch("src.utils.conversation_export.CursorQuery")
    def test_export_conversations_simple_valueerror(self, mock_cursor_query):
        """Test export handles ValueError gracefully."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.side_effect = ValueError("Invalid data")
        mock_cursor_query.return_value = mock_instance

        output_path = self.temp_dir / "test_export.json"

        result = export_conversations_simple(
            output_path=output_path, format_type="json", silent=True
        )

        assert result is False

    @patch("src.utils.conversation_export.CursorQuery")
    def test_export_conversations_simple_typeerror(self, mock_cursor_query):
        """Test export handles TypeError gracefully."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.side_effect = TypeError("Type mismatch")
        mock_cursor_query.return_value = mock_instance

        output_path = self.temp_dir / "test_export.json"

        result = export_conversations_simple(
            output_path=output_path, format_type="json", silent=True
        )

        assert result is False

    @patch("src.utils.conversation_export.CursorQuery")
    def test_export_conversations_simple_keyerror(self, mock_cursor_query):
        """Test export handles KeyError gracefully."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.side_effect = KeyError("Missing key")
        mock_cursor_query.return_value = mock_instance

        output_path = self.temp_dir / "test_export.json"

        result = export_conversations_simple(
            output_path=output_path, format_type="json", silent=True
        )

        assert result is False

    @patch("src.utils.conversation_export.CursorQuery")
    @patch("src.utils.conversation_export.log_info")
    def test_export_conversations_simple_verbose_output(
        self, mock_log_info, mock_cursor_query
    ):
        """Test export with verbose output (silent=False)."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = self.mock_conversation_data
        mock_instance.export_to_file = Mock()
        mock_cursor_query.return_value = mock_instance

        output_path = self.temp_dir / "test_export.json"

        result = export_conversations_simple(
            output_path=output_path, format_type="json", silent=False
        )

        assert result is True
        mock_log_info.assert_called()
        log_call_args = str(mock_log_info.call_args)
        assert "Exported" in log_call_args
        assert "conversations" in log_call_args

    @patch("src.utils.conversation_export.CursorQuery")
    @patch("src.utils.conversation_export.log_error")
    def test_export_conversations_simple_error_verbose(
        self, mock_log_error, mock_cursor_query
    ):
        """Test export error with verbose output (silent=False)."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.side_effect = OSError("Test error")
        mock_cursor_query.return_value = mock_instance

        output_path = self.temp_dir / "test_export.json"

        result = export_conversations_simple(
            output_path=output_path, format_type="json", silent=False
        )

        assert result is False
        mock_log_error.assert_called()
        log_call_args = str(mock_log_error.call_args)
        assert "Export failed" in log_call_args

    @patch("src.utils.conversation_export.CursorQuery")
    def test_list_workspaces_success(self, mock_cursor_query):
        """Test successful workspace listing."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = self.mock_conversation_data
        mock_cursor_query.return_value = mock_instance

        result = list_workspaces(silent=True)

        assert isinstance(result, list)
        assert len(result) == 2
        assert "shire123baggins" in result
        assert "gondor456minas" in result
        mock_cursor_query.assert_called_once_with(silent=True)

    @patch("src.utils.conversation_export.CursorQuery")
    def test_list_workspaces_empty(self, mock_cursor_query):
        """Test workspace listing with no workspaces."""
        empty_data = {
            "workspaces": [],
            "query_timestamp": "2024-01-01T12:00:00.000Z",
            "total_databases": 0,
            "databases_with_conversations": 0,
        }

        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = empty_data
        mock_cursor_query.return_value = mock_instance

        result = list_workspaces(silent=True)

        assert isinstance(result, list)
        assert len(result) == 0

    @patch("src.utils.conversation_export.CursorQuery")
    def test_list_workspaces_missing_hash(self, mock_cursor_query):
        """Test workspace listing with missing workspace_hash."""
        data_missing_hash = {
            "workspaces": [
                {
                    "database_path": "/mock/path/hobbiton.db",
                    "conversations": [],
                },
                {
                    "workspace_hash": "",  # Empty hash
                    "database_path": "/mock/path/minas_tirith.db",
                    "conversations": [],
                },
                {
                    "workspace_hash": "valid_hash",
                    "database_path": "/mock/path/rohan.db",
                    "conversations": [],
                },
            ],
            "query_timestamp": "2024-01-01T12:00:00.000Z",
            "total_databases": 3,
            "databases_with_conversations": 3,
        }

        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = data_missing_hash
        mock_cursor_query.return_value = mock_instance

        result = list_workspaces(silent=True)

        assert isinstance(result, list)
        assert len(result) == 1  # Only the valid hash
        assert "valid_hash" in result

    @patch("src.utils.conversation_export.CursorQuery")
    def test_list_workspaces_oserror(self, mock_cursor_query):
        """Test workspace listing handles OSError gracefully."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.side_effect = OSError("Database error")
        mock_cursor_query.return_value = mock_instance

        result = list_workspaces(silent=True)

        assert isinstance(result, list)
        assert len(result) == 0

    @patch("src.utils.conversation_export.CursorQuery")
    def test_list_workspaces_ioerror(self, mock_cursor_query):
        """Test workspace listing handles IOError gracefully."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.side_effect = IOError("IO error")
        mock_cursor_query.return_value = mock_instance

        result = list_workspaces(silent=True)

        assert isinstance(result, list)
        assert len(result) == 0

    @patch("src.utils.conversation_export.CursorQuery")
    def test_list_workspaces_valueerror(self, mock_cursor_query):
        """Test workspace listing handles ValueError gracefully."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.side_effect = ValueError("Value error")
        mock_cursor_query.return_value = mock_instance

        result = list_workspaces(silent=True)

        assert isinstance(result, list)
        assert len(result) == 0

    @patch("src.utils.conversation_export.CursorQuery")
    def test_list_workspaces_typeerror(self, mock_cursor_query):
        """Test workspace listing handles TypeError gracefully."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.side_effect = TypeError("Type error")
        mock_cursor_query.return_value = mock_instance

        result = list_workspaces(silent=True)

        assert isinstance(result, list)
        assert len(result) == 0

    @patch("src.utils.conversation_export.CursorQuery")
    def test_list_workspaces_keyerror(self, mock_cursor_query):
        """Test workspace listing handles KeyError gracefully."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.side_effect = KeyError("Key error")
        mock_cursor_query.return_value = mock_instance

        result = list_workspaces(silent=True)

        assert isinstance(result, list)
        assert len(result) == 0

    @patch("src.utils.conversation_export.CursorQuery")
    @patch("src.utils.conversation_export.log_info")
    def test_list_workspaces_verbose_output(self, mock_log_info, mock_cursor_query):
        """Test workspace listing with verbose output (silent=False)."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.return_value = self.mock_conversation_data
        mock_cursor_query.return_value = mock_instance

        result = list_workspaces(silent=False)

        assert isinstance(result, list)
        assert len(result) == 2
        # Should log success message
        mock_log_info.assert_called()
        log_call_args = str(mock_log_info.call_args)
        assert "Found" in log_call_args
        assert "workspaces" in log_call_args

    @patch("src.utils.conversation_export.CursorQuery")
    @patch("src.utils.conversation_export.log_error")
    def test_list_workspaces_error_verbose(self, mock_log_error, mock_cursor_query):
        """Test workspace listing error with verbose output (silent=False)."""
        mock_instance = Mock()
        mock_instance.query_all_conversations.side_effect = OSError("Test error")
        mock_cursor_query.return_value = mock_instance

        result = list_workspaces(silent=False)

        assert isinstance(result, list)
        assert len(result) == 0
        # Should log error message
        mock_log_error.assert_called()
        log_call_args = str(mock_log_error.call_args)
        assert "Failed to list workspaces" in log_call_args
