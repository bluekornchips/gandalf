"""
Cursor query tool for accessing Cursor IDE conversation data.
"""

import json
from pathlib import Path
from typing import Any, Dict

from src.utils.common import log_error, log_info
from src.utils.cursor_chat_query import CursorQuery
from src.utils.security import SecurityValidator

# # Import cursor_chat_query from scripts directory
# scripts_dir = Path(__file__).resolve().parent.parent.parent.parent / "scripts"
# if str(scripts_dir) not in sys.path:
#     sys.path.insert(0, str(scripts_dir))


def handle_query_cursor_conversations(
    arguments: Dict[str, Any], project_root: Path, **kwargs
) -> Dict[str, Any]:
    """Query cursor conversations with comprehensive data retrieval."""
    try:
        # Get parameters
        format_type = arguments.get("format", "cursor")
        summary = arguments.get("summary", False)

        # Validate format
        if format_type not in ["json", "markdown", "cursor"]:
            return SecurityValidator.create_error_response(
                "format must be one of: json, markdown, cursor"
            )

        # Initialize query tool
        query_tool = CursorQuery(silent=True)

        # Query data
        log_info("Querying conversations from Cursor databases...")
        data = query_tool.query_all_conversations()

        if summary:
            # Return summary statistics only
            total_conversations = sum(
                len(ws["conversations"]) for ws in data["workspaces"]
            )
            total_prompts = sum(
                len(ws["prompts"]) for ws in data["workspaces"]
            )
            total_generations = sum(
                len(ws["generations"]) for ws in data["workspaces"]
            )

            # Get recent conversation names for preview
            recent_conversations = []
            for workspace in data["workspaces"]:
                for conversation in workspace["conversations"][
                    -3:
                ]:  # Last 3 per workspace
                    name = conversation.get("name", "Untitled")
                    if name and name != "Untitled":
                        recent_conversations.append(name)

            summary_data = {
                "workspaces": len(data["workspaces"]),
                "total_conversations": total_conversations,
                "total_prompts": total_prompts,
                "total_generations": total_generations,
                "query_timestamp": data["query_timestamp"],
                "recent_conversations": recent_conversations[:10],  # Top 10
            }

            log_info(
                f"Summary: {total_conversations} conversations across {len(data['workspaces'])} workspaces"
            )
            return SecurityValidator.create_success_response(
                json.dumps(summary_data, indent=2)
            )

        # Format output based on requested format
        if format_type == "markdown":
            content = query_tool.format_as_markdown(data)
        elif format_type == "cursor":
            content = query_tool.format_as_cursor_markdown(data)
        else:  # json
            content = json.dumps(data, indent=2)

        log_info(
            f"Queried {sum(len(ws['conversations']) for ws in data['workspaces'])} conversations in {format_type} format"
        )
        return SecurityValidator.create_success_response(content)

    except (OSError, ValueError, TypeError, KeyError, FileNotFoundError) as e:
        log_error(e, "query_cursor_conversations")
        return SecurityValidator.create_error_response(
            f"Error querying cursor conversations: {str(e)}"
        )


def handle_list_cursor_workspaces(
    arguments: Dict[str, Any], project_root: Path, **kwargs
) -> Dict[str, Any]:
    """List available Cursor workspace databases."""
    try:
        # Initialize query tool
        query_tool = CursorQuery(silent=True)

        # Find workspace databases
        workspace_dbs = query_tool.find_workspace_databases()

        # Format response
        workspaces = []
        for db_path in workspace_dbs:
            workspace_hash = db_path.parent.name
            workspaces.append(
                {
                    "hash": workspace_hash,
                    "path": str(db_path),
                    "exists": db_path.exists(),
                }
            )

        result = {
            "total_workspaces": len(workspaces),
            "workspaces": workspaces,
        }

        log_info(f"Found {len(workspaces)} workspace databases")
        return SecurityValidator.create_success_response(
            json.dumps(result, indent=2)
        )

    except (OSError, ValueError, PermissionError, FileNotFoundError) as e:
        log_error(e, "list_cursor_workspaces")
        return SecurityValidator.create_error_response(
            f"Error listing workspace databases: {str(e)}"
        )


TOOL_QUERY_CURSOR_CONVERSATIONS = {
    "name": "query_cursor_conversations",
    "description": "Query conversations directly from Cursor IDE databases for AI context analysis",
    "inputSchema": {
        "type": "object",
        "properties": {
            "format": {
                "type": "string",
                "enum": ["json", "markdown", "cursor"],
                "default": "cursor",
                "description": "Data format for AI analysis - 'cursor' matches Cursor's native format",
            },
            "summary": {
                "type": "boolean",
                "default": False,
                "description": "Return summary statistics instead of full conversation data",
            },
        },
        "required": [],
    },
    "annotations": {
        "title": "Query Cursor Conversations",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}

TOOL_LIST_CURSOR_WORKSPACES = {
    "name": "list_cursor_workspaces",
    "description": "List available Cursor workspace databases",
    "inputSchema": {"type": "object", "properties": {}, "required": []},
    "annotations": {
        "title": "List Cursor Workspaces",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}


CURSOR_QUERY_TOOL_HANDLERS = {
    "query_cursor_conversations": handle_query_cursor_conversations,
    "list_cursor_workspaces": handle_list_cursor_workspaces,
}

CURSOR_QUERY_TOOL_DEFINITIONS = [
    TOOL_QUERY_CURSOR_CONVERSATIONS,
    TOOL_LIST_CURSOR_WORKSPACES,
]
