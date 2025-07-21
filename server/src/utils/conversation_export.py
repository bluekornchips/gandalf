"""
Simple Conversation Export Utility

Basic conversation export functionality.
Use the MCP tool 'export_individual_conversations' for the primary export functionality.
"""

from pathlib import Path

from src.config.constants.conversation import (
    CONVERSATION_EXPORT_FORMAT_DEFAULT,
    CONVERSATION_EXPORT_FORMATS,
)
from src.utils.common import log_error, log_info
from src.utils.cursor_chat_query import CursorQuery


def export_conversations_simple(
    output_path: str | Path,
    format_type: str = CONVERSATION_EXPORT_FORMAT_DEFAULT,
    silent: bool = False,
) -> bool:
    """
    Simple export of all conversations to a single file.

    For individual conversation exports, use the MCP tool 'export_individual_conversations'.
    """
    if format_type not in CONVERSATION_EXPORT_FORMATS:
        raise ValueError(
            f"format_type must be one of: {', '.join(CONVERSATION_EXPORT_FORMATS)}"
        )

    try:
        query_tool = CursorQuery(silent=silent)
        data = query_tool.query_all_conversations()
        query_tool.export_to_file(data, Path(output_path), format_type)

        if not silent:
            total_conversations = sum(
                len(ws.get("conversations", [])) for ws in data.get("workspaces", [])
            )
            log_info(f"Exported {total_conversations} conversations to {output_path}")

        return True

    except (OSError, ValueError, TypeError, KeyError) as e:
        if not silent:
            log_error(e, "Export failed")
        return False


def list_workspaces(silent: bool = False) -> list[str]:
    """List available workspace hashes."""
    try:
        query_tool = CursorQuery(silent=silent)
        data = query_tool.query_all_conversations()

        hashes = [
            ws.get("workspace_hash", "")
            for ws in data.get("workspaces", [])
            if ws.get("workspace_hash")
        ]

        if not silent and hashes:
            log_info(f"Found {len(hashes)} workspaces: {', '.join(hashes)}")

        return hashes

    except (OSError, ValueError, TypeError, KeyError) as e:
        if not silent:
            log_error(e, "Failed to list workspaces")
        return []
