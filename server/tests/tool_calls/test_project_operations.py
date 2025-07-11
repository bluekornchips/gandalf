"""
Tests for project operations functionality.

Tests project info retrieval, git operations, and file statistics
with comprehensive coverage of project operations functionality.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.tool_calls.project_operations import (
    get_project_info,
    get_git_info,
    handle_get_project_info,
    _get_file_statistics,
)


class TestGetProjectInfo:
    """Test get_project_info function."""

    def test_get_project_info_complete(self):
        """Test complete project info retrieval."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Create some test files
            (project_root / "main.py").write_text("print('hello')")
            (project_root / "README.md").write_text("# Test Project")

            # Mock git operations
            with patch("src.tool_calls.project_operations.get_git_info") as mock_git:
                mock_git.return_value = {
                    "is_git_repo": True,
                    "current_branch": "main",
                    "repo_root": str(project_root),
                }

                with patch(
                    "src.tool_calls.project_operations._get_file_statistics"
                ) as mock_stats:
                    mock_stats.return_value = {
                        "total_files": 2,
                        "total_directories": 0,
                        "method": "mocked",
                    }

                    result = get_project_info(project_root)

                    assert (
                        result["project_name"] == "tmp"
                        or result["project_name"] == temp_dir.split("/")[-1]
                    )
                    assert result["project_root"] == str(project_root)
                    assert result["git"]["is_git_repo"] is True
                    assert result["file_stats"]["total_files"] == 2

    def test_get_project_info_without_stats(self):
        """Test project info retrieval without statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            with patch("src.tool_calls.project_operations.get_git_info") as mock_git:
                mock_git.return_value = {
                    "is_git_repo": False,
                }

                # Test handle function with include_stats=False
                result = handle_get_project_info({"include_stats": False}, project_root)

                # Updated: check for new response format with content field
                assert "content" in result
                content = json.loads(result["content"][0]["text"])
                assert "project_name" in content
                assert "project_root" in content
                # Should not have git or file_stats when stats are disabled
                assert "git" not in content
                assert "file_stats" not in content


class TestProjectOperationsErrorHandling:
    """Test error handling in project operations."""

    def test_handle_get_project_info_path_validation_error(self):
        """Test handling of path validation errors."""
        mock_project_root = Path("/nonexistent/path")
        arguments = {"include_stats": True}

        with patch(
            "src.tool_calls.project_operations.validate_project_root",
            return_value=False,
        ):
            result = handle_get_project_info(arguments, mock_project_root)

            # Updated: check for error response format
            assert "error" in result
            assert "Project root does not exist or is not accessible" in result["error"]

    def test_handle_get_project_info_exception(self):
        """Test handling of unexpected exceptions."""
        mock_project_root = Path("/path/to/project")
        arguments = {"include_stats": True}

        with patch(
            "src.tool_calls.project_operations.validate_project_root",
            return_value=True,
        ):
            with patch(
                "src.tool_calls.project_operations.get_project_info",
                side_effect=ValueError("Unexpected error"),
            ):
                result = handle_get_project_info(arguments, mock_project_root)

                # Updated: check for error response format
                assert "error" in result
                assert "Error retrieving project info" in result["error"]

    def test_handle_get_project_info_without_stats(self):
        """Test project info retrieval without statistics."""
        mock_project_root = Path("/path/to/project")
        arguments = {"include_stats": False}

        with patch(
            "src.tool_calls.project_operations.validate_project_root",
            return_value=True,
        ):
            with patch(
                "src.tool_calls.project_operations._create_basic_project_info"
            ) as mock_basic:
                mock_basic.return_value = {
                    "project_name": "project",
                    "project_root": str(mock_project_root),
                    "timestamp": 1234567890,
                    "valid_path": True,
                    "sanitized": False,
                }

                result = handle_get_project_info(arguments, mock_project_root)

                # Updated: check for new response format with content field
                assert "content" in result
                content = json.loads(result["content"][0]["text"])
                assert content["project_name"] == "project"


class TestGitInfoIntegration:
    """Test git information integration."""

    def test_get_git_info_not_a_repo(self):
        """Test Git info retrieval for non-repository."""
        mock_project_root = Path("/path/to/project")

        with patch("subprocess.run") as mock_run:
            # Mock failed git command (not a repo)
            mock_run.return_value = Mock(returncode=1)

            result = get_git_info(mock_project_root)

            assert result["is_git_repo"] is False
            # The function only sets current_branch when it's a git repo
            assert (
                "current_branch" not in result or result.get("current_branch") is None
            )

    def test_get_git_info_subprocess_error(self):
        """Test Git info retrieval with subprocess error."""
        mock_project_root = Path("/path/to/project")

        # Mock subprocess.run to raise OSError, which is caught by get_git_info
        with patch("subprocess.run", side_effect=OSError("Git error")):
            result = get_git_info(mock_project_root)

            assert result["is_git_repo"] is False
            assert "error" in result
            assert "Git error" in result["error"]


class TestFileStatistics:
    """Test file statistics functionality."""

    def test_get_file_statistics_success(self):
        """Test successful file statistics retrieval."""
        mock_project_root = Path("/path/to/project")

        with patch(
            "src.tool_calls.project_operations._get_file_stats_with_cache_optimization"
        ) as mock_cache_opt:
            mock_cache_opt.return_value = {
                "total_files": 100,
                "total_directories": 10,
                "method": "cached_optimized",
            }

            # Mock the Path.exists() method to return True
            with patch.object(Path, "exists", return_value=True):
                result = _get_file_statistics(mock_project_root)

                assert result["total_files"] == 100
                assert result["total_directories"] == 10

    def test_get_file_statistics_fallback(self):
        """Test file statistics with fallback method."""
        mock_project_root = Path("/path/to/project")

        # Mock the optimization method to fail and fallback to fast method
        with patch(
            "src.tool_calls.project_operations._get_file_stats_with_cache_optimization",
            side_effect=OSError("Cache error"),
        ):
            with patch(
                "src.tool_calls.project_operations._get_file_stats_fast"
            ) as mock_fast:
                mock_fast.return_value = {
                    "total_files": 50,
                    "total_directories": 5,
                    "method": "find_command",
                }

                # Mock the Path.exists() method to return True
                with patch.object(Path, "exists", return_value=True):
                    result = _get_file_statistics(mock_project_root)

                    # Should use the fallback method when optimization fails
                    assert result["total_files"] == 50
                    assert result["total_directories"] == 5
                    assert result["method"] == "find_command"

    def test_get_file_statistics_all_methods_fail(self):
        """Test file statistics when all methods fail."""
        mock_project_root = Path("/path/to/project")

        # Mock the fast method to return an error result instead of raising
        with patch(
            "src.tool_calls.project_operations._get_file_stats_with_cache_optimization",
            side_effect=OSError("Error"),
        ):
            with patch(
                "src.tool_calls.project_operations._get_file_stats_fast"
            ) as mock_fast:
                # Mock _get_file_stats_fast to return error result
                mock_fast.return_value = {
                    "total_files": 0,
                    "total_directories": 0,
                    "method": "find_error",
                }

                # Mock the Path.exists() method to return True
                with patch.object(Path, "exists", return_value=True):
                    result = _get_file_statistics(mock_project_root)

                    # When optimization fails, should fallback to fast method
                    assert result["total_files"] == 0
                    assert result["total_directories"] == 0
                    assert result["method"] == "find_error"
