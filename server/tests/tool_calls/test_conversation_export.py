"""
Tests for conversation export functionality.

Tests conversation export with comprehensive coverage of export functionality.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.tool_calls.export import (
    format_timestamp,
    handle_export_individual_conversations,
)


class TestHandleExportIndividualConversations:
    """Test handle_export_individual_conversations function."""

    def test_handle_export_basic(self):
        """Test basic export functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            arguments = {
                "format": "json",
                "output_dir": str(temp_dir),
                "limit": 5,
            }

            # Mock the query tool
            with patch("src.tool_calls.export.CursorQuery") as mock_cursor:
                mock_cursor.return_value.query_all_conversations.return_value = {
                    "workspaces": [
                        {
                            "workspace_hash": "test123",
                            "conversations": [
                                {
                                    "composerId": "conv1",
                                    "name": "Test Conversation",
                                    "createdAt": 1640995200000,
                                    "lastUpdatedAt": 1640995200000,
                                    "type": "chat",
                                    "unifiedMode": "enabled",
                                    "forceMode": "disabled",
                                }
                            ],
                            "prompts": [],
                            "generations": [],
                        }
                    ]
                }

                result = handle_export_individual_conversations(arguments, project_root)

                # Updated: check for new response format with content field
                assert "content" in result
                content_text = result["content"][0]["text"]
                exported_data = json.loads(content_text)
                assert exported_data["exported_count"] == 1
                assert len(exported_data["files"]) == 1

    def test_handle_export_with_all_arguments(self):
        """Test export with all arguments specified."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            arguments = {
                "format": "markdown",
                "output_dir": str(temp_dir),
                "limit": 10,
                "conversation_filter": "Test",
            }

            with patch("src.tool_calls.export.CursorQuery") as mock_cursor:
                mock_cursor.return_value.query_all_conversations.return_value = {
                    "workspaces": [
                        {
                            "workspace_hash": "test123",
                            "conversations": [
                                {
                                    "composerId": "conv1",
                                    "name": "Test Conversation",
                                    "createdAt": 1640995200000,
                                    "lastUpdatedAt": 1640995200000,
                                    "type": "chat",
                                    "unifiedMode": "enabled",
                                    "forceMode": "disabled",
                                }
                            ],
                            "prompts": [],
                            "generations": [],
                        }
                    ]
                }

                result = handle_export_individual_conversations(arguments, project_root)

                # Updated: check for new response format with content field
                assert "content" in result
                content_text = result["content"][0]["text"]
                exported_data = json.loads(content_text)
                assert exported_data["exported_count"] == 1
                assert len(exported_data["files"]) == 1
                assert exported_data["format"] == "markdown"

    def test_handle_export_error(self):
        """Test export error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            arguments = {
                "format": "json",
                "output_dir": "/nonexistent/path",
                "limit": 5,
            }

            with patch("src.tool_calls.export.CursorQuery") as mock_cursor:
                mock_cursor.return_value.query_all_conversations.return_value = {
                    "workspaces": [
                        {
                            "workspace_hash": "test123",
                            "conversations": [
                                {
                                    "composerId": "conv1",
                                    "name": "Test Conversation",
                                    "createdAt": 1640995200000,
                                    "lastUpdatedAt": 1640995200000,
                                    "type": "chat",
                                    "unifiedMode": "enabled",
                                    "forceMode": "disabled",
                                }
                            ],
                            "prompts": [],
                            "generations": [],
                        }
                    ]
                }

                result = handle_export_individual_conversations(arguments, project_root)

                # Updated: check for error response format
                assert "error" in result
                assert "Export failed" in result["error"]

    def test_handle_export_invalid_limit(self):
        """Test export with invalid limit."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            arguments = {
                "format": "json",
                "output_dir": str(temp_dir),
                "limit": "invalid",
            }

            result = handle_export_individual_conversations(arguments, project_root)

            assert result.get("isError") is True
            assert "Limit must be an integer between 1 and 100" in result["error"]

    def test_handle_export_missing_format(self):
        """Test export with missing format (should use default)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            arguments = {
                "output_dir": str(temp_dir),
                "limit": 5,
            }

            with patch("src.tool_calls.export.CursorQuery") as mock_cursor:
                mock_cursor.return_value.query_all_conversations.return_value = {
                    "workspaces": []
                }

                result = handle_export_individual_conversations(arguments, project_root)

                # Updated: check for new response format with content field
                assert "content" in result
                content_text = result["content"][0]["text"]
                exported_data = json.loads(content_text)
                assert exported_data["exported_count"] == 0
                assert exported_data["format"] == "json"  # default format


class TestFormatTimestamp:
    """Test timestamp formatting functionality."""

    def test_format_timestamp_basic(self):
        """Test basic timestamp formatting."""
        timestamp = 1640995200000  # 2022-01-01 00:00:00 UTC
        result = format_timestamp(timestamp)
        assert len(result) == 15  # YYYYMMDD_HHMMSS format
        # Updated: Use more flexible assertion for timezone differences
        assert result.startswith("202112") or result.startswith("202201")

    def test_format_timestamp_none(self):
        """Test timestamp formatting with None value."""
        result = format_timestamp(None)
        assert len(result) == 15  # YYYYMMDD_HHMMSS format
        # Should use current time, so just check format
        assert "_" in result

    def test_format_timestamp_seconds(self):
        """Test timestamp formatting with seconds (not milliseconds)."""
        timestamp = 1640995200  # 2022-01-01 00:00:00 UTC in seconds
        result = format_timestamp(timestamp)
        assert len(result) == 15  # YYYYMMDD_HHMMSS format
        # Updated: Use more flexible assertion for timezone differences
        assert result.startswith("202112") or result.startswith("202201")


class TestSanitizeFilename:
    """Test filename sanitization functionality."""

    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        from src.tool_calls.export import sanitize_filename

        result = sanitize_filename("Test Conversation")
        # Spaces are NOT replaced
        assert result == "Test Conversation"

    def test_sanitize_filename_special_chars(self):
        """Test filename sanitization with special characters."""
        from src.tool_calls.export import sanitize_filename

        result = sanitize_filename("Test<>:Conversation")
        # Special chars are replaced
        assert result == "Test___Conversation"

    def test_sanitize_filename_empty(self):
        """Test filename sanitization with empty string."""
        from src.tool_calls.export import sanitize_filename

        result = sanitize_filename("")
        # Correct default name
        assert result == "unnamed_conversation"
