"""
Conversation export functionality for Gandalf MCP server.
Handles exporting individual conversations to various formats.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config.core_constants import GANDALF_HOME
from src.config.security_config import (
    FILENAME_CONTROL_CHARS_PATTERN,
    FILENAME_INVALID_CHARS_PATTERN,
)
from src.config.tool_config import TIMESTAMP_MILLISECOND_THRESHOLD
from src.utils.access_control import AccessValidator, create_mcp_tool_result
from src.utils.common import log_debug, log_info
from src.utils.cursor_chat_query import CursorQuery, list_cursor_workspaces


def format_timestamp(timestamp: float | None = None) -> str:
    """Format timestamp for filenames and content."""
    if timestamp is None:
        timestamp = datetime.now().timestamp()

    dt = datetime.fromtimestamp(
        timestamp / 1000 if timestamp > TIMESTAMP_MILLISECOND_THRESHOLD else timestamp
    )
    return dt.strftime("%Y%m%d_%H%M%S")


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for filesystem safety."""
    # Remove or replace problematic characters
    sanitized = re.sub(FILENAME_INVALID_CHARS_PATTERN, "_", filename)

    # Remove control characters
    sanitized = re.sub(FILENAME_CONTROL_CHARS_PATTERN, "", sanitized)

    # Limit length and strip whitespace (100 chars for conversation names)
    sanitized = sanitized.strip()[:100]

    # Ensure it's not empty
    if not sanitized:
        sanitized = "unnamed_conversation"

    return sanitized


def handle_export_individual_conversations(
    arguments: dict[str, Any], project_root: Path, **kwargs: Any
) -> dict[str, Any]:
    """Export individual conversations to files."""
    try:
        # Validate arguments
        format_type = arguments.get("format", "json")
        output_dir = arguments.get("output_dir")
        limit = arguments.get("limit", 10)
        conversation_filter = arguments.get("conversation_filter")

        if output_dir is None:
            output_dir = str(GANDALF_HOME / "exports")

        output_path = Path(output_dir).resolve()

        valid_formats = ["json", "md", "markdown", "txt"]
        if format_type not in valid_formats:
            return AccessValidator.create_error_response(
                f"Invalid format. Must be one of: {', '.join(valid_formats)}"
            )

        if not isinstance(limit, int) or limit < 1 or limit > 100:
            return AccessValidator.create_error_response(
                "Limit must be an integer between 1 and 100"
            )

        query_tool = CursorQuery(silent=True)
        data = query_tool.query_all_conversations()

        if not data or not data.get("workspaces"):
            structured_data = {
                "success": True,
                "exported_count": 0,
                "output_directory": str(output_path),
                "format": format_type,
                "files": [],
                "errors": [],
                "message": "No conversations found to export",
            }
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(structured_data, indent=2),
                    }
                ]
            }

        # Create output directory
        output_path.mkdir(parents=True, exist_ok=True)

        # Collect conversations from all workspaces
        all_conversations = []
        for workspace in data["workspaces"]:
            workspace_hash = workspace.get("workspace_hash", "unknown")
            conversations = workspace.get("conversations", [])
            prompts = workspace.get("prompts", [])
            generations = workspace.get("generations", [])

            for conv in conversations:
                conv_id = conv.get("composerId", "")
                conv_name = conv.get("name", "Untitled")

                if (
                    conversation_filter
                    and conversation_filter.lower() not in conv_name.lower()
                ):
                    continue

                conversation_data = {
                    "conversation_id": conv_id,
                    "name": conv_name,
                    "workspace_hash": workspace_hash,
                    "created_at": conv.get("createdAt", 0),
                    "last_updated": conv.get("lastUpdatedAt", 0),
                    "conversation_metadata": {
                        "type": conv.get("type", ""),
                        "unified_mode": conv.get("unifiedMode", ""),
                        "force_mode": conv.get("forceMode", ""),
                    },
                    "workspace_prompts_count": len(prompts),
                    "workspace_generations_count": len(generations),
                    "workspace_total_conversations": len(conversations),
                }
                all_conversations.append(conversation_data)

        all_conversations = all_conversations[:limit]

        exported_files = []

        for conversation in all_conversations:
            name = sanitize_filename(conversation.get("name", "unnamed"))
            timestamp = format_timestamp(conversation.get("created_at"))
            conv_id = conversation.get("conversation_id", "unknown")[:8]

            # Normalize format
            normalized_format = (
                "md" if format_type in ["md", "markdown"] else format_type
            )
            filename = f"{timestamp}_{name}_{conv_id}.{normalized_format}"
            file_path = output_path / filename

            # Export based on format
            if format_type == "json":
                content = json.dumps(conversation, indent=2)
            elif format_type in ["md", "markdown"]:
                content = _format_conversation_markdown(conversation)
            else:  # txt
                content = _format_conversation_text(conversation)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            exported_files.append(str(file_path))

        log_info(f"Exported {len(exported_files)} conversations to {output_dir}")

        structured_data = {
            "success": True,
            "exported_count": len(exported_files),
            "output_directory": str(output_path.absolute()),
            "format": format_type,
            "files": exported_files,
            "errors": [],
        }
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(structured_data, indent=2),
                }
            ]
        }

    except (OSError, json.JSONDecodeError, KeyError, AttributeError) as e:
        log_debug(f"Error in export_individual_conversations: {e}")
        return AccessValidator.create_error_response(f"Export failed: {str(e)}")


def handle_list_cursor_workspaces(
    arguments: dict[str, Any], project_root: Path, **kwargs: Any
) -> dict[str, Any]:
    """List available Cursor workspaces."""
    try:
        result = list_cursor_workspaces()
        workspace_result = {
            "workspaces": result["workspaces"],
            "count": result["total_workspaces"],
        }
        structured_data = {
            "workspaces": {
                "items": [
                    {"hash": ws["hash"], "path": ws["path"]}
                    for ws in result["workspaces"]
                ],
                "total_count": result["total_workspaces"],
            },
            "status": "workspaces_listed",
        }
        content_text = json.dumps(workspace_result, indent=2)
        mcp_result = create_mcp_tool_result(content_text, structured_data)
        return mcp_result

    except (OSError, KeyError, AttributeError) as e:
        log_debug(f"Error in list_cursor_workspaces: {e}")
        return AccessValidator.create_error_response(str(e))


def _format_conversation_markdown(conversation: dict[str, Any]) -> str:
    """Format conversation as Markdown."""
    name = conversation.get("name", "Unnamed Conversation")
    created = conversation.get("created_at")
    conv_id = conversation.get("conversation_id", "unknown")

    content = f"# {name}\n\n"
    content += f"**Conversation ID:** {conv_id}\n"

    if created:
        dt = datetime.fromtimestamp(
            created / 1000 if created > TIMESTAMP_MILLISECOND_THRESHOLD else created
        )
        content += f"**Created:** {dt.strftime('%Y-%m-%d %H:%M:%S')}\n"

    content += "\n---\n\n"
    content += f"```json\n{json.dumps(conversation, indent=2)}\n```\n"

    return content


def _format_conversation_text(conversation: dict[str, Any]) -> str:
    """Format conversation as plain text."""
    name = conversation.get("name", "Unnamed Conversation")
    created = conversation.get("created_at")
    conv_id = conversation.get("conversation_id", "unknown")

    content = f"Conversation: {name}\n"
    content += f"ID: {conv_id}\n"

    if created:
        dt = datetime.fromtimestamp(
            created / 1000 if created > TIMESTAMP_MILLISECOND_THRESHOLD else created
        )
        content += f"Created: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n"

    content += "\n" + "=" * 50 + "\n\n"
    content += f"Raw Data:\n{json.dumps(conversation, indent=2)}\n"

    return content


# Tool definition
TOOL_EXPORT_INDIVIDUAL_CONVERSATIONS = {
    "name": "export_individual_conversations",
    "title": "Export Individual Conversations",
    "description": (
        "Export individual conversations to separate files in the specified directory."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "format": {
                "type": "string",
                "enum": ["json", "md", "markdown", "txt"],
                "default": "json",
                "description": "Export format for individual files",
            },
            "output_dir": {
                "type": "string",
                "description": (
                    "Output directory path. Defaults to ~/.gandalf/exports "
                    "if not specified."
                ),
            },
            "limit": {
                "type": "integer",
                "default": 20,
                "minimum": 1,
                "maximum": 100,
                "description": "Maximum number of conversations to export",
            },
            "workspace_filter": {
                "type": "string",
                "description": "Filter by specific workspace hash",
            },
            "conversation_filter": {
                "type": "string",
                "description": "Filter conversations by name (partial match)",
            },
        },
        "required": [],
    },
    "annotations": {
        "title": "Export Individual Conversations",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
}

CONVERSATION_EXPORT_TOOL_HANDLERS = {
    "export_individual_conversations": handle_export_individual_conversations
}

CONVERSATION_EXPORT_TOOL_DEFINITIONS = [TOOL_EXPORT_INDIVIDUAL_CONVERSATIONS]
