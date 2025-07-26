"""
Context intelligence for file scoring and project analysis.
"""

import time
from pathlib import Path
from typing import Any

from src.config.conversation_config import (
    CONTEXT_FILE_SIZE_ACCEPTABLE_MAX,
    CONTEXT_TOP_FILES_COUNT,
)
from src.config.core_constants import CONTEXT_MIN_SCORE
from src.config.weights import WeightsManager
from src.core.git_activity import GitActivityTracker
from src.utils.common import log_debug


class ContextIntelligence:
    """Context scoring and prioritization system."""

    def __init__(self, project_root: Path, weights_config: Any | None = None):
        """Initialize context intelligence for a project."""
        self.project_root = project_root
        self._import_cache: dict[str, Any] = {}

        # dependency injection, great, this is a good idea me
        self.weights = weights_config or WeightsManager.get_default()

        self.git_tracker = GitActivityTracker(project_root)

        log_debug(f"Initialized context intelligence for {project_root}")

    def score_file_relevance(
        self, file_path: str, context: dict[str, Any] | None = None
    ) -> float:
        """Calculate relevance score for a file."""
        try:
            full_path = self.project_root / file_path
            score = CONTEXT_MIN_SCORE

            if not full_path.exists():
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

            return max(score, CONTEXT_MIN_SCORE)

        except (OSError, FileNotFoundError):
            return CONTEXT_MIN_SCORE

    def _score_recent_modification(self, full_path: Path) -> float:
        """Score based on recent file modifications."""
        try:
            mod_time = full_path.stat().st_mtime
            now = time.time()
            hours_ago = (now - mod_time) / 3600

            context_weights = self.weights.get_dict("weights")
            recent_hour_threshold = self.weights.get(
                "context.recent_modifications.hour_threshold"
            )
            recent_day_threshold = self.weights.get(
                "context.recent_modifications.day_threshold"
            )
            recent_week_threshold = self.weights.get(
                "context.recent_modifications.week_threshold"
            )
            recent_day_multiplier = float(
                self.weights.get("context.recent_modifications.day_multiplier")
            )
            recent_week_multiplier = float(
                self.weights.get("context.recent_modifications.week_multiplier")
            )

            if hours_ago < recent_hour_threshold:
                return float(
                    context_weights.get("recent_modification", CONTEXT_MIN_SCORE)
                )
            elif hours_ago < recent_day_threshold:
                return (
                    float(context_weights.get("recent_modification", CONTEXT_MIN_SCORE))
                    * recent_day_multiplier
                )
            elif hours_ago < recent_week_threshold:
                return (
                    float(context_weights.get("recent_modification", CONTEXT_MIN_SCORE))
                    * recent_week_multiplier
                )
            else:
                return CONTEXT_MIN_SCORE

        except (OSError, FileNotFoundError):
            return CONTEXT_MIN_SCORE

    def _score_file_size(self, full_path: Path) -> float:
        """Score based on optimal file size for analysis."""
        try:
            size = full_path.stat().st_size

            context_weights = self.weights.get_dict("weights")
            optimal_min = self.weights.get("context.file_size.optimal_min")
            optimal_max = self.weights.get("context.file_size.optimal_max")
            acceptable_multiplier = float(
                self.weights.get("context.file_size.acceptable_multiplier")
            )
            large_multiplier = float(
                self.weights.get("context.file_size.large_multiplier")
            )

            if optimal_min <= size <= optimal_max:
                return float(
                    context_weights.get("file_size_optimal", CONTEXT_MIN_SCORE)
                )
            elif optimal_max < size <= CONTEXT_FILE_SIZE_ACCEPTABLE_MAX:
                return (
                    float(context_weights.get("file_size_optimal", CONTEXT_MIN_SCORE))
                    * acceptable_multiplier
                )
            elif size > CONTEXT_FILE_SIZE_ACCEPTABLE_MAX:
                return (
                    float(context_weights.get("file_size_optimal", CONTEXT_MIN_SCORE))
                    * large_multiplier
                )
            else:
                return CONTEXT_MIN_SCORE

        except (OSError, FileNotFoundError):
            return CONTEXT_MIN_SCORE

    def _score_file_type(self, file_path: str) -> float:
        """Score based on file extension priority."""
        suffix = Path(file_path).suffix.lower()
        extension_score = self.weights.get_file_extension_weights().get(
            suffix, CONTEXT_MIN_SCORE
        )
        context_weights = self.weights.get_dict("weights")
        return extension_score * float(
            context_weights.get("file_type_priority", CONTEXT_MIN_SCORE)
        )

    def _score_directory_importance(self, file_path: str) -> float:
        """Score based on directory importance."""
        parts = Path(file_path).parts
        score = 0.0

        context_weights = self.weights.get_dict("weights")
        directory_weights = self.weights.get_directory_priority_weights()

        for part in parts[:-1]:  # Exclude filename
            dir_score = directory_weights.get(part.lower(), CONTEXT_MIN_SCORE)
            score += dir_score * float(
                context_weights.get("directory_importance", CONTEXT_MIN_SCORE)
            )

        return score

    def _score_git_activity(self, file_path: str) -> float:
        """Score based on recent git activity using GitActivityTracker."""
        try:
            activity_score = self.git_tracker.get_activity_score(file_path)
            context_weights = self.weights.get_dict("weights")
            return activity_score * float(
                context_weights.get("git_activity", CONTEXT_MIN_SCORE)
            )
        except (AttributeError, TypeError):
            return CONTEXT_MIN_SCORE

    def _score_import_relationships(
        self, file_path: str, active_files: list[str]
    ) -> float:
        """Score based on import relationships with active files."""
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
        files: list[str],
        context: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> list[tuple[str, float]]:
        """Rank files by relevance score in descending order."""
        scored_files = []
        for file_path in files:
            score = self.score_file_relevance(file_path, context)
            scored_files.append((file_path, score))

        # Sort by score descending
        scored_files.sort(key=lambda x: x[1], reverse=True)

        if limit:
            scored_files = scored_files[:limit]

        # Add summary debug information instead of per-file logging
        if scored_files:
            log_debug(
                f"Ranked {len(scored_files)} files with relevance scores "
                f"for {self.project_root}"
            )

        return scored_files

    def get_context_summary(
        self, files: list[str], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Generate a comprehensive context summary for a set of files."""
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

        # Categorize files by priority
        high_priority = [f for f, s in scored_files if s >= 0.8]
        medium_priority = [f for f, s in scored_files if 0.5 <= s < 0.8]
        low_priority = [f for f, s in scored_files if s < 0.5]

        # Calculate average score
        average_score = (
            sum(score for _, score in scored_files) / len(scored_files)
            if scored_files
            else 0.0
        )

        # Get top files for display
        top_files = scored_files[:CONTEXT_TOP_FILES_COUNT]

        # Generate file type distribution
        file_type_dist: dict[str, int] = {}
        for file_path in files:
            suffix = Path(file_path).suffix.lower()
            if suffix:
                file_type_dist[suffix] = file_type_dist.get(suffix, 0) + 1

        return {
            "file_count": len(files),
            "priority_distribution": {
                "high": len(high_priority),
                "medium": len(medium_priority),
                "low": len(low_priority),
            },
            "file_type_distribution": file_type_dist,
            "total_files": len(scored_files),
            "high_priority_files": len(high_priority),
            "medium_priority_files": len(medium_priority),
            "low_priority_files": len(low_priority),
            "average_score": average_score,
            "top_files": [(path, f"{score:.3f}") for path, score in top_files],
        }


# Module-level cache for ContextIntelligence instances
_context_cache: dict[str, ContextIntelligence] = {}


def get_context_intelligence(
    project_root: Path, weights_config: Any | None = None
) -> ContextIntelligence:
    """Get context intelligence instance for a project."""
    cache_key = str(project_root)
    if cache_key not in _context_cache:
        _context_cache[cache_key] = ContextIntelligence(project_root, weights_config)
    return _context_cache[cache_key]
