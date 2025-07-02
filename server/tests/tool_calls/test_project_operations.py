"""Tests for project operations functionality."""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

from src.config.constants import (
    GANDALF_SERVER_VERSION,
    MCP_PROTOCOL_VERSION,
)
from src.tool_calls.project_operations import (
    get_git_info,
    handle_get_project_info,
    handle_get_server_version,
    validate_project_root,
)


class TestGetServerVersion:
    """Test get_server_version tool functionality."""

    def test_handle_get_server_version_success(self):
        """Test successful server version retrieval."""
        mock_project_root = Path("/path/to/project")
        arguments = {}

        with patch("time.time", return_value=1234567890.0):
            result = handle_get_server_version(arguments, mock_project_root)

        assert "content" in result
        assert result["content"][0]["type"] == "text"

        content = json.loads(result["content"][0]["text"])
        assert content["server_version"] == GANDALF_SERVER_VERSION
        assert content["protocol_version"] == MCP_PROTOCOL_VERSION
        assert content["timestamp"] == 1234567890.0

    def test_handle_get_server_version_with_environment_variable(self):
        """Test server version retrieval with environment variable override."""
        mock_project_root = Path("/path/to/project")
        arguments = {}

        with patch.dict(os.environ, {"GANDALF_SERVER_VERSION": "2.0.0"}):
            # Need to reload the module to pick up the new env var
            with patch(
                "src.tool_calls.project_operations.GANDALF_SERVER_VERSION",
                "2.0.0",
            ):
                with patch("time.time", return_value=1234567890.0):
                    result = handle_get_server_version(arguments, mock_project_root)

        assert "content" in result
        content = json.loads(result["content"][0]["text"])
        assert content["server_version"] == "2.0.0"

    def test_handle_get_server_version_exception_handling(self):
        """Test error handling in get_server_version."""
        mock_project_root = Path("/path/to/project")
        arguments = {}

        with patch("time.time", side_effect=Exception("Time error")):
            result = handle_get_server_version(arguments, mock_project_root)

        assert result["isError"] is True
        assert "Error retrieving server version" in result["error"]

    def test_get_server_version_returns_expected_fields(self):
        """Test that get_server_version returns all expected fields."""
        mock_project_root = Path("/path/to/project")
        arguments = {}

        result = handle_get_server_version(arguments, mock_project_root)
        content = json.loads(result["content"][0]["text"])

        expected_fields = {"server_version", "protocol_version", "timestamp"}
        assert set(content.keys()) == expected_fields

        assert isinstance(content["server_version"], str)
        assert isinstance(content["protocol_version"], str)
        assert isinstance(content["timestamp"], (int, float))

    def test_get_server_version_ignores_arguments(self):
        """Test that get_server_version ignores any arguments passed to it."""
        mock_project_root = Path("/path/to/project")

        arguments = {
            "include_stats": True,
            "random_param": "should_be_ignored",
            "another_param": 123,
        }

        result = handle_get_server_version(arguments, mock_project_root)

        assert "content" in result
        content = json.loads(result["content"][0]["text"])
        assert content["server_version"] == GANDALF_SERVER_VERSION


class TestProjectOperationsIntegration:
    """Test integration between different project operations."""

    def test_validate_project_root_existing_directory(self):
        """Test project root validation with existing directory."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                result = validate_project_root(Path("/existing/dir"))
                assert result is True

    def test_validate_project_root_nonexistent_directory(self):
        """Test project root validation with non-existent directory."""
        with patch("pathlib.Path.exists", return_value=False):
            result = validate_project_root(Path("/nonexistent/dir"))
            assert result is False

    def test_validate_project_root_file_not_directory(self):
        """Test project root validation with file instead of directory."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=False):
                result = validate_project_root(Path("/path/to/file"))
                assert result is False

    def test_validate_project_root_permission_error(self):
        """Test project root validation with permission error."""
        with patch("pathlib.Path.exists", side_effect=PermissionError):
            result = validate_project_root(Path("/no/permission"))
            assert result is False


class TestGitInfoRetrieval:
    """Test Git information retrieval functionality."""

    def test_get_git_info_valid_repo(self):
        """Test Git info retrieval for valid repository."""
        mock_project_root = Path("/path/to/shire")

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "fellowship\n"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                # First call: git rev-parse --is-inside-work-tree
                Mock(returncode=0),
                # Second call: git branch --show-current
                mock_result,
                # Third call: git rev-parse --show-toplevel
                Mock(returncode=0, stdout="/path/to/shire\n"),
            ]

            result = get_git_info(mock_project_root)

            assert result["is_git_repo"] is True
            assert result["current_branch"] == "fellowship"
            assert result["repo_root"] == "/path/to/shire"

    def test_get_git_info_not_a_repo(self):
        """Test Git info retrieval for non-repository."""
        mock_project_root = Path("/path/to/mordor")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1)

            result = get_git_info(mock_project_root)

            assert result["is_git_repo"] is False

    def test_get_git_info_subprocess_error(self):
        """Test Git info retrieval with subprocess error."""
        mock_project_root = Path("/path/to/isengard")

        with patch("subprocess.run", side_effect=OSError("Git not found in Isengard")):
            result = get_git_info(mock_project_root)

            assert result["is_git_repo"] is False
            assert "error" in result


class TestProjectOperationsErrorHandling:
    """Test error handling in project operations."""

    def test_handle_get_project_info_invalid_include_stats(self):
        """Test get_project_info with invalid include_stats parameter."""
        mock_project_root = Path("/path/to/project")
        arguments = {"include_stats": "not_a_boolean"}

        result = handle_get_project_info(arguments, mock_project_root)

        assert result["isError"] is True
        assert "include_stats must be a boolean" in result["error"]

    def test_handle_get_project_info_path_validation_error(self):
        """Test get_project_info with path validation error."""
        mock_project_root = Path("/invalid/path")
        arguments = {"include_stats": True}

        with patch(
            "src.tool_calls.project_operations.validate_project_root"
        ) as mock_validate:
            mock_validate.return_value = False

            result = handle_get_project_info(arguments, mock_project_root)

            assert result["isError"] is True
            assert "Project root does not exist or is not accessible" in result["error"]

    def test_handle_get_project_info_general_exception(self):
        """Test get_project_info with general exception."""
        mock_project_root = Path("/path/to/project")
        arguments = {"include_stats": True}

        with patch(
            "src.tool_calls.project_operations.validate_project_root",
            side_effect=Exception("General error"),
        ):
            result = handle_get_project_info(arguments, mock_project_root)

            assert result["isError"] is True
            assert "Error retrieving project info" in result["error"]


class TestVersionEnvironmentIntegration:
    """Test version functionality with environment variable integration."""

    def test_server_version_uses_environment_variable(self):
        """Test that server version uses environment variable when set."""
        mock_project_root = Path("/path/to/project")
        arguments = {}
        test_version = "3.0.0-test"

        with patch.dict(os.environ, {"GANDALF_SERVER_VERSION": test_version}):
            with patch(
                "src.tool_calls.project_operations.GANDALF_SERVER_VERSION",
                test_version,
            ):
                result = handle_get_server_version(arguments, mock_project_root)

        assert "content" in result
        content = json.loads(result["content"][0]["text"])
        assert content["server_version"] == test_version

    def test_server_version_fallback_when_no_env_var(self):
        """Test that server version falls back to default when no env var."""
        mock_project_root = Path("/path/to/project")
        arguments = {}

        # Ensure no environment variable is set
        with patch.dict(os.environ, {}, clear=True):
            result = handle_get_server_version(arguments, mock_project_root)

        assert "content" in result
        content = json.loads(result["content"][0]["text"])
        # Should use the default fallback version
        assert content["server_version"] == GANDALF_SERVER_VERSION


class TestToolDefinitionCompliance:
    """Test that tools comply with MCP tool definition standards."""

    def test_get_server_version_tool_definition_structure(self):
        """Test that get_server_version tool definition has correct structure."""
        from src.tool_calls.project_operations import TOOL_GET_SERVER_VERSION

        # Check required fields
        assert "name" in TOOL_GET_SERVER_VERSION
        assert "description" in TOOL_GET_SERVER_VERSION
        assert "inputSchema" in TOOL_GET_SERVER_VERSION
        assert "annotations" in TOOL_GET_SERVER_VERSION

        # Check specific values
        assert TOOL_GET_SERVER_VERSION["name"] == "get_server_version"
        assert isinstance(TOOL_GET_SERVER_VERSION["description"], str)

        # Check input schema structure
        schema = TOOL_GET_SERVER_VERSION["inputSchema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
        assert schema["required"] == []  # No required parameters

        # Check annotations
        annotations = TOOL_GET_SERVER_VERSION["annotations"]
        assert annotations["readOnlyHint"] is True
        assert annotations["destructiveHint"] is False
        assert annotations["idempotentHint"] is True

    def test_tool_handlers_registration(self):
        """Test that all tool handlers are properly registered."""
        from src.tool_calls.project_operations import PROJECT_TOOL_HANDLERS

        assert "get_server_version" in PROJECT_TOOL_HANDLERS
        assert callable(PROJECT_TOOL_HANDLERS["get_server_version"])
        assert PROJECT_TOOL_HANDLERS["get_server_version"] == handle_get_server_version

    def test_tool_definitions_registration(self):
        """Test that all tool definitions are properly registered."""
        from src.tool_calls.project_operations import (
            PROJECT_TOOL_DEFINITIONS,
            TOOL_GET_SERVER_VERSION,
        )

        assert TOOL_GET_SERVER_VERSION in PROJECT_TOOL_DEFINITIONS

        # Find the get_server_version tool
        version_tool = None
        for tool in PROJECT_TOOL_DEFINITIONS:
            if tool["name"] == "get_server_version":
                version_tool = tool
                break

        assert version_tool is not None
        assert version_tool["name"] == "get_server_version"


class TestProjectOperations:
    """Test project operations functionality."""

    def test_get_project_info_basic(self):
        """Test basic project info retrieval."""
        with patch("src.tool_calls.project_operations.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.is_dir.return_value = True
