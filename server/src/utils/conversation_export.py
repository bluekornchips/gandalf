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
from src.utils.cursor_chat_query import CursorQuery


def export_conversations_simple(
    output_path: str | Path,
    format_type: str = CONVERSATION_EXPORT_FORMAT_DEFAULT,
    silent: bool = False,
) -> bool:
    """
    Simple export of all conversations to a single file.

    For individual conversation exports, use the MCP tool 'export_individual_conversations'.

    Args:
        output_path: Path where to save the exported data
        format_type: Export format - 'json', 'markdown', or 'cursor'
        silent: Suppress console output

    Returns:
        True if export succeeded, False otherwise
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
            print(f"Exported {total_conversations} conversations to {output_path}")

        return True

    except (OSError, ValueError, TypeError, KeyError) as e:
        if not silent:
            print(f"Export failed: {e}")
        return False


def list_workspaces(silent: bool = False) -> list[str]:
    """
    List available workspace hashes.

    Args:
        silent: Suppress console output

    Returns:
        List of workspace hash strings
    """
    try:
        query_tool = CursorQuery(silent=silent)
        data = query_tool.query_all_conversations()

        hashes = [
            ws.get("workspace_hash", "")
            for ws in data.get("workspaces", [])
            if ws.get("workspace_hash")
        ]

        if not silent and hashes:
            print(f"Found {len(hashes)} workspaces: {', '.join(hashes)}")

        return hashes

    except (OSError, ValueError, TypeError, KeyError) as e:
        if not silent:
            print(f"Failed to list workspaces: {e}")
        return []
