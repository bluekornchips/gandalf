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
        base_path = Path.home() / "Library" / "Application Support" / "Cursor" / "User"

        # SSH remote sessions for macOS
        remote_paths = [
            Path.home() / ".cursor-server" / "data" / "User",  # SSH remote sessions
        ]

        for remote_path in remote_paths:
            if remote_path.exists():
                # Check if this path has more recent data
                remote_workspace = (
                    remote_path.parent / "workspaceStorage"
                    if remote_path.name == "User"
                    else remote_path / "workspaceStorage"
                )
                base_workspace = base_path / "workspaceStorage"

                if remote_workspace.exists() and not base_workspace.exists():
                    return (
                        remote_path
                        if remote_path.name == "User"
                        else remote_path / "User"
                    )

        return base_path

    elif system == "linux":
        # Linux follows XDG specification
        config_home = Path.home() / ".config"
        if "XDG_CONFIG_HOME" in os.environ:
            config_home = Path(os.environ["XDG_CONFIG_HOME"])

        base_path = config_home / "Cursor" / "User"

        # SSH remote development detection for Linux
        if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_CLIENT"):
            remote_paths = [
                Path.home() / ".cursor-server" / "data" / "User",
            ]
            for remote_path in remote_paths:
                if remote_path.exists():
                    return remote_path

        return base_path

    else:
        # Fallback for unknown systems
        return Path.home() / ".config" / "Cursor" / "User"


def find_all_cursor_paths() -> List[Path]:
    """Find all possible Cursor data paths for database discovery across supported platforms."""
    paths = []
    system = platform.system().lower()

    # primary path
    primary_path = get_default_cursor_path()
    if primary_path.exists():
        paths.append(primary_path)

    # additional search paths based on supported systems
    if system == "darwin":
        additional_paths = [
            Path.home() / "Library" / "Application Support" / "Cursor" / "User",
            Path.home() / ".cursor-server" / "data" / "User",  # SSH remote
        ]
    elif system == "linux":
        config_home = Path.home() / ".config"
        if "XDG_CONFIG_HOME" in os.environ:
            config_home = Path(os.environ["XDG_CONFIG_HOME"])

        additional_paths = [
            config_home / "Cursor" / "User",
            Path.home() / ".config" / "Cursor" / "User",  # standard path
            Path.home() / ".cursor-server" / "data" / "User",  # SSH remote
        ]
    else:
        additional_paths = [
            Path.home() / ".config" / "Cursor" / "User",
        ]

    # Add paths that exist and aren't already included
    for path in additional_paths:
        if path.exists() and path not in paths:
            paths.append(path)

    return paths


class CursorQuery:
    """
    Query and retrieve chat conversations from Cursor IDE databases.

    Provides methods to find workspace databases, query conversation data,
    and format results in various output formats.
    """

    def __init__(self, silent: bool = False):
        self.silent = silent
        self.cursor_data_path: Optional[Path] = None
        self._set_cursor_data_path(get_default_cursor_path())

    def _set_cursor_data_path(self, path: Path) -> None:
        """Set the Cursor data path with validation."""
        if path.exists():
            self.cursor_data_path = path
        elif not self.silent:
            print(f"Warning: Cursor data path not found: {path}")

    def set_cursor_data_path(self, path: Path) -> None:
        """Set custom Cursor data path."""
        self._set_cursor_data_path(path)

    def find_workspace_databases(self) -> List[Path]:
        """Find all workspace database files across all possible Cursor data locations."""
        databases = []
        cursor_paths = find_all_cursor_paths() or [get_default_cursor_path()]

        for cursor_path in cursor_paths:
            if not cursor_path.exists():
                continue

            workspace_storage = cursor_path / "workspaceStorage"
            if not workspace_storage.exists():
                continue

            for workspace_dir in workspace_storage.iterdir():
                if workspace_dir.is_dir():
                    db_path = workspace_dir / "state.vscdb"
                    if db_path.exists() and db_path not in databases:
                        databases.append(db_path)

        return databases

    def get_data_from_db(self, db_path: Path, key: str) -> Optional[Any]:
        """Query specific data from database by key."""
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
                result = cursor.fetchone()
                return json.loads(result[0]) if result else None

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

    def _format_timestamp(self, timestamp: int) -> str:
        """Format timestamp consistently."""
        return datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")

    def _create_message_map(
        self, prompts: List[Dict], generations: List[Dict]
    ) -> Dict[str, List]:
        """Create conversation ID to messages mapping."""
        prompt_map = {}
        gen_map = {}

        for prompt in prompts:
            conv_id = prompt.get("conversationId", "")
            prompt_map.setdefault(conv_id, []).append(prompt)

        for gen in generations:
            conv_id = gen.get("conversationId", "")
            gen_map.setdefault(conv_id, []).append(gen)

        return {"prompts": prompt_map, "generations": gen_map}

    def format_as_cursor_markdown(self, data: Dict[str, Any]) -> str:
        """Format conversation data as Cursor-style markdown."""
        lines = [
            "# Cursor Chat History",
            f"Queried: {data.get('query_timestamp', 'Unknown')}",
            f"Total Workspaces: {len(data.get('workspaces', []))}",
            "",
        ]

        for workspace in data.get("workspaces", []):
            workspace_hash = workspace.get("workspace_hash", "Unknown")
            conversations = workspace.get("conversations", [])
            prompts = workspace.get("prompts", [])
            generations = workspace.get("generations", [])

            lines.extend(
                [
                    f"## Workspace: {workspace_hash}",
                    f"Conversations: {len(conversations)}",
                    "",
                ]
            )

            message_maps = self._create_message_map(prompts, generations)

            for conv in conversations:
                conv_id = conv.get("composerId", "")
                conv_name = conv.get("name", "Untitled")
                created_at = conv.get("createdAt", 0)
                updated_at = conv.get("lastUpdatedAt", 0)

                lines.extend([f"### {conv_name}", f"**ID:** {conv_id}"])

                if created_at:
                    lines.append(f"**Created:** {self._format_timestamp(created_at)}")
                if updated_at:
                    lines.append(f"**Updated:** {self._format_timestamp(updated_at)}")

                lines.append("")

                conv_prompts = message_maps["prompts"].get(conv_id, [])
                conv_generations = message_maps["generations"].get(conv_id, [])

                if conv_prompts or conv_generations:
                    lines.extend(["**Conversation:**", ""])

                    all_messages = []
                    all_messages.extend([("user", p) for p in conv_prompts])
                    all_messages.extend([("assistant", g) for g in conv_generations])

                    all_messages.sort(
                        key=lambda x: x[1].get("unixMs", x[1].get("timestamp", 0))
                    )

                    for msg_type, msg in all_messages:
                        text = msg.get("text", "")
                        if text:
                            lines.extend([f"**{msg_type.title()}:** {text}", ""])

                lines.extend(["---", ""])

        return "\n".join(lines)

    def format_as_markdown(self, data: Dict[str, Any]) -> str:
        """Format conversation data as standard markdown."""
        lines = [
            "# Cursor Conversations",
            f"Queried: {data.get('query_timestamp', 'Unknown')}",
            "",
        ]

        for workspace in data.get("workspaces", []):
            workspace_hash = workspace.get("workspace_hash", "Unknown")
            conversations = workspace.get("conversations", [])

            lines.extend([f"## Workspace {workspace_hash}", ""])

            for conv in conversations:
                conv_name = conv.get("name", "Untitled")
                conv_id = conv.get("composerId", "")
                created_at = conv.get("createdAt", 0)
                updated_at = conv.get("lastUpdatedAt", 0)

                lines.extend([f"### {conv_name}", f"- **ID**: {conv_id}"])

                if created_at:
                    lines.append(f"- **Created**: {self._format_timestamp(created_at)}")
                if updated_at:
                    lines.append(f"- **Updated**: {self._format_timestamp(updated_at)}")

                lines.append("")

        return "\n".join(lines)

    def export_to_file(
        self, data: Dict[str, Any], output_path: Path, format_type: str = "json"
    ) -> None:
        """Export conversation data to file."""
        format_handlers = {
            "json": lambda: json.dump(
                data,
                open(output_path, "w", encoding="utf-8"),
                indent=2,
                ensure_ascii=False,
            ),
            "markdown": lambda: output_path.write_text(
                self.format_as_markdown(data), encoding="utf-8"
            ),
            "cursor": lambda: output_path.write_text(
                self.format_as_cursor_markdown(data), encoding="utf-8"
            ),
        }

        if format_type not in format_handlers:
            raise ValueError(f"Unsupported format: {format_type}")

        try:
            format_handlers[format_type]()
            if not self.silent:
                print(f"Data exported to: {output_path}")
        except (OSError, IOError, json.JSONEncodeError, UnicodeEncodeError) as e:
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
