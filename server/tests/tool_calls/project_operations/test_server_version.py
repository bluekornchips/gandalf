"""
Tests for server version functionality.

lotr-info: Tests server version operations using Shire council meeting
timestamps and Rivendell protocol versions.
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

from src.config.core_constants import (
    GANDALF_SERVER_VERSION,
    MCP_PROTOCOL_VERSION,
)
from src.tool_calls.project_operations import handle_get_server_version


class TestGetServerVersion:
    """Test get_server_version tool functionality."""

    def test_handle_get_server_version_success(self):
        """Test successful server version retrieval."""
        mock_project_root = Path("/mnt/doom/shire-project")
        arguments = {}

        with patch("time.time", return_value=1234567890.0):
            result = handle_get_server_version(
                arguments, project_root=mock_project_root
            )

        assert "content" in result
        assert result["content"][0]["type"] == "text"

        content = json.loads(result["content"][0]["text"])
        assert content["server_version"] == GANDALF_SERVER_VERSION
        assert content["protocol_version"] == MCP_PROTOCOL_VERSION
        assert content["timestamp"] == 1234567890.0

    def test_handle_get_server_version_with_environment_variable(self):
        """Test server version retrieval with environment variable override."""
        mock_project_root = Path("/mnt/doom/rivendell-project")
        arguments = {}

        with patch.dict(os.environ, {"GANDALF_SERVER_VERSION": "2.31"}):
            # Need to reload the module to pick up the new env var
            with patch(
                "src.tool_calls.project_operations.GANDALF_SERVER_VERSION",
                "2.31",
            ):
                with patch("time.time", return_value=1234567890.0):
                    result = handle_get_server_version(
                        arguments, project_root=mock_project_root
                    )

        assert "content" in result
        content = json.loads(result["content"][0]["text"])
        assert content["server_version"] == "2.31"

    @patch(
        "src.tool_calls.project_operations.GANDALF_SERVER_VERSION",
        "test_version",
    )
    def test_handle_get_server_version_exception(self):
        """Test server version handler with exception."""
        mock_project_root = Path("/mnt/doom/gondor-project")
        with patch(
            "src.tool_calls.project_operations.time.time",
            side_effect=OSError("Sauron's corruption error"),
        ):
            arguments = {}
            result = handle_get_server_version(
                arguments, project_root=mock_project_root
            )

            assert result["isError"] is True
            assert "Error retrieving server version" in result["error"]

    def test_get_server_version_returns_expected_fields(self):
        """Test that get_server_version returns all expected fields."""
        mock_project_root = Path("/mnt/doom/minas-tirith-project")
        arguments = {}

        result = handle_get_server_version(arguments, project_root=mock_project_root)
        content = json.loads(result["content"][0]["text"])

        expected_fields = {
            "server_name",
            "server_version",
            "protocol_version",
            "timestamp",
            "capabilities",
        }
        assert set(content.keys()) == expected_fields

        assert isinstance(content["server_name"], str)
        assert isinstance(content["server_version"], str)
        assert isinstance(content["protocol_version"], str)
        assert isinstance(content["timestamp"], int | float)
        assert isinstance(content["capabilities"], dict)

    def test_get_server_version_ignores_arguments(self):
        """Test that get_server_version ignores any arguments passed to it."""
        mock_project_root = Path("/mnt/doom/hobbiton-project")

        arguments = {
            "include_stats": True,
            "random_param": "should_be_ignored",
            "another_param": 123,
        }

        result = handle_get_server_version(arguments, project_root=mock_project_root)

        assert "content" in result
        content = json.loads(result["content"][0]["text"])
        assert content["server_version"] == GANDALF_SERVER_VERSION

    def test_handle_get_server_version_value_error(self):
        """Test server version handler with ValueError."""
        mock_project_root = Path("/mnt/doom/isengard-project")

        with patch("json.dumps", side_effect=ValueError("Saruman's JSON error")):
            result = handle_get_server_version({}, project_root=mock_project_root)

            assert result["isError"] is True
            assert "Error retrieving server version" in result["error"]

    def test_handle_get_server_version_runtime_error(self):
        """Test server version handler with RuntimeError."""
        mock_project_root = Path("/mnt/doom/rohan-project")

        with patch(
            "time.time", side_effect=RuntimeError("Riders of Rohan runtime error")
        ):
            result = handle_get_server_version({}, project_root=mock_project_root)

            assert result["isError"] is True
            assert "Error retrieving server version" in result["error"]


class TestVersionEnvironmentIntegration:
    """Test version functionality with environment integration."""

    def test_version_consistency_across_environments(self):
        """Test that version remains consistent across different environments."""
        # Test default environment
        result1 = handle_get_server_version({}, project_root=Path("/mnt/doom/shire"))
        content1 = json.loads(result1["content"][0]["text"])

        # Test with mocked environment
        with patch.dict(os.environ, {"TEST_ENV": "gondor"}):
            result2 = handle_get_server_version(
                {}, project_root=Path("/mnt/doom/gondor")
            )
            content2 = json.loads(result2["content"][0]["text"])

        # Version should remain consistent
        assert content1["server_version"] == content2["server_version"]
        assert content1["protocol_version"] == content2["protocol_version"]

    def test_version_with_special_characters_in_project_path(self):
        """Test version handling with special characters in project path."""
        special_path = Path("/mnt/doom/shire's-hobbiton & bag-end")
        result = handle_get_server_version({}, project_root=special_path)

        assert "content" in result
        content = json.loads(result["content"][0]["text"])
        assert "server_version" in content
        assert "protocol_version" in content
