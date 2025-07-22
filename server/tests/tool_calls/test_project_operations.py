"""Tests for project operations functionality."""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.config.constants.server_config import (
    GANDALF_SERVER_VERSION,
    MCP_PROTOCOL_VERSION,
)
from src.tool_calls.project_operations import (
    PROJECT_TOOL_DEFINITIONS,
    PROJECT_TOOL_HANDLERS,
    TOOL_GET_PROJECT_INFO,
    TOOL_GET_SERVER_VERSION,
    _create_basic_project_info,
    _get_file_statistics,
    _get_file_stats_fast,
    _get_file_stats_with_cache_optimization,
    get_git_info,
    get_project_info,
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
        mock_project_root = Path("/path/to/project")
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
        mock_project_root = Path("/path/to/project")
        with patch(
            "src.tool_calls.project_operations.time.time",
            side_effect=OSError("Test error"),
        ):
            arguments = {}
            result = handle_get_server_version(
                arguments, project_root=mock_project_root
            )

            assert result["isError"] is True
            assert "Error retrieving server version" in result["error"]

    def test_get_server_version_returns_expected_fields(self):
        """Test that get_server_version returns all expected fields."""
        mock_project_root = Path("/path/to/project")
        arguments = {}

        result = handle_get_server_version(arguments, project_root=mock_project_root)
        content = json.loads(result["content"][0]["text"])

        expected_fields = {"server_version", "protocol_version", "timestamp"}
        assert set(content.keys()) == expected_fields

        assert isinstance(content["server_version"], str)
        assert isinstance(content["protocol_version"], str)
        assert isinstance(content["timestamp"], int | float)

    def test_get_server_version_ignores_arguments(self):
        """Test that get_server_version ignores any arguments passed to it."""
        mock_project_root = Path("/path/to/project")

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
        mock_project_root = Path("/path/to/project")

        with patch("json.dumps", side_effect=ValueError("JSON error")):
            result = handle_get_server_version({}, project_root=mock_project_root)

            assert result["isError"] is True
            assert "Error retrieving server version" in result["error"]

    def test_handle_get_server_version_runtime_error(self):
        """Test server version handler with RuntimeError."""
        mock_project_root = Path("/path/to/project")

        with patch("time.time", side_effect=RuntimeError("Runtime error")):
            result = handle_get_server_version({}, project_root=mock_project_root)

            assert result["isError"] is True
            assert "Error retrieving server version" in result["error"]


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

    def test_validate_project_root_os_error(self):
        """Test project root validation with OSError."""
        with patch("pathlib.Path.exists", side_effect=OSError("OS error")):
            result = validate_project_root(Path("/os/error"))
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

    def test_get_git_info_timeout_error(self):
        """Test Git info retrieval with timeout error."""
        mock_project_root = Path("/path/to/timeout")

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 5)):
            result = get_git_info(mock_project_root)

            assert result["is_git_repo"] is False
            assert "error" in result

    def test_get_git_info_subprocess_error_on_branch(self):
        """Test Git info retrieval with error getting branch."""
        mock_project_root = Path("/path/to/shire")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                # First call: git rev-parse --is-inside-work-tree (success)
                Mock(returncode=0),
                # Second call: git branch --show-current (error)
                subprocess.SubprocessError("Branch error"),
                # Third call: git rev-parse --show-toplevel (success)
                Mock(returncode=0, stdout="/path/to/shire\n"),
            ]

            result = get_git_info(mock_project_root)

            assert result["is_git_repo"] is True
            assert "current_branch" not in result
            assert result["repo_root"] == "/path/to/shire"

    def test_get_git_info_subprocess_error_on_toplevel(self):
        """Test Git info retrieval with error getting toplevel."""
        mock_project_root = Path("/path/to/shire")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                # First call: git rev-parse --is-inside-work-tree (success)
                Mock(returncode=0),
                # Second call: git branch --show-current (success)
                Mock(returncode=0, stdout="fellowship\n"),
                # Third call: git rev-parse --show-toplevel (error)
                subprocess.SubprocessError("Toplevel error"),
            ]

            result = get_git_info(mock_project_root)

            assert result["is_git_repo"] is True
            assert result["current_branch"] == "fellowship"
            assert "repo_root" not in result

    def test_get_git_info_branch_command_failure(self):
        """Test Git info retrieval when branch command fails."""
        mock_project_root = Path("/path/to/shire")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                # First call: git rev-parse --is-inside-work-tree (success)
                Mock(returncode=0),
                # Second call: git branch --show-current (non-zero return)
                Mock(returncode=1, stdout=""),
                # Third call: git rev-parse --show-toplevel (success)
                Mock(returncode=0, stdout="/path/to/shire\n"),
            ]

            result = get_git_info(mock_project_root)

            assert result["is_git_repo"] is True
            assert "current_branch" not in result
            assert result["repo_root"] == "/path/to/shire"

    def test_get_git_info_toplevel_command_failure(self):
        """Test Git info retrieval when toplevel command fails."""
        mock_project_root = Path("/path/to/shire")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                # First call: git rev-parse --is-inside-work-tree (success)
                Mock(returncode=0),
                # Second call: git branch --show-current (success)
                Mock(returncode=0, stdout="fellowship\n"),
                # Third call: git rev-parse --show-toplevel (non-zero return)
                Mock(returncode=1, stdout=""),
            ]

            result = get_git_info(mock_project_root)

            assert result["is_git_repo"] is True
            assert result["current_branch"] == "fellowship"
            assert "repo_root" not in result


class TestFileStatistics:
    """Test file statistics functionality."""

    def test_get_file_stats_fast_success(self):
        """Test _get_file_stats_fast with successful find commands."""
        mock_project_root = Path("/path/to/shire")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                # First call: find files
                Mock(returncode=0, stdout="file1.py\nfile2.js\nfile3.md\n"),
                # Second call: find directories
                Mock(
                    returncode=0,
                    stdout="/path/to/shire\n/path/to/shire/dir1\n/path/to/shire/dir2\n",
                ),
            ]

            result = _get_file_stats_fast(mock_project_root)

            assert result["total_files"] == 3
            assert result["total_directories"] == 2  # Excluding root
            assert result["method"] == "find_command"

    def test_get_file_stats_fast_command_failure(self):
        """Test _get_file_stats_fast with find command failure."""
        mock_project_root = Path("/path/to/mordor")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                # First call: find files (failure)
                Mock(returncode=1, stdout=""),
                # Second call: find directories (success)
                Mock(returncode=0, stdout="/path/to/mordor\n"),
            ]

            result = _get_file_stats_fast(mock_project_root)

            assert result["total_files"] == 0
            assert result["total_directories"] == 0
            assert result["method"] == "find_failed"

    def test_get_file_stats_fast_subprocess_error(self):
        """Test _get_file_stats_fast with subprocess error."""
        mock_project_root = Path("/path/to/isengard")

        with patch(
            "subprocess.run",
            side_effect=subprocess.SubprocessError("Find error"),
        ):
            result = _get_file_stats_fast(mock_project_root)

            assert result["total_files"] == 0
            assert result["total_directories"] == 0
            assert result["method"] == "find_error"

    def test_get_file_stats_fast_timeout_error(self):
        """Test _get_file_stats_fast with timeout error."""
        mock_project_root = Path("/path/to/timeout")

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("find", 5)):
            result = _get_file_stats_fast(mock_project_root)

            assert result["total_files"] == 0
            assert result["total_directories"] == 0
            assert result["method"] == "find_error"

    def test_get_file_stats_fast_os_error(self):
        """Test _get_file_stats_fast with OS error."""
        mock_project_root = Path("/path/to/error")

        with patch("subprocess.run", side_effect=OSError("OS error")):
            result = _get_file_stats_fast(mock_project_root)

            assert result["total_files"] == 0
            assert result["total_directories"] == 0
            assert result["method"] == "find_error"

    def test_get_file_stats_fast_empty_output(self):
        """Test _get_file_stats_fast with empty find output."""
        mock_project_root = Path("/path/to/empty")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                # First call: find files (empty)
                Mock(returncode=0, stdout=""),
                # Second call: find directories (only root)
                Mock(returncode=0, stdout="/path/to/empty\n"),
            ]

            result = _get_file_stats_fast(mock_project_root)

            assert result["total_files"] == 0
            assert result["total_directories"] == 0  # Excluding root
            assert result["method"] == "find_command"

    def test_get_file_stats_with_cache_optimization_success(self):
        """Test _get_file_stats_with_cache_optimization with cached files."""
        mock_project_root = Path("/path/to/shire")
        mock_files = ["file1.py", "file2.js", "file3.md"]

        with patch(
            "src.tool_calls.project_operations.get_files_list",
            return_value=mock_files,
        ):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(
                    returncode=0,
                    stdout="/path/to/shire\n/path/to/shire/dir1\n/path/to/shire/dir2\n",
                )

                result = _get_file_stats_with_cache_optimization(mock_project_root)

                assert result["total_files"] == 3
                assert result["total_directories"] == 2  # Excluding root
                assert result["method"] == "cached_optimized"

    def test_get_file_stats_with_cache_optimization_no_cache(self):
        """Test _get_file_stats_with_cache_optimization without cached files."""
        mock_project_root = Path("/path/to/shire")

        with patch("src.tool_calls.project_operations.get_files_list", return_value=[]):
            with patch(
                "src.tool_calls.project_operations._get_file_stats_fast"
            ) as mock_fast:
                mock_fast.return_value = {
                    "total_files": 5,
                    "total_directories": 3,
                    "method": "find_command",
                }

                result = _get_file_stats_with_cache_optimization(mock_project_root)

                assert result["total_files"] == 5
                assert result["total_directories"] == 3
                assert result["method"] == "find_command"
                mock_fast.assert_called_once_with(mock_project_root)

    def test_get_file_stats_with_cache_optimization_cache_error(self):
        """Test _get_file_stats_with_cache_optimization with cache error."""
        mock_project_root = Path("/path/to/shire")

        with patch(
            "src.tool_calls.project_operations.get_files_list",
            side_effect=ValueError("Cache error"),
        ):
            with patch(
                "src.tool_calls.project_operations._get_file_stats_fast"
            ) as mock_fast:
                mock_fast.return_value = {
                    "total_files": 5,
                    "total_directories": 3,
                    "method": "find_command",
                }

                result = _get_file_stats_with_cache_optimization(mock_project_root)

                assert result["total_files"] == 5
                assert result["total_directories"] == 3
                assert result["method"] == "find_command"
                mock_fast.assert_called_once_with(mock_project_root)

    def test_get_file_stats_with_cache_optimization_subprocess_error(self):
        """Test _get_file_stats_with_cache_optimization with subprocess error."""
        mock_project_root = Path("/path/to/shire")
        mock_files = ["file1.py", "file2.js"]

        with patch(
            "src.tool_calls.project_operations.get_files_list",
            return_value=mock_files,
        ):
            with patch(
                "subprocess.run",
                side_effect=subprocess.SubprocessError("Error"),
            ):
                with patch(
                    "src.tool_calls.project_operations._get_file_stats_fast"
                ) as mock_fast:
                    mock_fast.return_value = {
                        "total_files": 0,
                        "total_directories": 0,
                        "method": "find_error",
                    }

                    result = _get_file_stats_with_cache_optimization(mock_project_root)

                    assert result["total_files"] == 0
                    assert result["total_directories"] == 0
                    assert result["method"] == "find_error"

    def test_get_file_statistics_path_not_found(self):
        """Test _get_file_statistics with non-existent path."""
        mock_project_root = Path("/nonexistent/path")

        with patch("pathlib.Path.exists", return_value=False):
            result = _get_file_statistics(mock_project_root)

            assert result["total_files"] == 0
            assert result["total_directories"] == 0
            assert result["method"] == "path_not_found"

    def test_get_file_statistics_cache_optimization_success(self):
        """Test _get_file_statistics using cache optimization."""
        mock_project_root = Path("/path/to/shire")

        with patch("pathlib.Path.exists", return_value=True):
            with patch(
                "src.tool_calls.project_operations._get_file_stats_with_cache_optimization"
            ) as mock_cache:
                mock_cache.return_value = {
                    "total_files": 10,
                    "total_directories": 5,
                    "method": "cached_optimized",
                }

                result = _get_file_statistics(mock_project_root)

                assert result["total_files"] == 10
                assert result["total_directories"] == 5
                assert result["method"] == "cached_optimized"
                mock_cache.assert_called_once_with(mock_project_root)

    def test_get_file_statistics_fallback_to_fast(self):
        """Test _get_file_statistics fallback to fast method."""
        mock_project_root = Path("/path/to/shire")

        with patch("pathlib.Path.exists", return_value=True):
            with patch(
                "src.tool_calls.project_operations._get_file_stats_with_cache_optimization",
                side_effect=OSError("Cache error"),
            ):
                with patch(
                    "src.tool_calls.project_operations._get_file_stats_fast"
                ) as mock_fast:
                    mock_fast.return_value = {
                        "total_files": 8,
                        "total_directories": 4,
                        "method": "find_command",
                    }

                    result = _get_file_statistics(mock_project_root)

                    assert result["total_files"] == 8
                    assert result["total_directories"] == 4
                    assert result["method"] == "find_command"
                    mock_fast.assert_called_once_with(mock_project_root)


class TestCreateBasicProjectInfo:
    """Test basic project info creation."""

    def test_create_basic_project_info_normal_name(self):
        """Test _create_basic_project_info with normal project name."""
        mock_project_root = Path("/path/to/shire")

        with patch(
            "src.tool_calls.project_operations.validate_project_root",
            return_value=True,
        ):
            with patch(
                "src.tool_calls.project_operations.AccessValidator.sanitize_project_name",
                return_value="shire",
            ):
                with patch("time.time", return_value=1234567890.0):
                    result = _create_basic_project_info(mock_project_root)

                    assert result["project_root"] == "/path/to/shire"
                    assert result["project_name"] == "shire"
                    assert result["timestamp"] == 1234567890.0
                    assert result["valid_path"] is True
                    assert result["sanitized"] is False

    def test_create_basic_project_info_sanitized_name(self):
        """Test _create_basic_project_info with name that needs sanitization."""
        mock_project_root = Path("/path/to/shire-with-special-chars!")

        with patch(
            "src.tool_calls.project_operations.validate_project_root",
            return_value=True,
        ):
            with patch(
                "src.tool_calls.project_operations.AccessValidator.sanitize_project_name",
                return_value="shire_with_special_chars",
            ):
                with patch("time.time", return_value=1234567890.0):
                    result = _create_basic_project_info(mock_project_root)

                    assert (
                        result["project_root"] == "/path/to/shire-with-special-chars!"
                    )
                    assert result["project_name"] == "shire_with_special_chars"
                    assert result["raw_project_name"] == "shire-with-special-chars!"
                    assert result["timestamp"] == 1234567890.0
                    assert result["valid_path"] is True
                    assert result["sanitized"] is True

    def test_create_basic_project_info_invalid_path(self):
        """Test _create_basic_project_info with invalid path."""
        mock_project_root = Path("/invalid/path")

        with patch(
            "src.tool_calls.project_operations.validate_project_root",
            return_value=False,
        ):
            with patch(
                "src.tool_calls.project_operations.AccessValidator.sanitize_project_name",
                return_value="path",
            ):
                with patch("time.time", return_value=1234567890.0):
                    result = _create_basic_project_info(mock_project_root)

                    assert result["project_root"] == "/invalid/path"
                    assert result["project_name"] == "path"
                    assert result["timestamp"] == 1234567890.0
                    assert result["valid_path"] is False
                    assert result["sanitized"] is False


class TestGetProjectInfo:
    """Test complete project info retrieval."""

    def test_get_project_info_complete(self):
        """Test get_project_info with all components."""
        mock_project_root = Path("/path/to/shire")

        mock_basic_info = {
            "project_root": "/path/to/shire",
            "project_name": "shire",
            "timestamp": 1234567890.0,
            "valid_path": True,
            "sanitized": False,
        }

        mock_git_info = {
            "is_git_repo": True,
            "current_branch": "fellowship",
            "repo_root": "/path/to/shire",
        }

        mock_file_stats = {
            "total_files": 42,
            "total_directories": 7,
            "method": "cached_optimized",
        }

        with patch(
            "src.tool_calls.project_operations._create_basic_project_info",
            return_value=mock_basic_info,
        ):
            with patch(
                "src.tool_calls.project_operations.get_git_info",
                return_value=mock_git_info,
            ):
                with patch(
                    "src.tool_calls.project_operations._get_file_statistics",
                    return_value=mock_file_stats,
                ):
                    with patch(
                        "src.tool_calls.project_operations.start_timer",
                        return_value=0,
                    ):
                        with patch(
                            "src.tool_calls.project_operations.get_duration",
                            return_value=0.123,
                        ):
                            result = get_project_info(mock_project_root)

                            assert result["project_root"] == "/path/to/shire"
                            assert result["project_name"] == "shire"
                            assert result["git"] == mock_git_info
                            assert result["file_stats"] == mock_file_stats
                            assert result["processing_time"] == 0.123


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
        """Test get_project_info with nonexistent path returns success with valid_path=false."""
        mock_project_root = Path("/invalid/path")
        arguments = {"include_stats": True}

        with patch(
            "src.tool_calls.project_operations.validate_project_root",
            return_value=False,
        ):
            result = handle_get_project_info(arguments, mock_project_root)

            assert result.get("isError", True) is False
            content = json.loads(result["content"][0]["text"])
            structured_content = result.get("structuredContent", {})

            assert content["valid_path"] is False
            assert content["project_root"] == "/invalid/path"
            assert structured_content["project"]["valid"] is False
            assert structured_content["project"]["root"] == "/invalid/path"

    @patch("src.tool_calls.project_operations.get_project_info")
    @patch("src.tool_calls.project_operations.validate_project_root")
    def test_handle_get_project_info_exception(
        self, mock_validate, mock_get_project_info
    ):
        """Test get_project_info handler with exception."""
        mock_validate.return_value = True
        mock_get_project_info.side_effect = OSError("Test error")

        mock_project_root = Path("/path/to/project")
        arguments = {"include_stats": True}

        result = handle_get_project_info(arguments, mock_project_root)

        assert result["isError"] is True
        assert "Error retrieving project info" in result["error"]

    def test_handle_get_project_info_without_stats(self):
        """Test get_project_info without statistics."""
        mock_project_root = Path("/path/to/shire")
        arguments = {"include_stats": False}

        mock_basic_info = {
            "project_root": "/path/to/shire",
            "project_name": "shire",
            "timestamp": 1234567890.0,
            "valid_path": True,
            "sanitized": False,
        }

        with patch(
            "src.tool_calls.project_operations.validate_project_root",
            return_value=True,
        ):
            with patch(
                "src.tool_calls.project_operations._create_basic_project_info",
                return_value=mock_basic_info,
            ):
                result = handle_get_project_info(arguments, mock_project_root)

                assert "content" in result
                content = json.loads(result["content"][0]["text"])
                structured_content = result.get("structuredContent", {})

                assert content["project_root"] == "/path/to/shire"
                assert content["project_name"] == "shire"
                assert content["valid_path"] is True
                assert content["sanitized"] is False
                assert "git" not in content
                assert "file_stats" not in content

                assert structured_content["project"]["root"] == "/path/to/shire"
                assert structured_content["project"]["name"] == "shire"
                assert structured_content["project"]["valid"] is True

    def test_handle_get_project_info_without_stats_sanitized(self):
        """Test get_project_info without statistics with sanitized name."""
        mock_project_root = Path("/path/to/shire-special!")
        arguments = {"include_stats": False}

        mock_basic_info = {
            "project_root": "/path/to/shire-special!",
            "project_name": "shire_special",
            "raw_project_name": "shire-special!",
            "timestamp": 1234567890.0,
            "valid_path": True,
            "sanitized": True,
        }

        with patch(
            "src.tool_calls.project_operations.validate_project_root",
            return_value=True,
        ):
            with patch(
                "src.tool_calls.project_operations._create_basic_project_info",
                return_value=mock_basic_info,
            ):
                result = handle_get_project_info(arguments, mock_project_root)

                assert "content" in result
                content = json.loads(result["content"][0]["text"])
                structured_content = result.get("structuredContent", {})

                assert content["project_name"] == "shire_special"
                assert content["raw_project_name"] == "shire-special!"
                assert content["sanitized"] is True

                assert structured_content["project"]["name"] == "shire_special"
                assert (
                    structured_content["project"]["original_name"] == "shire-special!"
                )
                assert structured_content["metadata"]["sanitized"] is True

    def test_handle_get_project_info_value_error(self):
        """Test get_project_info handler with ValueError."""
        mock_project_root = Path("/path/to/project")
        arguments = {"include_stats": True}

        with patch(
            "src.tool_calls.project_operations.validate_project_root",
            return_value=True,
        ):
            with patch(
                "src.tool_calls.project_operations.get_project_info",
                side_effect=ValueError("Value error"),
            ):
                result = handle_get_project_info(arguments, mock_project_root)

                assert result["isError"] is True
                assert "Error retrieving project info" in result["error"]

    def test_handle_get_project_info_type_error(self):
        """Test get_project_info handler with TypeError."""
        mock_project_root = Path("/path/to/project")
        arguments = {"include_stats": True}

        with patch(
            "src.tool_calls.project_operations.validate_project_root",
            return_value=True,
        ):
            with patch(
                "src.tool_calls.project_operations.get_project_info",
                side_effect=TypeError("Type error"),
            ):
                result = handle_get_project_info(arguments, mock_project_root)

                assert result["isError"] is True
                assert "Error retrieving project info" in result["error"]

    def test_handle_get_project_info_json_decode_error(self):
        """Test get_project_info handler with JSON decode error."""
        mock_project_root = Path("/path/to/project")
        arguments = {"include_stats": True}

        with patch(
            "src.tool_calls.project_operations.validate_project_root",
            return_value=True,
        ):
            with patch(
                "json.dumps",
                side_effect=json.JSONDecodeError("JSON error", "", 0),
            ):
                result = handle_get_project_info(arguments, mock_project_root)

                assert result["isError"] is True
                assert "Error retrieving project info" in result["error"]


class TestVersionEnvironmentIntegration:
    """Test version handling with environment variables."""

    def test_server_version_uses_environment_variable(self):
        """Test that server version can be overridden by environment variable."""
        mock_project_root = Path("/path/to/project")
        arguments = {}

        with patch.dict(os.environ, {"GANDALF_SERVER_VERSION": "3.0.0"}):
            with patch(
                "src.tool_calls.project_operations.GANDALF_SERVER_VERSION",
                "3.0.0",
            ):
                result = handle_get_server_version(
                    arguments, project_root=mock_project_root
                )

        content = json.loads(result["content"][0]["text"])
        assert content["server_version"] == "3.0.0"

    def test_server_version_fallback_when_no_env_var(self):
        """Test that server version falls back to default when no env var."""
        mock_project_root = Path("/path/to/project")
        arguments = {}

        # Ensure the environment variable is not set
        with patch.dict(os.environ, {}, clear=True):
            result = handle_get_server_version(
                arguments, project_root=mock_project_root
            )

        content = json.loads(result["content"][0]["text"])
        # Should use the default from constants
        assert content["server_version"] == GANDALF_SERVER_VERSION


class TestToolDefinitionCompliance:
    """Test tool definition compliance and structure."""

    def test_get_server_version_tool_definition_structure(self):
        """Test that get_server_version tool definition has correct structure."""
        tool_def = TOOL_GET_SERVER_VERSION

        assert tool_def["name"] == "get_server_version"
        assert "description" in tool_def
        assert "inputSchema" in tool_def
        assert tool_def["inputSchema"]["type"] == "object"
        assert "properties" in tool_def["inputSchema"]
        assert tool_def["inputSchema"]["required"] == []

        # Check annotations
        assert "annotations" in tool_def
        annotations = tool_def["annotations"]
        assert annotations["readOnlyHint"] is True
        assert annotations["destructiveHint"] is False
        assert annotations["idempotentHint"] is True

    def test_get_project_info_tool_definition_structure(self):
        """Test that get_project_info tool definition has correct structure."""
        tool_def = TOOL_GET_PROJECT_INFO

        assert tool_def["name"] == "get_project_info"
        assert "description" in tool_def
        assert "inputSchema" in tool_def
        assert tool_def["inputSchema"]["type"] == "object"
        assert "properties" in tool_def["inputSchema"]
        assert "include_stats" in tool_def["inputSchema"]["properties"]
        assert (
            tool_def["inputSchema"]["properties"]["include_stats"]["type"] == "boolean"
        )
        assert tool_def["inputSchema"]["properties"]["include_stats"]["default"] is True

    def test_tool_handlers_registration(self):
        """Test that tool handlers are properly registered."""
        assert "get_project_info" in PROJECT_TOOL_HANDLERS
        assert "get_server_version" in PROJECT_TOOL_HANDLERS

        assert PROJECT_TOOL_HANDLERS["get_project_info"] == handle_get_project_info
        assert PROJECT_TOOL_HANDLERS["get_server_version"] == handle_get_server_version

    def test_tool_definitions_registration(self):
        """Test that tool definitions are properly registered."""
        assert len(PROJECT_TOOL_DEFINITIONS) == 2

        tool_names = [tool["name"] for tool in PROJECT_TOOL_DEFINITIONS]
        assert "get_project_info" in tool_names
        assert "get_server_version" in tool_names

    def test_tool_definition_annotations_consistency(self):
        """Test that tool definition annotations are consistent."""
        for tool_def in PROJECT_TOOL_DEFINITIONS:
            assert "annotations" in tool_def
            annotations = tool_def["annotations"]

            # All project operations should be read-only
            assert annotations["readOnlyHint"] is True
            assert annotations["destructiveHint"] is False
            assert annotations["idempotentHint"] is True
            assert "title" in annotations


class TestProjectOperations:
    """Test project operations integration."""

    def test_get_project_info_basic(self):
        """Test basic project info retrieval."""
        # This test is already implemented in the original file

    def test_project_operations_with_real_temp_directory(self):
        """Test project operations with a real temporary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Create some test files
            (project_root / "test.py").write_text("# Test file")
            (project_root / "subdir").mkdir()
            (project_root / "subdir" / "nested.js").write_text("// Nested file")

            arguments = {"include_stats": True}
            result = handle_get_project_info(arguments, project_root)

            assert "content" in result
            content = json.loads(result["content"][0]["text"])
            structured_content = result.get("structuredContent", {})

            assert content["valid_path"] is True
            assert content["project_name"] == project_root.name

            assert structured_content["project"]["valid"] is True
            assert structured_content["project"]["name"] == project_root.name
            assert "file_stats" in content
            assert "git" in content

    def test_project_operations_performance_timing(self):
        """Test that project operations include performance timing."""
        mock_project_root = Path("/path/to/shire")
        arguments = {"include_stats": True}

        with patch(
            "src.tool_calls.project_operations.validate_project_root",
            return_value=True,
        ):
            with patch(
                "src.tool_calls.project_operations.get_project_info"
            ) as mock_get_info:
                mock_get_info.return_value = {
                    "project_root": "/path/to/shire",
                    "project_name": "shire",
                    "processing_time": 0.456,
                    "git": {"is_git_repo": False},
                    "file_stats": {"total_files": 10, "total_directories": 2},
                }

                result = handle_get_project_info(arguments, mock_project_root)

                assert "content" in result
                content = json.loads(result["content"][0]["text"])
                structured_content = result.get("structuredContent", {})

                assert "processing_time" in content
                assert isinstance(content["processing_time"], int | float)

                assert "metadata" in structured_content
                assert "timestamp" in structured_content["metadata"]
