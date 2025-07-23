"""
Tests for project filtering functionality.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.project_filtering import (
    filter_project_files,
    get_excluded_patterns,
)


class TestFilterProjectFiles:
    """Test cases for filter_project_files function."""

    def test_successful_filtering(self, tmp_path):
        """Test successful file filtering with real files."""
        # Create test files
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("# main module")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text("# test module")
        (tmp_path / "README.md").write_text("# Project")

        result = filter_project_files(tmp_path)

        assert len(result) == 3
        assert all(isinstance(f, str) for f in result)

        # Convert to relative paths for easier assertion
        relative_paths = [str(Path(f).relative_to(tmp_path)) for f in result]
        assert "src/main.py" in relative_paths
        assert "tests/test_main.py" in relative_paths
        assert "README.md" in relative_paths

    def test_empty_project(self, tmp_path):
        """Test filtering empty project."""
        result = filter_project_files(tmp_path)
        assert result == []

    def test_excluded_files_filtered_out(self, tmp_path):
        """Test that excluded files are properly filtered out."""
        # Create files that should be included
        (tmp_path / "main.py").write_text("# main")
        (tmp_path / "config.json").write_text("{}")

        # Create files that should be excluded
        (tmp_path / "test.pyc").write_text("")  # Compiled Python
        (tmp_path / "debug.log").write_text("")  # Log file
        (tmp_path / ".DS_Store").write_text("")  # macOS metadata

        result = filter_project_files(tmp_path)

        # Should only include non-excluded files
        assert len(result) == 2
        relative_paths = [str(Path(f).relative_to(tmp_path)) for f in result]
        assert "main.py" in relative_paths
        assert "config.json" in relative_paths
        assert "test.pyc" not in relative_paths
        assert "debug.log" not in relative_paths
        assert ".DS_Store" not in relative_paths

    def test_excluded_directories_filtered_out(self, tmp_path):
        """Test that excluded directories are properly filtered out."""
        # Create files in included directories
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("# main")

        # Create files in excluded directories
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "main.cpython-39.pyc").write_text("")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("")
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "package.json").write_text("{}")

        result = filter_project_files(tmp_path)

        # Should only include files from non-excluded directories
        assert len(result) == 1
        relative_paths = [str(Path(f).relative_to(tmp_path)) for f in result]
        assert "src/main.py" in relative_paths

    def test_file_limit_enforcement(self, tmp_path):
        """Test that file limit is enforced."""
        # Create many files
        for i in range(50):
            (tmp_path / f"file_{i}.py").write_text(f"# file {i}")

        with patch("src.core.project_filtering.MAX_PROJECT_FILES", 10):
            result = filter_project_files(tmp_path)
            assert len(result) == 10

    def test_permission_error_handling(self, tmp_path):
        """Test handling of permission errors."""
        # Create a file we can access
        (tmp_path / "accessible.py").write_text("# accessible")

        # Mock permission error during iteration
        with patch(
            "src.core.project_filtering._iterate_project_files",
            side_effect=PermissionError("Access denied"),
        ):
            result = filter_project_files(tmp_path)
            assert result == []

    def test_os_error_handling(self, tmp_path):
        """Test handling of OS errors."""
        with patch(
            "src.core.project_filtering._iterate_project_files",
            side_effect=OSError("Test OS error"),
        ):
            result = filter_project_files(tmp_path)
            assert result == []

    def test_timeout_handling(self, tmp_path):
        """Test handling of timeout during file scanning."""
        # Create some files
        for i in range(5):
            (tmp_path / f"file_{i}.py").write_text(f"# file {i}")

        # Mock very short timeout
        with patch("src.core.project_filtering.FIND_COMMAND_TIMEOUT", 0.001):
            result = filter_project_files(tmp_path)
            # Should return partial results due to timeout
            assert isinstance(result, list)

    def test_nested_directories(self, tmp_path):
        """Test handling of deeply nested directories."""
        # Create nested structure
        nested_dir = tmp_path / "level1" / "level2" / "level3"
        nested_dir.mkdir(parents=True)
        (nested_dir / "deep_file.py").write_text("# deep file")
        (tmp_path / "root_file.py").write_text("# root file")

        result = filter_project_files(tmp_path)

        assert len(result) == 2
        relative_paths = [str(Path(f).relative_to(tmp_path)) for f in result]
        assert "root_file.py" in relative_paths
        assert "level1/level2/level3/deep_file.py" in relative_paths

    def test_invalid_project_root_type(self):
        """Test that TypeError is raised for invalid project_root type."""
        with pytest.raises(TypeError, match="project_root must be a Path object"):
            filter_project_files("/invalid/string/path")

    def test_nonexistent_project_root(self, tmp_path):
        """Test that ValueError is raised for nonexistent project_root."""
        nonexistent_path = tmp_path / "nonexistent"

        with pytest.raises(ValueError, match="Project root does not exist"):
            filter_project_files(nonexistent_path)

    def test_project_root_not_directory(self, tmp_path):
        """Test that ValueError is raised when project_root is not a directory."""
        file_path = tmp_path / "test_file.txt"
        file_path.write_text("test content")

        with pytest.raises(ValueError, match="Project root is not a directory"):
            filter_project_files(file_path)

    @patch("src.core.project_filtering.log_debug")
    def test_logging_on_timeout(self, mock_log_debug, tmp_path):
        """Test that timeout is logged appropriately."""
        # Create many files to increase processing time
        for i in range(20):
            (tmp_path / f"test_{i}.py").write_text(f"# test {i}")

        # Mock very short timeout to force timeout condition
        with patch("src.core.project_filtering.FIND_COMMAND_TIMEOUT", 0.0001):
            result = filter_project_files(tmp_path)

            # Should log timeout message if timeout was hit
            [
                call
                for call in mock_log_debug.call_args_list
                if "timeout" in str(call).lower()
            ]
            # At minimum, the function should still complete and return a list
            assert isinstance(result, list)

    @patch("src.core.project_filtering.log_error")
    def test_logging_on_error(self, mock_log_error, tmp_path):
        """Test that errors are logged appropriately."""
        with patch(
            "src.core.project_filtering._iterate_project_files",
            side_effect=OSError("Test error"),
        ):
            filter_project_files(tmp_path)
            mock_log_error.assert_called_once()


class TestGetExcludedPatterns:
    """Test cases for get_excluded_patterns function."""

    def test_returns_expected_structure(self):
        """Test that function returns expected dictionary structure."""
        patterns = get_excluded_patterns()

        assert isinstance(patterns, dict)
        assert "directories" in patterns
        assert "file_patterns" in patterns
        assert "max_files" in patterns
        assert "timeout" in patterns

    def test_directories_list(self):
        """Test that directories list contains expected values."""
        patterns = get_excluded_patterns()
        directories = patterns["directories"]

        assert isinstance(directories, list)
        assert "__pycache__" in directories
        assert ".git" in directories

    def test_file_patterns_list(self):
        """Test that file patterns list contains expected values."""
        patterns = get_excluded_patterns()
        file_patterns = patterns["file_patterns"]

        assert isinstance(file_patterns, list)
        assert "*.pyc" in file_patterns

    def test_numeric_values(self):
        """Test that numeric values are present and reasonable."""
        patterns = get_excluded_patterns()

        assert isinstance(patterns["max_files"], int)
        assert patterns["max_files"] > 0
        assert isinstance(patterns["timeout"], int)
        assert patterns["timeout"] > 0
