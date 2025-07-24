"""
Tests for file statistics functionality.

lotr-info: Tests file counting operations using Shire directory structures
and Rivendell archive statistics.
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

from src.tool_calls.project_operations import (
    _get_file_statistics,
    _get_file_stats_fast,
    _get_file_stats_with_cache_optimization,
)


class TestFileStatistics:
    """Test file statistics functionality."""

    def test_get_file_stats_fast_success(self):
        """Test _get_file_stats_fast with successful find commands."""
        mock_project_root = Path("/mnt/doom/shire")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                # First call: find files
                Mock(returncode=0, stdout="baggins.py\nfellowship.js\nring.md\n"),
                # Second call: find directories
                Mock(
                    returncode=0,
                    stdout="/mnt/doom/shire\n/mnt/doom/shire/hobbiton\n/mnt/doom/shire/bywater\n",
                ),
            ]

            result = _get_file_stats_fast(mock_project_root)

            assert result["total_files"] == 3
            assert result["total_directories"] == 2  # Excluding root
            assert result["method"] == "find_command"

    def test_get_file_stats_fast_command_failure(self):
        """Test _get_file_stats_fast with find command failure."""
        mock_project_root = Path("/mnt/doom/mordor")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                # First call: find files (failure)
                Mock(returncode=1, stdout=""),
                # Second call: find directories (success)
                Mock(returncode=0, stdout="/mnt/doom/mordor\n"),
            ]

            result = _get_file_stats_fast(mock_project_root)

            assert result["total_files"] == 0
            assert result["total_directories"] == 0
            assert result["method"] == "find_failed"

    def test_get_file_stats_fast_subprocess_error(self):
        """Test _get_file_stats_fast with subprocess error."""
        mock_project_root = Path("/mnt/doom/isengard")

        with patch(
            "subprocess.run",
            side_effect=subprocess.SubprocessError("Saruman's find error"),
        ):
            result = _get_file_stats_fast(mock_project_root)

            assert result["total_files"] == 0
            assert result["total_directories"] == 0
            assert result["method"] == "find_error"

    def test_get_file_stats_fast_timeout_error(self):
        """Test _get_file_stats_fast with timeout error."""
        mock_project_root = Path("/mnt/doom/fangorn")

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("find", 5)):
            result = _get_file_stats_fast(mock_project_root)

            assert result["total_files"] == 0
            assert result["total_directories"] == 0
            assert result["method"] == "find_error"

    def test_get_file_stats_fast_os_error(self):
        """Test _get_file_stats_fast with OS error."""
        mock_project_root = Path("/mnt/doom/moria")

        with patch("subprocess.run", side_effect=OSError("Balrog OS error")):
            result = _get_file_stats_fast(mock_project_root)

            assert result["total_files"] == 0
            assert result["total_directories"] == 0
            assert result["method"] == "find_error"

    def test_get_file_stats_fast_empty_output(self):
        """Test _get_file_stats_fast with empty find output."""
        mock_project_root = Path("/mnt/doom/empty-lands")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                # First call: find files (empty)
                Mock(returncode=0, stdout=""),
                # Second call: find directories (only root)
                Mock(returncode=0, stdout="/mnt/doom/empty-lands\n"),
            ]

            result = _get_file_stats_fast(mock_project_root)

            assert result["total_files"] == 0
            assert result["total_directories"] == 0  # Excluding root
            assert result["method"] == "find_command"

    def test_get_file_stats_with_cache_optimization_success(self):
        """Test _get_file_stats_with_cache_optimization with cached files."""
        mock_project_root = Path("/mnt/doom/rivendell")
        mock_files = ["elrond.py", "arwen.js", "vilya.md"]

        with patch(
            "src.tool_calls.project_operations.get_files_list",
            return_value=mock_files,
        ):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(
                    returncode=0,
                    stdout="/mnt/doom/rivendell\n/mnt/doom/rivendell/halls\n/mnt/doom/rivendell/gardens\n",
                )

                result = _get_file_stats_with_cache_optimization(mock_project_root)

                assert result["total_files"] == 3
                assert result["total_directories"] == 2  # Excluding root
                assert result["method"] == "cached_optimized"

    def test_get_file_stats_with_cache_optimization_no_cache(self):
        """Test _get_file_stats_with_cache_optimization without cached files."""
        mock_project_root = Path("/mnt/doom/gondor")

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
        mock_project_root = Path("/mnt/doom/rohan")

        with patch(
            "src.tool_calls.project_operations.get_files_list",
            side_effect=ValueError("Eomer's cache error"),
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
        mock_project_root = Path("/mnt/doom/lorien")
        mock_files = ["galadriel.py", "celeborn.js"]

        with patch(
            "src.tool_calls.project_operations.get_files_list",
            return_value=mock_files,
        ):
            with patch(
                "subprocess.run",
                side_effect=subprocess.SubprocessError("Mirror error"),
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
        mock_project_root = Path("/mnt/doom/undying-lands")

        with patch("pathlib.Path.exists", return_value=False):
            result = _get_file_statistics(mock_project_root)

            assert result["total_files"] == 0
            assert result["total_directories"] == 0
            assert result["method"] == "path_not_found"

    def test_get_file_statistics_cache_optimization_success(self):
        """Test _get_file_statistics using cache optimization."""
        mock_project_root = Path("/mnt/doom/minas-tirith")

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
        mock_project_root = Path("/mnt/doom/edoras")

        with patch("pathlib.Path.exists", return_value=True):
            with patch(
                "src.tool_calls.project_operations._get_file_stats_with_cache_optimization",
                side_effect=OSError("Golden Hall cache error"),
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

    def test_file_statistics_edge_cases(self):
        """Test file statistics with edge cases."""
        # Test with very large numbers
        large_project_root = Path("/mnt/doom/all-middle-earth")

        with patch("pathlib.Path.exists", return_value=True):
            with patch(
                "src.tool_calls.project_operations._get_file_stats_with_cache_optimization"
            ) as mock_cache:
                mock_cache.return_value = {
                    "total_files": 999999,
                    "total_directories": 888888,
                    "method": "cached_optimized",
                }

                result = _get_file_statistics(large_project_root)

                assert result["total_files"] == 999999
                assert result["total_directories"] == 888888
                assert result["method"] == "cached_optimized"

    def test_file_statistics_with_special_characters(self):
        """Test file statistics with special characters in paths."""
        special_path = Path("/mnt/doom/shire's bag-end & hobbiton")

        with patch("pathlib.Path.exists", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = [
                    Mock(returncode=0, stdout="frodo's-diary.txt\nsam&pippin.log\n"),
                    Mock(
                        returncode=0, stdout=f"{special_path}\n{special_path}/storage\n"
                    ),
                ]

                result = _get_file_stats_fast(special_path)

                assert result["total_files"] == 2
                assert result["total_directories"] == 1
                assert result["method"] == "find_command"
