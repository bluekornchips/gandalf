"""
Context intelligence for Gandalf MCP server.
"""

import time
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

from config.weights import (
    CONTEXT_WEIGHTS,
    get_file_extension_weights,
    get_directory_priority_weights,
)
from config.constants.system import (
    CONTEXT_MIN_SCORE,
    CONTEXT_FILE_SIZE_OPTIMAL_MIN,
    CONTEXT_FILE_SIZE_OPTIMAL_MAX,
    CONTEXT_FILE_SIZE_ACCEPTABLE_MAX,
    CONTEXT_FILE_SIZE_ACCEPTABLE_MULTIPLIER,
    CONTEXT_FILE_SIZE_LARGE_MULTIPLIER,
    CONTEXT_RECENT_HOUR_THRESHOLD,
    CONTEXT_RECENT_DAY_THRESHOLD,
    CONTEXT_RECENT_WEEK_THRESHOLD,
    CONTEXT_RECENT_DAY_MULTIPLIER,
    CONTEXT_RECENT_WEEK_MULTIPLIER,
    CONTEXT_HIGH_PRIORITY_THRESHOLD,
    CONTEXT_MEDIUM_PRIORITY_THRESHOLD,
    CONTEXT_TOP_FILES_COUNT,
)
from src.utils.common import log_info, log_debug
from src.core.git_activity import GitActivityTracker


class ContextIntelligence:
    """Context scoring and prioritization system."""

    def __init__(self, project_root: Path):
        """Initialize context intelligence for a project."""
        self.project_root = project_root
        self._import_cache = {}

        self.git_tracker = GitActivityTracker(project_root)

        self.weights = CONTEXT_WEIGHTS.copy()
        log_info(f"Initialized context intelligence for {project_root}")

    def score_file_relevance(
        self, file_path: str, context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate relevance score for a file."""
        try:
            full_path = self.project_root / file_path
            score = CONTEXT_MIN_SCORE

            if not full_path.exists():
                log_debug(f"File does not exist: {file_path}")
                return score

            recent_score = self._score_recent_modification(full_path)
            size_score = self._score_file_size(full_path)
            type_score = self._score_file_type(file_path)
            dir_score = self._score_directory_importance(file_path)
            git_score = self._score_git_activity(file_path)

            score = recent_score + size_score + type_score + dir_score + git_score

            if context and "active_files" in context:
                import_score = self._score_import_relationships(
                    file_path, context["active_files"]
                )
                score += import_score

            log_debug(
                f"Scored {file_path}: {score:.3f} (recent:{recent_score:.2f}, size:{size_score:.2f}, type:{type_score:.2f}, dir:{dir_score:.2f}, git:{git_score:.2f})"
            )
            return max(score, CONTEXT_MIN_SCORE)

        except (OSError, FileNotFoundError):
            return CONTEXT_MIN_SCORE

    def _score_recent_modification(self, full_path: Path) -> float:
        """Score based on recent file modifications."""
        try:
            mod_time = full_path.stat().st_mtime
            now = time.time()
            hours_ago = (now - mod_time) / 3600

            if hours_ago < CONTEXT_RECENT_HOUR_THRESHOLD:
                return self.weights["recent_modification"]
            elif hours_ago < CONTEXT_RECENT_DAY_THRESHOLD:
                return (
                    self.weights["recent_modification"] * CONTEXT_RECENT_DAY_MULTIPLIER
                )
            elif hours_ago < CONTEXT_RECENT_WEEK_THRESHOLD:
                return (
                    self.weights["recent_modification"] * CONTEXT_RECENT_WEEK_MULTIPLIER
                )
            else:
                return CONTEXT_MIN_SCORE

        except (OSError, FileNotFoundError):
            return CONTEXT_MIN_SCORE

    def _score_file_size(self, full_path: Path) -> float:
        """Score based on optimal file size for analysis."""
        try:
            size = full_path.stat().st_size

            if CONTEXT_FILE_SIZE_OPTIMAL_MIN <= size <= CONTEXT_FILE_SIZE_OPTIMAL_MAX:
                return self.weights["file_size_optimal"]
            elif (
                CONTEXT_FILE_SIZE_OPTIMAL_MAX < size <= CONTEXT_FILE_SIZE_ACCEPTABLE_MAX
            ):
                return (
                    self.weights["file_size_optimal"]
                    * CONTEXT_FILE_SIZE_ACCEPTABLE_MULTIPLIER
                )
            elif size > CONTEXT_FILE_SIZE_ACCEPTABLE_MAX:
                return (
                    self.weights["file_size_optimal"]
                    * CONTEXT_FILE_SIZE_LARGE_MULTIPLIER
                )
            else:
                return CONTEXT_MIN_SCORE

        except (OSError, FileNotFoundError):
            return CONTEXT_MIN_SCORE

    def _score_file_type(self, file_path: str) -> float:
        """Score based on file extension priority."""
        suffix = Path(file_path).suffix.lower()
        extension_score = get_file_extension_weights().get(
            suffix.lstrip("."), CONTEXT_MIN_SCORE
        )
        return extension_score * self.weights["file_type_priority"]

    def _score_directory_importance(self, file_path: str) -> float:
        """Score based on directory importance."""
        parts = Path(file_path).parts
        score = 0.0

        for part in parts[:-1]:  # Exclude filename
            dir_score = get_directory_priority_weights().get(
                part.lower(), CONTEXT_MIN_SCORE
            )
            score += dir_score * self.weights["directory_importance"]

        return score

    def _score_git_activity(self, file_path: str) -> float:
        """Score based on recent git activity using GitActivityTracker."""
        try:
            activity_score = self.git_tracker.get_activity_score(file_path)
            return activity_score * self.weights["git_activity"]
        except (AttributeError, TypeError):
            return CONTEXT_MIN_SCORE

    def _score_import_relationships(
        self, file_path: str, active_files: List[str]
    ) -> float:
        """Score based on import relationships with active files.

        Analyzes import statements to determine if this file is imported by
        or imports from files that are currently active in the editor.

        Args:
            file_path: Path to the file being scored
            active_files: List of currently active/open file paths

        Returns:
            float: Score based on import relationships (0.0 - 1.0)
        """
        if not active_files:
            return 0.0

        try:
            # Simple heuristic: look for file imports
            file_stem = Path(file_path).stem
            score = 0.0

            for active_file in active_files:
                active_stem = Path(active_file).stem
                if file_stem != active_stem:
                    # Basic import relationship detection
                    if file_stem in active_stem or active_stem in file_stem:
                        score += 0.3

            return min(score, 1.0)

        except (AttributeError, TypeError):
            return 0.0

    def rank_files(
        self,
        files: List[str],
        context: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[Tuple[str, float]]:
        """Rank files by relevance score in descending order.

        Applies context intelligence scoring to a list of files and returns
        them sorted by relevance score, optionally limited to top results.

        Args:
            files: List of file paths to rank
            context: Optional context information for enhanced scoring
            limit: Optional maximum number of results to return

        Returns:
            List[Tuple[str, float]]: Sorted list of (file_path, score) tuples

        Example:
            >>> ranked = context_intel.rank_files(['src/main.py', 'README.md'])
            >>> print(ranked[0])  # ('src/main.py', 0.85)
        """
        scored_files = []
        for file_path in files:
            score = self.score_file_relevance(file_path, context)
            scored_files.append((file_path, score))

        # Sort by score descending
        scored_files.sort(key=lambda x: x[1], reverse=True)

        if limit:
            scored_files = scored_files[:limit]

        return scored_files

    def get_context_summary(
        self, files: List[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a comprehensive context summary for a set of files.

        Analyzes the provided files and generates statistics about priority
        distribution, file types, and overall context characteristics.

        Args:
            files: List of file paths to analyze
            context: Optional context information for enhanced analysis

        Returns:
            Dict[str, Any]: Summary containing:
                - file_count: Total number of files
                - priority_distribution: Counts by priority level
                - file_type_distribution: Counts by file extension
                - average_score: Mean relevance score
                - top_files: Highest scoring files with scores

        Example:
            >>> summary = context_intel.get_context_summary(['src/main.py', 'test.py'])
            >>> print(summary['file_count'])  # 2
            >>> print(summary['average_score'])  # 0.73
        """
        if not files:
            return {
                "file_count": 0,
                "priority_distribution": {"high": 0, "medium": 0, "low": 0},
                "file_type_distribution": {},
                "average_score": 0.0,
                "top_files": [],
            }

        # Score all files
        scored_files = self.rank_files(files, context)

        # Calculate priority distribution
        priority_dist = {"high": 0, "medium": 0, "low": 0}
        file_type_dist = {}
        total_score = 0.0

        for file_path, score in scored_files:
            total_score += score

            # Categorize by priority
            if score >= CONTEXT_HIGH_PRIORITY_THRESHOLD:
                priority_dist["high"] += 1
            elif score >= CONTEXT_MEDIUM_PRIORITY_THRESHOLD:
                priority_dist["medium"] += 1
            else:
                priority_dist["low"] += 1

            # Track file types
            suffix = Path(file_path).suffix.lower()
            file_type_dist[suffix] = file_type_dist.get(suffix, 0) + 1

        # Get top files for display
        top_files = scored_files[:CONTEXT_TOP_FILES_COUNT]

        return {
            "file_count": len(files),
            "priority_distribution": priority_dist,
            "file_type_distribution": file_type_dist,
            "average_score": total_score / len(files) if files else 0.0,
            "top_files": [(path, f"{score:.3f}") for path, score in top_files],
        }


# Module-level cache for ContextIntelligence instances
_context_cache: Dict[str, ContextIntelligence] = {}


def get_context_intelligence(project_root: Path) -> ContextIntelligence:
    """Get or create a ContextIntelligence instance for a project."""
    cache_key = str(project_root)
    if cache_key not in _context_cache:
        _context_cache[cache_key] = ContextIntelligence(project_root)
    return _context_cache[cache_key]
