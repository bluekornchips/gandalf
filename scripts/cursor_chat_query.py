#!/usr/bin/env python3
"""
Cursor Chat Query Tool

A tool for querying and retrieving chat conversations from Cursor IDE's SQLite databases.
Provides comprehensive access to conversation history, user prompts, and AI responses.
"""

import json
import os
import platform
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional


def get_default_cursor_path() -> Path:
    """Get the default Cursor data path for the current platform."""
    system = platform.system().lower()

    if system == "darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "Cursor" / "User"
    elif system == "linux":
        # Linux follows XDG specification
        config_home = Path.home() / ".config"
        if "XDG_CONFIG_HOME" in os.environ:
            config_home = Path(os.environ["XDG_CONFIG_HOME"])
        return config_home / "Cursor" / "User"
    elif system == "windows":
        # Windows AppData path
        return Path.home() / "AppData" / "Roaming" / "Cursor" / "User"
    else:
        # Fallback to Linux-style for unknown systems
        return Path.home() / ".config" / "Cursor" / "User"


class CursorQuery:
    """
    Query and retrieve chat conversations from Cursor IDE databases.

    Provides methods to find workspace databases, query conversation data,
    and format results in various output formats.
    """

    def __init__(self, silent=False):
        self.silent = silent
        self.cursor_data_path = None
        self._set_cursor_data_path(get_default_cursor_path())

    def _set_cursor_data_path(self, path: Path):
        """Set the Cursor data path with validation."""
        if path.exists():
            self.cursor_data_path = path
        elif not self.silent:
            print(f"Warning: Cursor data path not found: {path}")

    def set_cursor_data_path(self, path: Path):
        """Set custom Cursor data path."""
        self._set_cursor_data_path(path)

    def find_workspace_databases(self) -> List[Path]:
        """Find all workspace database files."""
        if not self.cursor_data_path:
            return []

        workspace_storage = self.cursor_data_path / "workspaceStorage"
        if not workspace_storage.exists():
            return []

        databases = []
        for workspace_dir in workspace_storage.iterdir():
            if workspace_dir.is_dir():
                db_path = workspace_dir / "state.vscdb"
                if db_path.exists():
                    databases.append(db_path)

        return databases

    def get_data_from_db(self, db_path: Path, key: str) -> Optional[Any]:
        """Query specific data from database by key."""
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
                result = cursor.fetchone()

                if result:
                    return json.loads(result[0])
                return None
        except (sqlite3.Error, json.JSONDecodeError, OSError) as e:
            if not self.silent:
                print(f"Error querying database {db_path}: {e}")
            return None

    def query_conversations_from_db(self, db_path: Path) -> Dict[str, Any]:
        """Query all conversation data from a single database."""
        workspace_hash = db_path.parent.name

        # Query all relevant data
        conversations = self.get_data_from_db(db_path, "composer.composerData")
        prompts = self.get_data_from_db(db_path, "aiService.prompts")
        generations = self.get_data_from_db(db_path, "aiService.generations")

        # Process conversations
        all_conversations = []
        if conversations and "allComposers" in conversations:
            all_conversations = conversations["allComposers"]

        return {
            "workspace_hash": workspace_hash,
            "database_path": str(db_path),
            "conversations": all_conversations,
            "prompts": prompts or [],
            "generations": generations or [],
        }

    def query_all_conversations(self) -> Dict[str, Any]:
        """Query conversations from all available databases."""
        databases = self.find_workspace_databases()

        if not databases:
            if not self.silent:
                print("No workspace databases found")
            return {"workspaces": [], "query_timestamp": datetime.now().isoformat()}

        workspaces = []
        for db_path in databases:
            workspace_data = self.query_conversations_from_db(db_path)
            if workspace_data["conversations"]:  # Only include if has conversations
                workspaces.append(workspace_data)

        return {
            "workspaces": workspaces,
            "query_timestamp": datetime.now().isoformat(),
            "total_databases": len(databases),
            "databases_with_conversations": len(workspaces),
        }

    def format_as_cursor_markdown(self, data: Dict[str, Any]) -> str:
        """Format conversation data as Cursor-style markdown."""
        lines = []
        lines.append("# Cursor Chat History")
        lines.append(f"Queried: {data.get('query_timestamp', 'Unknown')}")
        lines.append(f"Total Workspaces: {len(data.get('workspaces', []))}")
        lines.append("")

        for workspace in data.get("workspaces", []):
            workspace_hash = workspace.get("workspace_hash", "Unknown")
            conversations = workspace.get("conversations", [])
            prompts = workspace.get("prompts", [])
            generations = workspace.get("generations", [])

            lines.append(f"## Workspace: {workspace_hash}")
            lines.append(f"Conversations: {len(conversations)}")
            lines.append("")

            # Create conversation ID to prompts/generations mapping
            prompt_map = {}
            gen_map = {}

            for prompt in prompts:
                conv_id = prompt.get("conversationId", "")
                if conv_id not in prompt_map:
                    prompt_map[conv_id] = []
                prompt_map[conv_id].append(prompt)

            for gen in generations:
                conv_id = gen.get("conversationId", "")
                if conv_id not in gen_map:
                    gen_map[conv_id] = []
                gen_map[conv_id].append(gen)

            # Process each conversation
            for conv in conversations:
                conv_id = conv.get("composerId", "")
                conv_name = conv.get("name", "Untitled")
                created_at = conv.get("createdAt", 0)
                updated_at = conv.get("lastUpdatedAt", 0)

                lines.append(f"### {conv_name}")
                lines.append(f"**ID:** {conv_id}")
                if created_at:
                    lines.append(
                        f"**Created:** {datetime.fromtimestamp(created_at/1000).strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                if updated_at:
                    lines.append(
                        f"**Updated:** {datetime.fromtimestamp(updated_at/1000).strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                lines.append("")

                # Add prompts and generations for this conversation
                conv_prompts = prompt_map.get(conv_id, [])
                conv_generations = gen_map.get(conv_id, [])

                if conv_prompts or conv_generations:
                    lines.append("**Conversation:**")
                    lines.append("")

                    # Combine and sort by timestamp
                    all_messages = []
                    for prompt in conv_prompts:
                        all_messages.append(("user", prompt))
                    for gen in conv_generations:
                        all_messages.append(("assistant", gen))

                    # Sort by timestamp (approximate)
                    all_messages.sort(
                        key=lambda x: x[1].get("unixMs", x[1].get("timestamp", 0))
                    )

                    for msg_type, msg in all_messages:
                        if msg_type == "user":
                            text = msg.get("text", "")
                            if text:
                                lines.append(f"**User:** {text}")
                                lines.append("")
                        else:
                            text = msg.get("text", "")
                            if text:
                                lines.append(f"**Assistant:** {text}")
                                lines.append("")

                lines.append("---")
                lines.append("")

        return "\n".join(lines)

    def format_as_markdown(self, data: Dict[str, Any]) -> str:
        """Format conversation data as standard markdown."""
        lines = []
        lines.append("# Cursor Conversations")
        lines.append(f"Queried: {data.get('query_timestamp', 'Unknown')}")
        lines.append("")

        for workspace in data.get("workspaces", []):
            workspace_hash = workspace.get("workspace_hash", "Unknown")
            conversations = workspace.get("conversations", [])

            lines.append(f"## Workspace {workspace_hash}")
            lines.append("")

            for conv in conversations:
                conv_name = conv.get("name", "Untitled")
                conv_id = conv.get("composerId", "")
                created_at = conv.get("createdAt", 0)
                updated_at = conv.get("lastUpdatedAt", 0)

                lines.append(f"### {conv_name}")
                lines.append(f"- **ID**: {conv_id}")

                if created_at:
                    created_str = datetime.fromtimestamp(created_at / 1000).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    lines.append(f"- **Created**: {created_str}")

                if updated_at:
                    updated_str = datetime.fromtimestamp(updated_at / 1000).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    lines.append(f"- **Updated**: {updated_str}")

                lines.append("")

        return "\n".join(lines)

    def export_to_file(
        self, data: Dict[str, Any], output_path: Path, format_type: str = "json"
    ):
        """Export conversation data to file."""
        try:
            if format_type == "json":
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            elif format_type == "markdown":
                content = self.format_as_markdown(data)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(content)
            elif format_type == "cursor":
                content = self.format_as_cursor_markdown(data)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                raise ValueError(f"Unsupported format: {format_type}")

            if not self.silent:
                print(f"Data exported to: {output_path}")

        except (
            OSError,
            IOError,
            json.JSONEncodeError,
            ValueError,
            UnicodeEncodeError,
        ) as e:
            if not self.silent:
                print(f"Error exporting to {output_path}: {e}")


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(description="Query Cursor IDE chat conversations")
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "cursor"],
        default="json",
        help="Output format",
    )
    parser.add_argument("--output", type=Path, help="Output file path")
    parser.add_argument(
        "--list-workspaces",
        action="store_true",
        help="List available workspace databases",
    )
    parser.add_argument(
        "--cursor-path", type=Path, help="Custom Cursor data directory path"
    )
    parser.add_argument(
        "--silent", action="store_true", help="Suppress output messages"
    )

    args = parser.parse_args()

    # Initialize query tool
    query_tool = CursorQuery(silent=args.silent)

    if args.cursor_path:
        query_tool.set_cursor_data_path(args.cursor_path)

    if args.list_workspaces:
        databases = query_tool.find_workspace_databases()
        print(f"Found {len(databases)} workspace databases:")
        for db in databases:
            print(f"  - {db}")
        return

    # Query all conversations
    data = query_tool.query_all_conversations()

    if args.output:
        query_tool.export_to_file(data, args.output, args.format)
    else:
        if args.format == "json":
            print(json.dumps(data, indent=2))
        elif args.format == "markdown":
            print(query_tool.format_as_markdown(data))
        elif args.format == "cursor":
            print(query_tool.format_as_cursor_markdown(data))


if __name__ == "__main__":
    main()
