"""
Conversation export functionality for Gandalf MCP server.
Handles exporting individual conversations to various formats.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.config.constants.core import GANDALF_HOME
from src.config.constants.security import (
    FILENAME_CONTROL_CHARS_PATTERN,
    FILENAME_INVALID_CHARS_PATTERN,
    FILENAME_MAX_LENGTH,
    TIMESTAMP_MILLISECOND_THRESHOLD,
)
from src.utils.access_control import AccessValidator
from src.utils.common import log_debug, log_info
from src.utils.cursor_chat_query import CursorQuery


def format_timestamp(timestamp: Optional[float] = None) -> str:
    """Format timestamp for filenames and content.

    Args:
        timestamp: Unix timestamp (defaults to current time)

    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        timestamp = datetime.now().timestamp()

    dt = datetime.fromtimestamp(
        timestamp / 1000
        if timestamp > TIMESTAMP_MILLISECOND_THRESHOLD
        else timestamp
    )
    return dt.strftime("%Y%m%d_%H%M%S")


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for filesystem safety.

    Args:
        filename: Raw filename

    Returns:
        Sanitized filename safe for filesystem use
    """
    # Remove or replace problematic characters
    sanitized = re.sub(FILENAME_INVALID_CHARS_PATTERN, "_", filename)

    # Remove control characters
    sanitized = re.sub(FILENAME_CONTROL_CHARS_PATTERN, "", sanitized)

    # Limit length and strip whitespace
    sanitized = sanitized.strip()[:FILENAME_MAX_LENGTH]

    # Ensure it's not empty
    if not sanitized:
        sanitized = "unnamed_conversation"

    return sanitized


def handle_export_individual_conversations(
    arguments: Dict[str, Any], project_root: Path, **kwargs
) -> Dict[str, Any]:
    """Export individual conversations to files.

    Args:
        arguments: Tool arguments containing format, output_dir, etc.
        project_root: Project root path
        **kwargs: Additional arguments

    Returns:
        MCP response with export results
    """
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
            return AccessValidator.create_success_response(
                json.dumps(
                    {
                        "exported_count": 0,
                        "files": [],
                        "message": "No conversations found to export",
                        "output_directory": str(output_path),
                        "format": format_type,
                    }
                )
            )

        # Create output directory
        output_path.mkdir(parents=True, exist_ok=True)

        # Collect conversations from all workspaces
        all_conversations = []
        for workspace in data["workspaces"]:
            workspace_hash = workspace.get("workspace_hash", "unknown")
            conversations = workspace.get("conversations", [])
            prompts = workspace.get("prompts", [])
            generations = workspace.get("generations", [])

            # Create message maps for this workspace
            message_maps = query_tool._create_message_map(prompts, generations)

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
                    "prompts": message_maps["prompts"].get(conv_id, []),
                    "generations": message_maps["generations"].get(
                        conv_id, []
                    ),
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

        log_info(
            f"Exported {len(exported_files)} conversations to {output_dir}"
        )

        return AccessValidator.create_success_response(
            json.dumps(
                {
                    "exported_count": len(exported_files),
                    "files": exported_files,
                    "output_directory": str(output_path.absolute()),
                    "format": format_type,
                }
            )
        )

    except Exception as e:
        log_debug(f"Error in export_individual_conversations: {e}")
        return AccessValidator.create_error_response(
            f"Export failed: {str(e)}"
        )


def handle_list_cursor_workspaces(
    arguments: Dict[str, Any], project_root: Path, **kwargs
) -> Dict[str, Any]:
    """List available Cursor workspaces.

    Args:
        arguments: Tool arguments (currently unused)
        project_root: Project root path
        **kwargs: Additional arguments

    Returns:
        MCP response with workspace list
    """
    try:
        query_tool = CursorQuery(silent=True)
        workspace_dbs = query_tool.find_workspace_databases()

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

        return AccessValidator.create_success_response(
            json.dumps({"workspaces": workspaces, "count": len(workspaces)})
        )

    except Exception as e:
        log_debug(f"Error in list_cursor_workspaces: {e}")
        return AccessValidator.create_error_response(
            f"Failed to list workspaces: {str(e)}"
        )


def _format_conversation_markdown(conversation: Dict[str, Any]) -> str:
    """Format conversation as Markdown."""
    name = conversation.get("name", "Unnamed Conversation")
    created = conversation.get("created_at")
    conv_id = conversation.get("conversation_id", "unknown")

    content = f"# {name}\n\n"
    content += f"**Conversation ID:** {conv_id}\n"

    if created:
        dt = datetime.fromtimestamp(
            created / 1000
            if created > TIMESTAMP_MILLISECOND_THRESHOLD
            else created
        )
        content += f"**Created:** {dt.strftime('%Y-%m-%d %H:%M:%S')}\n"

    content += "\n---\n\n"
    content += f"```json\n{json.dumps(conversation, indent=2)}\n```\n"

    return content


def _format_conversation_text(conversation: Dict[str, Any]) -> str:
    """Format conversation as plain text."""
    name = conversation.get("name", "Unnamed Conversation")
    created = conversation.get("created_at")
    conv_id = conversation.get("conversation_id", "unknown")

    content = f"Conversation: {name}\n"
    content += f"ID: {conv_id}\n"

    if created:
        dt = datetime.fromtimestamp(
            created / 1000
            if created > TIMESTAMP_MILLISECOND_THRESHOLD
            else created
        )
        content += f"Created: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n"

    content += "\n" + "=" * 50 + "\n\n"
    content += f"Raw Data:\n{json.dumps(conversation, indent=2)}\n"

    return content


# Tool definition
TOOL_EXPORT_INDIVIDUAL_CONVERSATIONS = {
    "name": "export_individual_conversations",
    "description": "Export individual conversations to separate files in the specified directory.",
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
                "description": "Output directory path. Defaults to ~/.gandalf/exports if not specified.",
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
