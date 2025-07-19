"""
Cursor query tool for accessing Cursor IDE conversation data.
"""

import json
from pathlib import Path
from typing import Any

from src.utils.access_control import AccessValidator
from src.utils.common import log_error, log_info
from src.utils.cursor_chat_query import CursorQuery, list_cursor_workspaces


def handle_query_cursor_conversations(
    arguments: dict[str, Any], project_root: Path, **kwargs
) -> dict[str, Any]:
    """Query cursor conversations with comprehensive data retrieval."""
    try:
        # Get parameters
        format_type = arguments.get("format", "cursor")
        summary = arguments.get("summary", False)

        # Validate format
        if format_type not in ["json", "markdown", "cursor"]:
            return AccessValidator.create_error_response(
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
            total_prompts = sum(len(ws["prompts"]) for ws in data["workspaces"])
            total_generations = sum(len(ws["generations"]) for ws in data["workspaces"])

            # Get recent conversation names for preview, sorted by lastUpdatedAt
            all_conversations = []
            for workspace in data["workspaces"]:
                for conversation in workspace["conversations"]:
                    # Add lastUpdatedAt for sorting, default to 0 if missing
                    last_updated = conversation.get("lastUpdatedAt", 0)
                    all_conversations.append(
                        {
                            "name": conversation.get("name", "Untitled"),
                            "lastUpdatedAt": last_updated,
                        }
                    )

            all_conversations.sort(key=lambda x: x["lastUpdatedAt"], reverse=True)

            # Get the most recent conversation names, excluding "Untitled"
            recent_conversations = []
            for conv in all_conversations:
                name = conv["name"]
                if name and name != "Untitled":
                    recent_conversations.append(name)
                if len(recent_conversations) >= 10:  # Limit to 10
                    break

            summary_data = {
                "workspaces": len(data["workspaces"]),
                "total_conversations": total_conversations,
                "total_prompts": total_prompts,
                "total_generations": total_generations,
                "query_timestamp": data["query_timestamp"],
                "recent_conversations": recent_conversations,
            }

            log_info(
                f"Summary: {total_conversations} conversations across "
                f"{len(data['workspaces'])} workspaces"
            )
            return AccessValidator.create_success_response(
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
            f"Queried {sum(len(ws['conversations']) for ws in data['workspaces'])} "
            f"conversations in {format_type} format"
        )
        return AccessValidator.create_success_response(content)

    except (OSError, ValueError, TypeError, KeyError, FileNotFoundError) as e:
        log_error(e, "query_cursor_conversations")
        return AccessValidator.create_error_response(
            f"Error querying cursor conversations: {str(e)}"
        )


def handle_list_cursor_workspaces(
    arguments: dict[str, Any], project_root: Path, **kwargs
) -> dict[str, Any]:
    """List available Cursor workspace databases."""
    try:
        result = list_cursor_workspaces()
        log_info(f"Found {result['total_workspaces']} workspace databases")
        return AccessValidator.create_success_response(json.dumps(result, indent=2))

    except (OSError, ValueError, TypeError, KeyError, AttributeError) as e:
        log_error(e, "list_cursor_workspaces")
        return AccessValidator.create_error_response(str(e))


TOOL_QUERY_CURSOR_CONVERSATIONS = {
    "name": "query_cursor_conversations",
    "description": (
        "Query conversations directly from Cursor IDE databases for AI context analysis"
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "format": {
                "type": "string",
                "enum": ["json", "markdown", "cursor"],
                "default": "cursor",
                "description": (
                    "Data format for AI analysis - 'cursor' matches "
                    "Cursor's native format"
                ),
            },
            "summary": {
                "type": "boolean",
                "default": False,
                "description": (
                    "Return summary statistics instead of full conversation data"
                ),
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
