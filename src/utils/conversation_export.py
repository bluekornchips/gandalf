#!/usr/bin/env python3
"""
Simple Conversation Export Utility

Basic conversation export functionality.
Use the MCP tool 'export_individual_conversations' for the primary export functionality.
"""

from pathlib import Path
from typing import List, Union

from src.utils.cursor_chat_query import CursorQuery


def export_conversations_simple(
    output_path: Union[str, Path],
    format_type: str = "json",
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
    if format_type not in ["json", "markdown", "cursor"]:
        raise ValueError("format_type must be one of: json, markdown, cursor")

    try:
        query_tool = CursorQuery(silent=silent)
        data = query_tool.query_all_conversations()
        query_tool.export_to_file(data, Path(output_path), format_type)

        if not silent:
            total_conversations = sum(
                len(ws.get("conversations", []))
                for ws in data.get("workspaces", [])
            )
            print(
                f"Exported {total_conversations} conversations to {output_path}"
            )

        return True

    except Exception as e:
        if not silent:
            print(f"Export failed: {e}")
        return False


def list_workspaces(silent: bool = False) -> List[str]:
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

    except Exception as e:
        if not silent:
            print(f"Failed to list workspaces: {e}")
        return []


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Simple conversation export utility"
    )
    parser.add_argument("output_path", help="Output file path")
    parser.add_argument(
        "--format", choices=["json", "markdown", "cursor"], default="json"
    )
    parser.add_argument(
        "--list-workspaces",
        action="store_true",
        help="List available workspaces and exit",
    )
    parser.add_argument(
        "--silent", action="store_true", help="Suppress console output"
    )

    args = parser.parse_args()

    if args.list_workspaces:
        list_workspaces(silent=args.silent)
    else:
        success = export_conversations_simple(
            output_path=args.output_path,
            format_type=args.format,
            silent=args.silent,
        )
        exit(0 if success else 1)
