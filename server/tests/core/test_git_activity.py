"""Test git activity tracking functionality."""

import subprocess
import time
from pathlib import Path
from unittest.mock import Mock, patch

from src.core.git_activity import (
    CONTEXT_MIN_SCORE,
    GIT_ACTIVITY_CACHE_TTL,
    GIT_ACTIVITY_COMMIT_LIMIT,
    GIT_ACTIVITY_RECENT_DAYS,
    GitActivityTracker,
)


class TestGitActivityTracker:
    """Test GitActivityTracker class functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.project_root = Path("/tmp/test_project")
        self.tracker = GitActivityTracker(self.project_root)

    def test_init(self):
        """Test GitActivityTracker initialization."""
        assert self.tracker.project_root == self.project_root
        assert self.tracker._activity_data == {}
        assert self.tracker._last_update == 0

    def test_get_activity_score_no_data(self):
        """Test getting activity score when no data is available."""
        with patch.object(self.tracker, "_refresh_activity_data"):
            score = self.tracker.get_activity_score("test_file.py")
            assert score == CONTEXT_MIN_SCORE

    def test_get_activity_score_with_data(self):
        """Test getting activity score when data is available."""
        self.tracker._activity_data = {
            "frodo_file.py": 0.8,
            "sam_file.py": 0.6,
        }
        self.tracker._last_update = time.time()

        score = self.tracker.get_activity_score("frodo_file.py")
        assert score == 0.8

        score = self.tracker.get_activity_score("sam_file.py")
        assert score == 0.6

        # Test file not in data
        score = self.tracker.get_activity_score("unknown_file.py")
        assert score == CONTEXT_MIN_SCORE

    def test_get_activity_score_cache_expired(self):
        """Test activity score refresh when cache is expired."""
        # Set expired timestamp
        self.tracker._last_update = time.time() - GIT_ACTIVITY_CACHE_TTL - 1

        with patch.object(self.tracker, "_refresh_activity_data") as mock_refresh:
            self.tracker.get_activity_score("test_file.py")
            mock_refresh.assert_called_once()

    def test_get_activity_score_cache_valid(self):
        """Test activity score without refresh when cache is valid."""
        # Set recent timestamp
        self.tracker._last_update = time.time() - 100

        with patch.object(self.tracker, "_refresh_activity_data") as mock_refresh:
            self.tracker.get_activity_score("test_file.py")
            mock_refresh.assert_not_called()

    def test_get_activity_score_exception_handling(self):
        """Test exception handling in get_activity_score."""
        with patch.object(
            self.tracker,
            "_refresh_activity_data",
            side_effect=subprocess.SubprocessError("Git error"),
        ):
            score = self.tracker.get_activity_score("test_file.py")
            assert score == CONTEXT_MIN_SCORE

        with patch.object(
            self.tracker,
            "_refresh_activity_data",
            side_effect=OSError("System error"),
        ):
            score = self.tracker.get_activity_score("test_file.py")
            assert score == CONTEXT_MIN_SCORE

        with patch.object(
            self.tracker,
            "_refresh_activity_data",
            side_effect=subprocess.TimeoutExpired("git", 10),
        ):
            score = self.tracker.get_activity_score("test_file.py")
            assert score == CONTEXT_MIN_SCORE


class TestRefreshActivityData:
    """Test the _refresh_activity_data method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.project_root = Path("/tmp/test_project")
        self.tracker = GitActivityTracker(self.project_root)

    def test_refresh_activity_data_success(self):
        """Test successful git activity data refresh."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = (
            "frodo_file.py\n"
            "sam_file.py\n"
            "frodo_file.py\n"
            "gandalf_file.py\n"
            "frodo_file.py\n"
            "\n"  # Empty line should be filtered
        )

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            with patch("src.core.git_activity.log_info") as mock_log_info:
                self.tracker._refresh_activity_data()

        # Verify git command was called correctly
        mock_run.assert_called_once_with(
            [
                "git",
                "log",
                "--name-only",
                "--pretty=format:",
                f"--since={GIT_ACTIVITY_RECENT_DAYS} days ago",
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=GIT_ACTIVITY_COMMIT_LIMIT,
        )

        # Verify activity data was normalized correctly
        # frodo_file.py appears 3 times (max), so score = 1.0
        # sam_file.py appears 1 time, so score = 1/3 ≈ 0.333
        # gandalf_file.py appears 1 time, so score = 1/3 ≈ 0.333
        assert self.tracker._activity_data["frodo_file.py"] == 1.0
        assert (
            abs(self.tracker._activity_data["sam_file.py"] - 0.3333333333333333) < 0.001
        )
        assert (
            abs(self.tracker._activity_data["gandalf_file.py"] - 0.3333333333333333)
            < 0.001
        )

        # Verify timestamp was updated
        assert self.tracker._last_update > 0

        # Verify logging
        mock_log_info.assert_called_once_with(
            "Git activity data refreshed: 3 active files"
        )

    def test_refresh_activity_data_empty_output(self):
        """Test refresh with empty git output."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            with patch("src.core.git_activity.log_info") as mock_log_info:
                self.tracker._refresh_activity_data()

        # Should handle empty output gracefully
        assert self.tracker._activity_data == {}
        assert self.tracker._last_update > 0
        mock_log_info.assert_called_once_with(
            "Git activity data refreshed: 0 active files"
        )

    def test_refresh_activity_data_git_failure(self):
        """Test refresh when git command fails."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "fatal: not a git repository"

        with patch("subprocess.run", return_value=mock_result):
            with patch("src.core.git_activity.log_debug") as mock_log_debug:
                self.tracker._refresh_activity_data()

        # Should not update activity data on failure
        assert self.tracker._activity_data == {}
        assert self.tracker._last_update == 0

        # Should log the error
        mock_log_debug.assert_called_once_with(
            "Git log command failed: fatal: not a git repository"
        )

    def test_refresh_activity_data_subprocess_error(self):
        """Test refresh with subprocess error."""
        with patch(
            "subprocess.run",
            side_effect=subprocess.SubprocessError("Command failed"),
        ):
            with patch("src.core.git_activity.log_debug") as mock_log_debug:
                with patch("src.core.git_activity.log_error") as mock_log_error:
                    self.tracker._refresh_activity_data()

        # Should not crash and should log error
        assert self.tracker._activity_data == {}
        assert self.tracker._last_update == 0
        mock_log_debug.assert_called_once()
        mock_log_error.assert_called_once()

    def test_refresh_activity_data_timeout(self):
        """Test refresh with timeout error."""
        timeout_error = subprocess.TimeoutExpired("git", 10)

        with patch("subprocess.run", side_effect=timeout_error):
            with patch("src.core.git_activity.log_debug") as mock_log_debug:
                with patch("src.core.git_activity.log_error") as mock_log_error:
                    self.tracker._refresh_activity_data()

        # Should handle timeout gracefully
        assert self.tracker._activity_data == {}
        assert self.tracker._last_update == 0
        mock_log_debug.assert_called_once()
        mock_log_error.assert_called_once()

    def test_refresh_activity_data_os_error(self):
        """Test refresh with OS error."""
        with patch("subprocess.run", side_effect=OSError("Permission denied")):
            with patch("src.core.git_activity.log_debug") as mock_log_debug:
                with patch("src.core.git_activity.log_error") as mock_log_error:
                    self.tracker._refresh_activity_data()

        # Should handle OS error gracefully
        assert self.tracker._activity_data == {}
        assert self.tracker._last_update == 0
        mock_log_debug.assert_called_once()
        mock_log_error.assert_called_once()

    def test_refresh_activity_data_value_error(self):
        """Test refresh with value error."""
        with patch("subprocess.run", side_effect=ValueError("Invalid value")):
            with patch("src.core.git_activity.log_debug") as mock_log_debug:
                with patch("src.core.git_activity.log_error") as mock_log_error:
                    self.tracker._refresh_activity_data()

        # Should handle value error gracefully
        assert self.tracker._activity_data == {}
        assert self.tracker._last_update == 0
        mock_log_debug.assert_called_once()
        mock_log_error.assert_called_once()


class TestUtilityMethods:
    """Test utility methods of GitActivityTracker."""

    def setup_method(self):
        """Set up test fixtures."""
        self.project_root = Path("/tmp/test_project")
        self.tracker = GitActivityTracker(self.project_root)

    def test_clear_activity_data(self):
        """Test clearing activity data."""
        self.tracker._activity_data = {"file1.py": 0.8, "file2.py": 0.6}
        self.tracker._last_update = time.time()

        with patch("src.core.git_activity.log_debug") as mock_log_debug:
            self.tracker.clear_activity_data()

        assert self.tracker._activity_data == {}
        assert self.tracker._last_update == 0

        mock_log_debug.assert_called_once_with(
            f"Cleared git activity data for {self.project_root}"
        )

    def test_get_activity_info_no_data(self):
        """Test getting activity info when no data exists."""
        current_time = time.time()

        with patch("time.time", return_value=current_time):
            info = self.tracker.get_activity_info()

        expected = {
            "has_data": False,
            "file_count": 0,
            "age_seconds": current_time,
            "age_minutes": current_time / 60,
            "ttl_seconds": GIT_ACTIVITY_CACHE_TTL,
            "expires_in_seconds": GIT_ACTIVITY_CACHE_TTL - current_time,
            "expires_in_minutes": (GIT_ACTIVITY_CACHE_TTL - current_time) / 60,
        }

        assert info == expected

    def test_get_activity_info_with_data(self):
        """Test getting activity info when data exists."""
        self.tracker._activity_data = {
            "aragorn_file.py": 0.9,
            "legolas_file.py": 0.7,
            "gimli_file.py": 0.5,
        }
        update_time = time.time() - 1800  # 30 minutes ago
        self.tracker._last_update = update_time

        current_time = time.time()

        with patch("time.time", return_value=current_time):
            info = self.tracker.get_activity_info()

        data_age = current_time - update_time

        expected = {
            "has_data": True,
            "file_count": 3,
            "age_seconds": data_age,
            "age_minutes": data_age / 60,
            "ttl_seconds": GIT_ACTIVITY_CACHE_TTL,
            "expires_in_seconds": GIT_ACTIVITY_CACHE_TTL - data_age,
            "expires_in_minutes": (GIT_ACTIVITY_CACHE_TTL - data_age) / 60,
        }

        assert info == expected


class TestConstants:
    """Test module constants are properly defined."""

    def test_constants_exist(self):
        """Test that all required constants are defined."""
        assert GIT_ACTIVITY_CACHE_TTL == 3600
        assert GIT_ACTIVITY_RECENT_DAYS == 7
        assert GIT_ACTIVITY_COMMIT_LIMIT == 10
        assert CONTEXT_MIN_SCORE == 0.0

    def test_constants_types(self):
        """Test that constants have correct types."""
        assert isinstance(GIT_ACTIVITY_CACHE_TTL, int)
        assert isinstance(GIT_ACTIVITY_RECENT_DAYS, int)
        assert isinstance(GIT_ACTIVITY_COMMIT_LIMIT, int)
        assert isinstance(CONTEXT_MIN_SCORE, float)


class TestIntegrationScenarios:
    """Test integration scenarios for GitActivityTracker."""

    def setup_method(self):
        """Set up test fixtures."""
        self.project_root = Path("/tmp/test_project")
        self.tracker = GitActivityTracker(self.project_root)

    def test_full_workflow_success(self):
        """Test complete workflow from initialization to score retrieval."""
        # Mock git output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "boromir_file.py\nfaramir_file.py\nboromir_file.py\n"

        with patch("subprocess.run", return_value=mock_result):
            with patch("src.core.git_activity.log_info"):
                # First call should trigger refresh
                score1 = self.tracker.get_activity_score("boromir_file.py")
                score2 = self.tracker.get_activity_score("faramir_file.py")
                score3 = self.tracker.get_activity_score("unknown_file.py")

        # Verify scores
        assert score1 == 1.0  # boromir_file.py appears twice (max)
        assert score2 == 0.5  # faramir_file.py appears once
        assert score3 == CONTEXT_MIN_SCORE  # unknown file

        # Second call should use cache (no subprocess call)
        with patch("subprocess.run") as mock_run:
            score4 = self.tracker.get_activity_score("boromir_file.py")
            mock_run.assert_not_called()
            assert score4 == 1.0

    def test_error_recovery_workflow(self):
        """Test workflow with error recovery."""
        # First call fails
        with patch(
            "subprocess.run",
            side_effect=subprocess.SubprocessError("Git error"),
        ):
            with patch("src.core.git_activity.log_debug"):
                with patch("src.core.git_activity.log_error"):
                    score1 = self.tracker.get_activity_score("test_file.py")
                    assert score1 == CONTEXT_MIN_SCORE

        # Second call succeeds
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test_file.py\n"

        # Expire cache to force refresh
        self.tracker._last_update = time.time() - GIT_ACTIVITY_CACHE_TTL - 1

        with patch("subprocess.run", return_value=mock_result):
            with patch("src.core.git_activity.log_info"):
                score2 = self.tracker.get_activity_score("test_file.py")
                assert score2 == 1.0

    def test_cache_expiration_workflow(self):
        """Test cache expiration and refresh workflow."""
        # Initial data
        mock_result1 = Mock()
        mock_result1.returncode = 0
        mock_result1.stdout = "old_file.py\n"

        with patch("subprocess.run", return_value=mock_result1):
            with patch("src.core.git_activity.log_info"):
                score1 = self.tracker.get_activity_score("old_file.py")
                assert score1 == 1.0

        # Expire cache
        self.tracker._last_update = time.time() - GIT_ACTIVITY_CACHE_TTL - 1

        # Data after cache expiration (completely different files)
        mock_result2 = Mock()
        mock_result2.returncode = 0
        mock_result2.stdout = "new_file.py\n"

        with patch("subprocess.run", return_value=mock_result2):
            with patch("src.core.git_activity.log_info"):
                score2 = self.tracker.get_activity_score("new_file.py")
                score3 = self.tracker.get_activity_score("old_file.py")

        # File should have score, old file should be gone from data
        assert score2 == 1.0
        # Note: old_file.py is not in the new git output, so it gets min score
        assert score3 == CONTEXT_MIN_SCORE
