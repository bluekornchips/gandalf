"""Test suite for common utility functions."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import src.utils.common as common


class MockConstants:
    VERSION = "0.1.0"


class TestGetVersion:
    """Test suite for get_version function."""

    @patch("src.utils.common.get_version", return_value=MockConstants.VERSION)
    def test_get_version_success(self, _mock_gv: MagicMock) -> None:
        """Test successful version retrieval."""
        version = common.get_version()
        assert version == MockConstants.VERSION

    def test_get_version_git_not_found(self) -> None:
        """Test error handling when git command is not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
            with pytest.raises(RuntimeError) as exc_info:
                common.get_version()
            assert "Git command not found" in str(exc_info.value)

    def test_get_version_git_failure(self) -> None:
        """Test error handling when git command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "git", "Not a git repository"
            )
            with pytest.raises(RuntimeError) as exc_info:
                common.get_version()
            assert "Failed to find git repository root" in str(exc_info.value)

    def test_get_version_file_not_found(self) -> None:
        """Test error handling when VERSION file is not found."""
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "/non/existent/path\n"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            with patch("pathlib.Path.exists", return_value=False):
                with pytest.raises(FileNotFoundError) as exc_info:
                    common.get_version()
                assert "VERSION file not found" in str(exc_info.value)

    def test_get_version_empty_file(self) -> None:
        """Test error handling when VERSION file is empty."""
        with tempfile.TemporaryDirectory() as temp_dir:
            version_file = Path(temp_dir) / "VERSION"
            version_file.write_text("")

            with patch("subprocess.run") as mock_run:
                mock_result = MagicMock()
                mock_result.stdout = f"{temp_dir}\n"
                mock_result.returncode = 0
                mock_run.return_value = mock_result

                with pytest.raises(ValueError) as exc_info:
                    common.get_version()
                assert "VERSION file is empty" in str(exc_info.value)

    def test_get_version_with_whitespace(self) -> None:
        """Test that version string is properly stripped of whitespace."""
        with tempfile.TemporaryDirectory() as temp_dir:
            version_file = Path(temp_dir) / "VERSION"
            version_file.write_text("  0.2.0  \n")

            with patch("subprocess.run") as mock_run:
                mock_result = MagicMock()
                mock_result.stdout = f"{temp_dir}\n"
                mock_result.returncode = 0
                mock_run.return_value = mock_result

                version = common.get_version()
                assert version == "0.2.0"

    def test_get_version_read_error(self) -> None:
        """Test error handling when VERSION file cannot be read."""
        with tempfile.TemporaryDirectory() as temp_dir:
            version_file = Path(temp_dir) / "VERSION"
            version_file.write_text("0.1.0")

            with patch("subprocess.run") as mock_run:
                mock_result = MagicMock()
                mock_result.stdout = f"{temp_dir}\n"
                mock_result.returncode = 0
                mock_run.return_value = mock_result

                with patch("builtins.open", side_effect=OSError("Permission denied")):
                    with pytest.raises(ValueError) as exc_info:
                        common.get_version()
                    assert "Error reading VERSION file" in str(exc_info.value)
