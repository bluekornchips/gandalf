"""
Tests for project filtering functionality.
"""

import subprocess
from unittest.mock import Mock, patch

import pytest

from src.core.project_filtering import (
    filter_project_files,
    get_excluded_patterns,
    _build_find_command,
    _process_find_output,
)


class TestFilterProjectFiles:
    """Test cases for filter_project_files function."""

    def test_successful_filtering(self, tmp_path):
        """Test successful file filtering with mock subprocess."""
        test_files = [
            "src/main.py",
            "tests/test_main.py",
            "README.md",
        ]

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "\n".join([str(tmp_path / f) for f in test_files])

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = filter_project_files(tmp_path)

            assert len(result) == 3
            assert all(isinstance(f, str) for f in result)
            mock_run.assert_called_once()

    def test_empty_project(self, tmp_path):
        """Test filtering empty project."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            result = filter_project_files(tmp_path)

            assert result == []

    def test_find_command_failure(self, tmp_path):
        """Test handling of find command failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Permission denied"

        with patch("subprocess.run", return_value=mock_result):
            result = filter_project_files(tmp_path)

            assert result == []

    def test_subprocess_timeout(self, tmp_path):
        """Test handling of subprocess timeout."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("find", 30)):
            result = filter_project_files(tmp_path)

            assert result == []

    def test_subprocess_error(self, tmp_path):
        """Test handling of subprocess errors."""
        with patch(
            "subprocess.run",
            side_effect=subprocess.SubprocessError("Test error"),
        ):
            result = filter_project_files(tmp_path)

            assert result == []

    def test_os_error(self, tmp_path):
        """Test handling of OS errors."""
        with patch("subprocess.run", side_effect=OSError("Test OS error")):
            result = filter_project_files(tmp_path)

            assert result == []

    def test_unicode_decode_error(self, tmp_path):
        """Test handling of unicode decode errors."""
        with patch(
            "subprocess.run",
            side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "Test error"),
        ):
            result = filter_project_files(tmp_path)

            assert result == []

    def test_file_limit_enforcement(self, tmp_path):
        """Test that file limit is enforced."""
        # Create a biiiig ole number of mock files
        large_file_list = [f"file_{i}.py" for i in range(15000)]

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "\n".join(large_file_list)

        with patch("subprocess.run", return_value=mock_result):
            result = filter_project_files(tmp_path)

            # Should be limited to MAX_PROJECT_FILES, default is 10000
            assert len(result) == 10000

    def test_find_command_construction(self, tmp_path):
        """Test that find command is constructed correctly."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            filter_project_files(tmp_path)

            # Verify the command structure
            call_args = mock_run.call_args
            cmd = call_args[0][0]

            assert cmd[0] == "find"
            assert cmd[1] == str(tmp_path)
            assert "-type" in cmd
            assert "f" in cmd
            assert "-not" in cmd
            assert "-path" in cmd or "-name" in cmd

    def test_whitespace_handling(self, tmp_path):
        """Test handling of whitespace in file paths."""
        test_files = [
            "file with spaces.py",
            "  leading_spaces.py",
            "trailing_spaces.py  ",
            "",  # Empty line
            "   ",  # Whitespace only
        ]

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "\n".join(test_files)

        with patch("subprocess.run", return_value=mock_result):
            result = filter_project_files(tmp_path)

            # Should filter out empty/whitespace-only entries
            assert len(result) == 3
            assert "file with spaces.py" in result
            assert "leading_spaces.py" in result
            assert "trailing_spaces.py" in result

    @patch("src.core.project_filtering.log_debug")
    def test_logging_on_failure(self, mock_log_debug, tmp_path):
        """Test that failures are logged appropriately."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Test error message"

        with patch("subprocess.run", return_value=mock_result):
            filter_project_files(tmp_path)

            mock_log_debug.assert_called_with("Find command failed: Test error message")

    @patch("src.core.project_filtering.log_error")
    def test_logging_on_timeout(self, mock_log_error, tmp_path):
        """Test that timeout errors are logged appropriately."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("find", 30)):
            filter_project_files(tmp_path)

            mock_log_error.assert_called_once()
            # Verify the exception type and message
            call_args = mock_log_error.call_args
            assert isinstance(call_args[0][0], subprocess.TimeoutExpired)
            assert call_args[0][1] == "filter_project_files"

    @patch("src.core.project_filtering.log_error")
    def test_logging_on_subprocess_error(self, mock_log_error, tmp_path):
        """Test that subprocess errors are logged appropriately."""
        test_error = subprocess.SubprocessError("Test subprocess error")

        with patch("subprocess.run", side_effect=test_error):
            filter_project_files(tmp_path)

            mock_log_error.assert_called_once_with(test_error, "filter_project_files")

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


class TestBuildFindCommand:
    """Test cases for _build_find_command function."""

    def test_basic_command_structure(self, tmp_path):
        """Test basic find command structure."""
        cmd = _build_find_command(tmp_path)

        assert cmd[0] == "find"
        assert cmd[1] == str(tmp_path)
        assert "-type" in cmd
        assert "f" in cmd

    def test_exclusion_patterns_included(self, tmp_path):
        """Test that exclusion patterns are included in command."""
        cmd = _build_find_command(tmp_path)

        # Should contain exclusion patterns
        assert "-not" in cmd
        assert "-path" in cmd
        assert "-name" in cmd

        # Should contain some common exclusions
        cmd_str = " ".join(cmd)
        assert "__pycache__" in cmd_str
        assert ".git" in cmd_str
        assert "*.pyc" in cmd_str


class TestProcessFindOutput:
    """Test cases for _process_find_output function."""

    def test_basic_output_processing(self):
        """Test basic output processing."""
        stdout = "file1.py\nfile2.py\nfile3.py\n"
        result = _process_find_output(stdout)

        assert result == ["file1.py", "file2.py", "file3.py"]

    def test_empty_output(self):
        """Test processing empty output."""
        result = _process_find_output("")
        assert result == []

    def test_whitespace_handling(self):
        """Test handling of whitespace in output."""
        stdout = "  file1.py  \n\nfile2.py\n   \n  file3.py\n"
        result = _process_find_output(stdout)

        assert result == ["file1.py", "file2.py", "file3.py"]

    def test_single_file(self):
        """Test processing single file output."""
        stdout = "single_file.py\n"
        result = _process_find_output(stdout)

        assert result == ["single_file.py"]


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
        assert "node_modules" in directories

    def test_file_patterns_list(self):
        """Test that file patterns list contains expected values."""
        patterns = get_excluded_patterns()
        file_patterns = patterns["file_patterns"]

        assert isinstance(file_patterns, list)
        assert "*.pyc" in file_patterns
        assert "*.log" in file_patterns
        assert ".DS_Store" in file_patterns

    def test_numeric_values(self):
        """Test that numeric values are present and reasonable."""
        patterns = get_excluded_patterns()

        assert isinstance(patterns["max_files"], int)
        assert patterns["max_files"] > 0
        assert isinstance(patterns["timeout"], int)
        assert patterns["timeout"] > 0
