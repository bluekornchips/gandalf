"""
Windsurf conversation query tool - Main orchestrator.

Provides focused access to actual Windsurf IDE conversation data from workspace databases,
with strict validation to avoid false positives from non-conversation data.
"""

import json
from pathlib import Path
from typing import Any

from src.tool_calls.windsurf.windsurf_query import WindsurfQuery
from src.utils.access_control import AccessValidator, create_mcp_tool_result
from src.utils.common import log_error


def handle_query_windsurf_conversations(
    arguments: dict[str, Any], project_root: Path, **kwargs: Any
) -> dict[str, Any]:
    """Query Windsurf conversations with comprehensive data retrieval."""
    try:
        # Extract and validate parameters
        format_type = arguments.get("format", "json")
        limit = arguments.get("limit", 50)

        if format_type not in ["json", "markdown", "windsurf"]:
            return AccessValidator.create_error_response(
                "format must be one of: json, markdown, windsurf"
            )

        # Query conversations
        query_tool = WindsurfQuery(silent=True)
        data = query_tool.query_all_conversations()

        # Apply limit
        conversations = data.get("conversations", [])
        if limit and len(conversations) > limit:
            conversations = conversations[:limit]
            data["conversations"] = conversations
            data["limited_results"] = True
            data["limit_applied"] = limit

        # Format response
        response_data = _format_response(data, format_type)

        # Create structured content
        structured_data = {
            "query_result": {
                "total_conversations": len(conversations),
                "format": format_type,
                "limited_results": data.get("limited_results", False),
            },
            "conversations": conversations,
            "status": "windsurf_query_complete",
        }

        return create_mcp_tool_result(response_data, structured_data)

    except (ValueError, KeyError, TypeError) as e:
        log_error(e, "query_windsurf_conversations")
        return AccessValidator.create_error_response(
            f"Error querying Windsurf conversations: {str(e)}"
        )


def _format_response(data: dict[str, Any], format_type: str) -> str:
    """Format response data according to specified format."""
    conversations = data.get("conversations", [])

    if format_type == "markdown":
        md_lines = [f"# Windsurf Conversations ({len(conversations)} total)"]
        for i, conv in enumerate(conversations, 1):
            md_lines.extend(
                [
                    f"\n## Conversation {i}",
                    f"- **ID**: {conv.get('id', 'Unknown')}",
                    f"- **Workspace**: {conv.get('workspace_id', 'Unknown')}",
                    f"- **Source**: {conv.get('source', 'Unknown')}",
                ]
            )
            if "session_data" in conv:
                session_preview = str(conv["session_data"])[:100] + "..."
                md_lines.append(f"- **Session Data**: {session_preview}")
        return "\n".join(md_lines)

    # Default to JSON for both "json" and "windsurf" formats
    return json.dumps(data, indent=2, default=str)


# Tool definitions
TOOL_QUERY_WINDSURF_CONVERSATIONS = {
    "name": "query_windsurf_conversations",
    "description": "Query conversations directly from Windsurf IDE databases for AI context analysis",
    "inputSchema": {
        "type": "object",
        "properties": {
            "format": {
                "type": "string",
                "enum": ["json", "markdown", "windsurf"],
                "default": "windsurf",
                "description": "Data format for AI analysis",
            },
            "summary": {
                "type": "boolean",
                "default": False,
                "description": "Return summary statistics instead of full conversation data",
            },
            "limit": {
                "type": "integer",
                "default": 50,
                "minimum": 1,
                "maximum": 200,
                "description": "Maximum number of conversations to return",
            },
        },
        "required": [],
    },
    "annotations": {
        "title": "Query Windsurf Conversations",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}

# Tool handlers and definitions
WINDSURF_QUERY_TOOL_HANDLERS = {
    "query_windsurf_conversations": handle_query_windsurf_conversations,
}

WINDSURF_QUERY_TOOL_DEFINITIONS = [
    TOOL_QUERY_WINDSURF_CONVERSATIONS,
]
