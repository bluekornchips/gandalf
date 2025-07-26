"""Test file scoring functionality."""

import time
from pathlib import Path
from unittest.mock import Mock, patch

from src.config.core_constants import MCP_CACHE_TTL, PRIORITY_NEUTRAL_SCORE
from src.core.file_scoring import (
    _compute_relevance_scores,
    _file_scores_cache,
    clear_file_scores,
    get_files_list,
    get_files_with_scores,
    get_scoring_info,
)


class TestGetFilesWithScores:
    """Test get_files_with_scores function."""

    def setup_method(self):
        """Set up test fixtures."""
        # Clear cache before each test
        _file_scores_cache.clear()
        self.project_root = Path("/tmp/test_project")

    def test_get_files_with_scores_no_cache(self):
        """Test getting files with scores when no cache exists."""
        mock_files = ["frodo_file.py", "sam_file.py", "gandalf_file.py"]
        mock_scored_files = [
            ("frodo_file.py", 0.9),
            ("sam_file.py", 0.7),
            ("gandalf_file.py", 0.5),
        ]

        with patch(
            "src.core.file_scoring.filter_project_files",
            return_value=mock_files,
        ):
            with patch(
                "src.core.file_scoring._compute_relevance_scores",
                return_value=mock_scored_files,
            ):
                with patch("src.core.file_scoring.log_info") as mock_log_info:
                    with patch("src.core.file_scoring.log_debug") as mock_log_debug:
                        result = get_files_with_scores(self.project_root)

        assert result == mock_scored_files

        cache_key = str(self.project_root)
        assert cache_key in _file_scores_cache
        assert _file_scores_cache[cache_key]["scored_files"] == mock_scored_files
        assert "timestamp" in _file_scores_cache[cache_key]

        mock_log_info.assert_called_once_with(
            f"Refreshing file scores with relevance scoring for {self.project_root}"
        )
        mock_log_debug.assert_called_once_with(
            f"Cached {len(mock_scored_files)} files with relevance scores "
            f"for {self.project_root}"
        )

    def test_get_files_with_scores_cached_valid(self):
        """Test getting files with scores when valid cache exists."""
        mock_scored_files = [
            ("aragorn_file.py", 0.8),
            ("legolas_file.py", 0.6),
        ]

        # Pre-populate cache with recent data
        cache_key = str(self.project_root)
        _file_scores_cache[cache_key] = {
            "scored_files": mock_scored_files,
            "timestamp": time.time() - 100,  # Recent timestamp
        }

        with patch("src.core.file_scoring.log_debug") as mock_log_debug:
            with patch("src.core.file_scoring.filter_project_files") as mock_filter:
                result = get_files_with_scores(self.project_root)

        assert result == mock_scored_files

        # No file filtering was called, cache was used
        mock_filter.assert_not_called()

        mock_log_debug.assert_called_once_with(
            f"Using cached file scores for {self.project_root}"
        )

    def test_get_files_with_scores_cached_expired(self):
        """Test getting files with scores when cache is expired."""
        old_scored_files = [("old_file.py", 0.3)]
        new_scored_files = [("new_file.py", 0.9)]

        # Pre-populate cache with expired data
        cache_key = str(self.project_root)
        _file_scores_cache[cache_key] = {
            "scored_files": old_scored_files,
            "timestamp": time.time() - MCP_CACHE_TTL - 100,  # Expired
        }

        with patch(
            "src.core.file_scoring.filter_project_files",
            return_value=["new_file.py"],
        ):
            with patch(
                "src.core.file_scoring._compute_relevance_scores",
                return_value=new_scored_files,
            ):
                with patch("src.core.file_scoring.log_info") as mock_log_info:
                    result = get_files_with_scores(self.project_root)

        # Should get new data, not old cached ones
        assert result == new_scored_files

        assert _file_scores_cache[cache_key]["scored_files"] == new_scored_files

        mock_log_info.assert_called_once()


class TestGetFilesList:
    """Test get_files_list function."""

    def setup_method(self):
        """Set up test fixtures."""
        _file_scores_cache.clear()
        self.project_root = Path("/tmp/test_project")

    def test_get_files_list(self):
        """Test getting file list without scores."""
        mock_scored_files = [
            ("gimli_file.py", 0.8),
            ("boromir_file.py", 0.6),
            ("faramir_file.py", 0.4),
        ]

        with patch(
            "src.core.file_scoring.get_files_with_scores",
            return_value=mock_scored_files,
        ):
            result = get_files_list(self.project_root)

        expected = ["gimli_file.py", "boromir_file.py", "faramir_file.py"]
        assert result == expected


class TestComputeRelevanceScores:
    """Test _compute_relevance_scores function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.project_root = Path("/tmp/test_project")
        self.mock_files = ["file1.py", "file2.py", "file3.py"]

    def test_compute_relevance_scores_success(self):
        """Test successful relevance score computation."""
        mock_scored_files = [
            ("file1.py", 0.9),
            ("file2.py", 0.7),
            ("file3.py", 0.5),
        ]

        mock_context_intel = Mock()
        mock_context_intel.rank_files.return_value = mock_scored_files

        with patch(
            "src.core.file_scoring.get_context_intelligence",
            return_value=mock_context_intel,
        ):
            result = _compute_relevance_scores(self.project_root, self.mock_files)

        assert result == mock_scored_files
        mock_context_intel.rank_files.assert_called_once_with(self.mock_files)

    def test_compute_relevance_scores_os_error(self):
        """Test relevance score computation with OS error."""
        with patch(
            "src.core.file_scoring.get_context_intelligence",
            side_effect=OSError("Permission denied"),
        ):
            with patch("src.core.file_scoring.log_debug") as mock_log_debug:
                result = _compute_relevance_scores(self.project_root, self.mock_files)

        # Should return neutral scores for all files
        expected = [(f, PRIORITY_NEUTRAL_SCORE) for f in self.mock_files]
        assert result == expected

        mock_log_debug.assert_called_once()
        assert "Context intelligence failed" in mock_log_debug.call_args[0][0]

    def test_compute_relevance_scores_value_error(self):
        """Test relevance score computation with value error."""
        with patch(
            "src.core.file_scoring.get_context_intelligence",
            side_effect=ValueError("Invalid configuration"),
        ):
            with patch("src.core.file_scoring.log_debug") as mock_log_debug:
                result = _compute_relevance_scores(self.project_root, self.mock_files)

        # Should return neutral scores for all files
        expected = [(f, PRIORITY_NEUTRAL_SCORE) for f in self.mock_files]
        assert result == expected
        mock_log_debug.assert_called_once()

    def test_compute_relevance_scores_attribute_error(self):
        """Test relevance score computation with attribute error."""
        with patch(
            "src.core.file_scoring.get_context_intelligence",
            side_effect=AttributeError("Missing method"),
        ):
            with patch("src.core.file_scoring.log_debug") as mock_log_debug:
                result = _compute_relevance_scores(self.project_root, self.mock_files)

        # Should return neutral scores for all files
        expected = [(f, PRIORITY_NEUTRAL_SCORE) for f in self.mock_files]
        assert result == expected
        mock_log_debug.assert_called_once()

    def test_compute_relevance_scores_import_error(self):
        """Test relevance score computation with import error."""
        with patch(
            "src.core.file_scoring.get_context_intelligence",
            side_effect=ImportError("Module not found"),
        ):
            with patch("src.core.file_scoring.log_debug") as mock_log_debug:
                result = _compute_relevance_scores(self.project_root, self.mock_files)

        # Should return neutral scores for all files
        expected = [(f, PRIORITY_NEUTRAL_SCORE) for f in self.mock_files]
        assert result == expected
        mock_log_debug.assert_called_once()


class TestClearFileScores:
    """Test clear_file_scores function."""

    def setup_method(self):
        """Set up test fixtures."""
        _file_scores_cache.clear()
        self.project_root1 = Path("/tmp/project1")
        self.project_root2 = Path("/tmp/project2")

        # Pre-populate cache
        _file_scores_cache[str(self.project_root1)] = {
            "scored_files": [("file1.py", 0.8)],
            "timestamp": time.time(),
        }
        _file_scores_cache[str(self.project_root2)] = {
            "scored_files": [("file2.py", 0.6)],
            "timestamp": time.time(),
        }

    def test_clear_file_scores_specific_project(self):
        """Test clearing file scores for a specific project."""
        with patch("src.core.file_scoring.log_debug") as mock_log_debug:
            clear_file_scores(self.project_root1)

        # Only project1 was cleared
        assert str(self.project_root1) not in _file_scores_cache
        assert str(self.project_root2) in _file_scores_cache

        mock_log_debug.assert_called_once_with(
            f"Cleared file scores for {self.project_root1}"
        )

    def test_clear_file_scores_nonexistent_project(self):
        """Test clearing file scores for a project not in cache."""
        nonexistent_project = Path("/tmp/nonexistent")

        with patch("src.core.file_scoring.log_debug") as mock_log_debug:
            clear_file_scores(nonexistent_project)

        assert len(_file_scores_cache) == 2

        # No logging for nonexistent project
        mock_log_debug.assert_not_called()

    def test_clear_file_scores_all_projects(self):
        """Test clearing file scores for all projects."""
        with patch("src.core.file_scoring.log_debug") as mock_log_debug:
            clear_file_scores()

        assert len(_file_scores_cache) == 0

        mock_log_debug.assert_called_once_with("Cleared all file scores")


class TestGetScoringInfo:
    """Test get_scoring_info function."""

    def setup_method(self):
        """Set up test fixtures."""
        _file_scores_cache.clear()
        self.project_root = Path("/tmp/test_project")

    def test_get_scoring_info_cached(self):
        """Test getting scoring info when data is cached."""
        mock_scored_files = [
            ("denethor_file.py", 0.9),
            ("theoden_file.py", 0.7),
            ("elrond_file.py", 0.5),
        ]

        cache_timestamp = time.time() - 1800  # 30 minutes ago
        cache_key = str(self.project_root)
        _file_scores_cache[cache_key] = {
            "scored_files": mock_scored_files,
            "timestamp": cache_timestamp,
        }

        current_time = time.time()
        with patch("time.time", return_value=current_time):
            result = get_scoring_info(self.project_root)

        cache_age = current_time - cache_timestamp
        expected = {
            "cached": True,
            "scored_files_count": 3,
            "age_seconds": cache_age,
            "age_minutes": cache_age / 60,
            "ttl_seconds": MCP_CACHE_TTL,
            "expires_in_seconds": MCP_CACHE_TTL - cache_age,
            "expires_in_minutes": (MCP_CACHE_TTL - cache_age) / 60,
        }

        assert result == expected

    def test_get_scoring_info_not_cached(self):
        """Test getting scoring info when no data is cached."""
        result = get_scoring_info(self.project_root)

        expected = {
            "cached": False,
            "scored_files_count": 0,
            "age_seconds": 0,
            "ttl_seconds": MCP_CACHE_TTL,
        }

        assert result == expected


class TestIntegrationScenarios:
    """Test integration scenarios for file scoring."""

    def setup_method(self):
        """Set up test fixtures."""
        _file_scores_cache.clear()
        self.project_root = Path("/tmp/test_project")

    def test_full_workflow_no_cache_to_cached(self):
        """Test complete workflow from no cache to cached results."""
        mock_files = ["galadriel_file.py", "celeborn_file.py"]
        mock_scored_files = [
            ("galadriel_file.py", 0.95),
            ("celeborn_file.py", 0.85),
        ]

        with patch(
            "src.core.file_scoring.filter_project_files",
            return_value=mock_files,
        ):
            with patch(
                "src.core.file_scoring._compute_relevance_scores",
                return_value=mock_scored_files,
            ):
                with patch("src.core.file_scoring.log_info"):
                    with patch("src.core.file_scoring.log_debug"):
                        # First call - should compute and cache
                        result1 = get_files_with_scores(self.project_root)
                        assert result1 == mock_scored_files

                        assert str(self.project_root) in _file_scores_cache

                        # Second call - should use cache
                        result2 = get_files_with_scores(self.project_root)
                        assert result2 == mock_scored_files

                        # Get file list (should extract from cached scores)
                        file_list = get_files_list(self.project_root)
                        assert file_list == [
                            "galadriel_file.py",
                            "celeborn_file.py",
                        ]

    def test_cache_expiration_and_refresh(self):
        """Test cache expiration and automatic refresh."""
        old_files = [("old_file.py", 0.3)]
        new_files = ["new_file.py"]
        new_scored_files = [("new_file.py", 0.9)]

        # Pre-populate with expired cache
        cache_key = str(self.project_root)
        _file_scores_cache[cache_key] = {
            "scored_files": old_files,
            "timestamp": time.time() - MCP_CACHE_TTL - 100,
        }

        with patch(
            "src.core.file_scoring.filter_project_files",
            return_value=new_files,
        ):
            with patch(
                "src.core.file_scoring._compute_relevance_scores",
                return_value=new_scored_files,
            ):
                with patch("src.core.file_scoring.log_info"):
                    result = get_files_with_scores(self.project_root)

        # Should get new results, not old cached ones
        assert result == new_scored_files
        assert _file_scores_cache[cache_key]["scored_files"] == new_scored_files

    def test_error_handling_with_fallback(self):
        """Test error handling with fallback to neutral scores."""
        mock_files = ["error_file.py", "another_file.py"]

        with patch(
            "src.core.file_scoring.filter_project_files",
            return_value=mock_files,
        ):
            with patch(
                "src.core.file_scoring.get_context_intelligence",
                side_effect=OSError("System error"),
            ):
                with patch("src.core.file_scoring.log_debug"):
                    with patch("src.core.file_scoring.log_info"):
                        result = get_files_with_scores(self.project_root)

        # Should get neutral scores for all files
        expected = [(f, PRIORITY_NEUTRAL_SCORE) for f in mock_files]
        assert result == expected

    def test_cache_management_workflow(self):
        """Test cache management operations."""
        mock_scored_files = [("cache_file.py", 0.8)]

        # Populate cache
        with patch(
            "src.core.file_scoring.filter_project_files",
            return_value=["cache_file.py"],
        ):
            with patch(
                "src.core.file_scoring._compute_relevance_scores",
                return_value=mock_scored_files,
            ):
                with patch("src.core.file_scoring.log_info"):
                    with patch("src.core.file_scoring.log_debug"):
                        get_files_with_scores(self.project_root)

        assert str(self.project_root) in _file_scores_cache

        # Get scoring info
        info = get_scoring_info(self.project_root)
        assert info["cached"] is True
        assert info["scored_files_count"] == 1

        # Clear cache
        with patch("src.core.file_scoring.log_debug"):
            clear_file_scores(self.project_root)

        assert str(self.project_root) not in _file_scores_cache

        # Get scoring info after clear
        info_after = get_scoring_info(self.project_root)
        assert info_after["cached"] is False
        assert info_after["scored_files_count"] == 0


class TestCacheManagement:
    """Test cache-specific functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        _file_scores_cache.clear()

    def test_cache_isolation_between_projects(self):
        """Test that cache is properly isolated between projects."""
        project1 = Path("/tmp/project1")
        project2 = Path("/tmp/project2")

        files1 = [("project1_file.py", 0.8)]
        files2 = [("project2_file.py", 0.6)]

        # Populate cache for both projects
        with patch("src.core.file_scoring.filter_project_files") as mock_filter:
            with patch(
                "src.core.file_scoring._compute_relevance_scores"
            ) as mock_compute:
                with patch("src.core.file_scoring.log_info"):
                    with patch("src.core.file_scoring.log_debug"):
                        # Project 1
                        mock_filter.return_value = ["project1_file.py"]
                        mock_compute.return_value = files1
                        result1 = get_files_with_scores(project1)

                        # Project 2
                        mock_filter.return_value = ["project2_file.py"]
                        mock_compute.return_value = files2
                        result2 = get_files_with_scores(project2)

        assert result1 == files1
        assert result2 == files2

        # Both are cached independently
        assert str(project1) in _file_scores_cache
        assert str(project2) in _file_scores_cache
        assert _file_scores_cache[str(project1)]["scored_files"] == files1
        assert _file_scores_cache[str(project2)]["scored_files"] == files2

        # Clear one project, verify other remains
        with patch("src.core.file_scoring.log_debug"):
            clear_file_scores(project1)

        assert str(project1) not in _file_scores_cache
        assert str(project2) in _file_scores_cache
