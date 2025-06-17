"""
Helpful git operations.
"""

import json
from pathlib import Path
from typing import Any, Dict

from src.git_operations import get_git_status, get_git_commit_history, get_git_branches, get_git_diff
from config.constants import (
    GIT_INCLUDE_UNTRACKED, GIT_VERBOSE, 
    GIT_INCLUDE_MERGED, GIT_COMMIT_LIMIT, GIT_TIMEOUT, GIT_BRANCH_TIMEOUT
)


def handle_git_status(arguments: Dict[str, Any], project_root: Path) -> Dict[str, Any]:
    """Handle get_git_status tool call."""
    include_untracked = arguments.get("include_untracked", GIT_INCLUDE_UNTRACKED)
    verbose = arguments.get("verbose", GIT_VERBOSE)
    
    status_result = get_git_status(project_root, include_untracked, verbose)
    
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(status_result, indent=2)
            }
        ]
    }


def handle_git_commit_history(arguments: Dict[str, Any], project_root: Path) -> Dict[str, Any]:
    """Handle get_git_commit_history tool call."""
    limit = arguments.get("limit", GIT_COMMIT_LIMIT)
    since = arguments.get("since")
    author = arguments.get("author")
    branch = arguments.get("branch")
    timeout = arguments.get("timeout", GIT_TIMEOUT)
    
    history_result = get_git_commit_history(
        project_root,
        limit=limit,
        since=since,
        author=author,
        branch=branch,
        timeout=timeout
    )
    
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(history_result, indent=2)
            }
        ]
    }


def handle_git_branches(arguments: Dict[str, Any], project_root: Path) -> Dict[str, Any]:
    """Handle get_git_branches tool call."""
    include_remote = False  # Removed expensive remote branch fetching
    include_merged = arguments.get("include_merged", GIT_INCLUDE_MERGED)
    timeout = arguments.get("timeout", GIT_BRANCH_TIMEOUT)
    
    branches_result = get_git_branches(project_root, include_remote, include_merged, timeout)
    
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(branches_result, indent=2)
            }
        ]
    }


def handle_git_diff(arguments: Dict[str, Any], project_root: Path) -> Dict[str, Any]:
    """Handle get_git_diff tool call."""
    commit_hash = arguments.get("commit_hash")
    file_path = arguments.get("file_path")
    staged = arguments.get("staged", False)
    timeout = arguments.get("timeout", GIT_TIMEOUT)
    
    diff_result = get_git_diff(project_root, commit_hash, file_path, staged, timeout)
    
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(diff_result, indent=2)
            }
        ]
    }


# Tool registry for git operations
GIT_TOOL_HANDLERS = {
    "get_git_status": handle_git_status,
    "get_git_commit_history": handle_git_commit_history,
    "get_git_branches": handle_git_branches,
    "get_git_diff": handle_git_diff,
} 