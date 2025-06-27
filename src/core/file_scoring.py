"""
File scoring and relevance ranking for the Gandalf MCP server.
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.config.constants.system import MCP_CACHE_TTL, PRIORITY_NEUTRAL_SCORE
from src.core.context_intelligence import get_context_intelligence
from src.core.project_filtering import filter_project_files
from src.utils.common import log_debug, log_info

_file_scores_cache: Dict[str, Dict] = {}


def get_files_with_scores(project_root: Path) -> List[Tuple[str, float]]:
    """Get files with pre-computed relevance scores."""
    cache_key = str(project_root)
    current_time = time.time()

    if (
        cache_key in _file_scores_cache
        and current_time - _file_scores_cache[cache_key]["timestamp"]
        < MCP_CACHE_TTL
    ):
        log_debug(f"Using cached file scores for {project_root}")
        return _file_scores_cache[cache_key]["scored_files"]

    log_info(
        f"Refreshing file scores with relevance scoring for {project_root}"
    )

    # Get raw file list and compute scores
    files = filter_project_files(project_root)
    scored_files = _compute_relevance_scores(project_root, files)

    # Store scored files
    _file_scores_cache[cache_key] = {
        "scored_files": scored_files,
        "timestamp": current_time,
    }

    log_debug(
        f"Cached {len(scored_files)} files with relevance scores for {project_root}"
    )
    return scored_files


def get_files_list(project_root: Path) -> List[str]:
    """Get file list without scores."""
    scored_files = get_files_with_scores(project_root)
    return [file_path for file_path, score in scored_files]


def _compute_relevance_scores(
    project_root: Path, files: List[str]
) -> List[Tuple[str, float]]:
    """Compute relevance scores for files during refresh."""
    try:
        context_intel = get_context_intelligence(project_root)
        scored_files = context_intel.rank_files(files)
        return [(f, score) for f, score in scored_files]
    except (OSError, ValueError, AttributeError, ImportError) as e:
        log_debug(
            f"Context intelligence failed for {project_root}: {e}, using neutral scores"
        )
        # Fallback to neutral scores if context intelligence fails
        return [(f, PRIORITY_NEUTRAL_SCORE) for f in files]


def clear_file_scores(project_root: Optional[Path] = None) -> None:
    """Clear file scores for specific project or all projects."""
    if project_root:
        cache_key = str(project_root)
        if cache_key in _file_scores_cache:
            del _file_scores_cache[cache_key]
            log_debug(f"Cleared file scores for {project_root}")
    else:
        _file_scores_cache.clear()
        log_debug("Cleared all file scores")


def get_scoring_info(project_root: Path) -> Dict[str, Any]:
    """Get scoring information for debugging."""
    cache_key = str(project_root)
    current_time = time.time()

    if cache_key in _file_scores_cache:
        cache_age = current_time - _file_scores_cache[cache_key]["timestamp"]
        cache_data = _file_scores_cache[cache_key]
        return {
            "cached": True,
            "scored_files_count": len(cache_data["scored_files"]),
            "age_seconds": cache_age,
            "age_minutes": cache_age / 60,
            "ttl_seconds": MCP_CACHE_TTL,
            "expires_in_seconds": MCP_CACHE_TTL - cache_age,
            "expires_in_minutes": (MCP_CACHE_TTL - cache_age) / 60,
        }
    else:
        return {
            "cached": False,
            "scored_files_count": 0,
            "age_seconds": 0,
            "ttl_seconds": MCP_CACHE_TTL,
        }
