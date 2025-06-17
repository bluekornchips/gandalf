"""
Project operations tool handlers for MCP server.
Handles project information and metadata operations.
"""

import json
from pathlib import Path
from typing import Any, Dict

from src.git_operations import get_project_info
from src.tool_calls.file.file_cache import get_cached_files


def handle_project_info(arguments: Dict[str, Any], project_root: Path) -> Dict[str, Any]:
    """Handle get_project_info tool call."""
    include_stats = arguments.get("include_stats", True)
    
    project_info = get_project_info(project_root)
    
    if include_stats:
        files = get_cached_files(project_root)
        project_info["file_count"] = len(files)
    
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(project_info, indent=2)
            }
        ]
    }


# Tool registry for project operations
PROJECT_TOOL_HANDLERS = {
    "get_project_info": handle_project_info,
} 