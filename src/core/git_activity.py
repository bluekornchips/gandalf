"""
Git activity tracking for intelligent file scoring.
"""

import subprocess
import time
from pathlib import Path
from typing import Dict

from src.utils.common import log_debug, log_error, log_info

# Git activity constants (not in system config yet)
GIT_ACTIVITY_CACHE_TTL = 3600  # 1 hour cache
GIT_ACTIVITY_RECENT_DAYS = 7  # Look back 7 days
GIT_ACTIVITY_MAX_FILES = 1000  # Max files to track
GIT_ACTIVITY_COMMIT_LIMIT = 10  # Timeout for git commands

# Context scoring constants
CONTEXT_MIN_SCORE = 0.0  # Minimum score for files with no activity

# Global cache for git activity data
_git_activity_cache = {}
_git_activity_cache_time = {}


class GitActivityTracker:
    """Git activity tracker for file scoring."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._activity_data = {}
        self._last_update = 0

    def get_activity_score(self, file_path: str) -> float:
        """Get git activity score for a file."""
        try:
            if time.time() - self._last_update > GIT_ACTIVITY_CACHE_TTL:
                self._refresh_activity_data()

            return self._activity_data.get(file_path, CONTEXT_MIN_SCORE)

        except (
            OSError,
            subprocess.SubprocessError,
            subprocess.TimeoutExpired,
        ) as e:
            log_debug(f"Git activity error for {file_path}: {e}")
            return CONTEXT_MIN_SCORE

    def _refresh_activity_data(self):
        """Refresh git activity data with recent file modification data.

        Executes git log command to gather file activity over the configured
        lookback period. Results are normalized and stored for performance.

        Side Effects:
            - Updates self._activity_data with normalized scores
            - Updates self._last_update with current timestamp
            - Logs refresh status

        Raises:
            No exceptions raised; errors are logged and handled gracefully
        """
        try:
            log_debug(f"Refreshing git activity data for {self.project_root}")
            result = subprocess.run(
                [
                    "git",
                    "log",
                    f"--since={GIT_ACTIVITY_RECENT_DAYS} days ago",
                    "--name-only",
                    "--pretty=format:",
                    "--",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=GIT_ACTIVITY_COMMIT_LIMIT,
            )

            if result.returncode == 0:
                files = [
                    line.strip()
                    for line in result.stdout.split("\n")
                    if line.strip()
                ]
                file_counts = {}

                for file in files:
                    file_counts[file] = file_counts.get(file, 0) + 1

                # Normalize scores
                max_count = max(file_counts.values()) if file_counts else 1
                for file, count in file_counts.items():
                    self._activity_data[file] = count / max_count

                self._last_update = time.time()
                log_debug(
                    f"Refreshed git activity data with {len(file_counts)} files"
                )
                log_info(
                    f"Git activity data refreshed: {len(file_counts)} active files"
                )
            else:
                log_debug(f"Git log command failed: {result.stderr}")

        except (
            subprocess.SubprocessError,
            subprocess.TimeoutExpired,
            OSError,
            ValueError,
        ) as e:
            log_debug(f"Error refreshing git activity data: {e}")
            log_error(e, "Git activity refresh failed")

    def clear_activity_data(self):
        """Clear the git activity data."""
        self._activity_data.clear()
        self._last_update = 0
        log_debug(f"Cleared git activity data for {self.project_root}")

    def get_activity_info(self) -> Dict:
        """Get activity information for debugging."""
        current_time = time.time()
        data_age = current_time - self._last_update

        return {
            "has_data": bool(self._activity_data),
            "file_count": len(self._activity_data),
            "age_seconds": data_age,
            "age_minutes": data_age / 60,
            "ttl_seconds": GIT_ACTIVITY_CACHE_TTL,
            "expires_in_seconds": GIT_ACTIVITY_CACHE_TTL - data_age,
            "expires_in_minutes": (GIT_ACTIVITY_CACHE_TTL - data_age) / 60,
        }
