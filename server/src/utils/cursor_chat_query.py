"""
Cursor Chat Query Tool

A tool for querying and retrieving chat conversations from Cursor IDE's SQLite databases.
Provides comprehensive access to conversation history, user prompts, and AI responses.
"""

import argparse
import json
import os
import platform
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config.constants.database import CURSOR_DATABASE_FILES


def is_running_in_wsl() -> bool:
    """Check if we're running in Windows Subsystem for Linux."""
    try:
        with open("/proc/version", "r", encoding="utf-8") as f:
            return "microsoft" in f.read().lower()
    except (OSError, IOError):
        return False


def get_windows_username() -> Optional[str]:
    """Get Windows username for WSL environments."""
    windows_username = os.getenv("WINDOWS_USERNAME")
    if windows_username:
        return windows_username

    # Try to find from /mnt/c/Users directory
    users_dir = Path("/mnt/c/Users")
    if not users_dir.exists():
        return None

    # Look for first non-default user directory
    default_users = {"default", "defaultuser0", "public", "all users"}

    try:
        for user_dir in users_dir.iterdir():
            if user_dir.name.lower() not in default_users:
                return user_dir.name
    except (OSError, IOError):
        pass

    return None


def get_wsl_cursor_path() -> Optional[Path]:
    """Get Cursor path for WSL environment if available."""
    windows_username = get_windows_username()
    if not windows_username:
        return None

    windows_path = Path(f"/mnt/c/Users/{windows_username}/AppData/Roaming/Cursor/User")
    return windows_path if windows_path.exists() else None


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
        # Check for WSL environment first
        if is_running_in_wsl():
            wsl_path = get_wsl_cursor_path()
            if wsl_path:
                return wsl_path

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


def get_wsl_additional_paths() -> List[Path]:
    """Get additional Cursor paths for WSL environments."""
    additional_paths: List[Path] = []
    users_dir = Path("/mnt/c/Users")

    if not users_dir.exists():
        return additional_paths

    default_users = {"default", "defaultuser0", "public", "all users"}

    try:
        for user_dir in users_dir.iterdir():
            if user_dir.name.lower() not in default_users:
                windows_path = user_dir / "AppData/Roaming/Cursor/User"
                if windows_path.exists():
                    additional_paths.append(windows_path)
    except (OSError, IOError):
        pass

    return additional_paths


def find_all_cursor_paths() -> List[Path]:
    """Find all possible Cursor data paths for database discovery across supported platforms."""
    paths = []
    system = platform.system().lower()

    primary_path = get_default_cursor_path()
    if primary_path.exists():
        paths.append(primary_path)

    # Additional search paths based on supported systems
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
            Path.home() / ".config" / "Cursor" / "User",  # Standard path
            Path.home() / ".cursor-server" / "data" / "User",  # SSH remote
        ]

        # Add WSL-specific paths
        if is_running_in_wsl():
            additional_paths.extend(get_wsl_additional_paths())
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
        self.cursor_data_path = get_default_cursor_path()

    def _set_cursor_data_path(self, path: Path) -> None:
        """Set the Cursor data path after validation."""
        if not path.exists():
            raise FileNotFoundError(f"Cursor data path does not exist: {path}")
        self.cursor_data_path = path

    def set_cursor_data_path(self, path: Path) -> None:
        """Public method to set Cursor data path."""
        self._set_cursor_data_path(path)

    def find_workspace_databases(self) -> List[Path]:
        """Find all workspace database files in the Cursor data directory."""
        databases: List[Path] = []
        workspace_storage_path = self.cursor_data_path / "workspaceStorage"

        if not workspace_storage_path.exists():
            if not self.silent:
                print(f"No workspace storage found at: {workspace_storage_path}")
            return databases

        try:
            for workspace_dir in workspace_storage_path.iterdir():
                if workspace_dir.is_dir():
                    for db_file in CURSOR_DATABASE_FILES:
                        db_path = workspace_dir / db_file
                        if db_path.exists() and db_path.is_file():
                            databases.append(db_path)
                            if not self.silent:
                                print(f"Found database: {db_path}")
        except (OSError, PermissionError) as e:
            if not self.silent:
                print(f"Error accessing workspace storage: {e}")

        return databases

    def get_data_from_db(self, db_path: Path, key: str) -> Optional[Any]:
        """Extract data from database using a specific key."""
        try:
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
                result = cursor.fetchone()
                if result:
                    data = json.loads(result[0])
                    # Explicitly close to ensure cleanup
                    cursor.close()
                    return data
                # Explicitly close to ensure cleanup
                cursor.close()
                return None
        except (sqlite3.Error, json.JSONDecodeError, OSError) as e:
            if not self.silent:
                print(f"Error reading from database {db_path}: {e}")
            return None

    def query_conversations_from_db(self, db_path: Path) -> Dict[str, Any]:
        """Query all conversation data from a single database."""
        composer_data = self.get_data_from_db(db_path, "composer.composerData")
        conversations = []

        if composer_data and isinstance(composer_data, dict):
            # Extract conversations from allComposers array
            conversations = composer_data.get("allComposers", [])

        # Fall back to old format if new format doesn't exist
        if not conversations:
            conversations = self.get_data_from_db(db_path, "aiConversations") or []

        # Try new key names first (current Cursor format)
        prompts = self.get_data_from_db(db_path, "aiService.prompts")
        generations = self.get_data_from_db(db_path, "aiService.generations")

        # Fall back to old key names if new ones don't exist
        if not prompts:
            prompts = self.get_data_from_db(db_path, "userPrompts")
        if not generations:
            generations = self.get_data_from_db(db_path, "aiGenerations")

        prompts = prompts or []
        generations = generations or []

        # If no conversations but we have prompts/generations, reconstruct conversations
        if not conversations and (prompts or generations):
            conversations = self._reconstruct_conversations_from_prompts_generations(
                prompts, generations
            )

        return {
            "conversations": conversations or [],
            "prompts": prompts,
            "generations": generations,
        }

    def _reconstruct_conversations_from_prompts_generations(
        self, prompts: List[Dict[str, Any]], generations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Reconstruct conversations from prompts and generations."""
        if not prompts and not generations:
            return []

        conversations: List[Dict[str, Any]] = []
        all_items: List[Dict[str, Any]] = []

        for prompt in prompts:
            if isinstance(prompt, dict) and "text" in prompt:
                all_items.append(
                    {
                        "type": "prompt",
                        "text": prompt["text"],
                        "timestamp": prompt.get("unixMs", 0),
                        "commandType": prompt.get("commandType", 0),
                    }
                )

        for gen in generations:
            if isinstance(gen, dict):
                all_items.append(
                    {
                        "type": "generation",
                        "text": gen.get("textDescription", ""),
                        "timestamp": gen.get("unixMs", 0),
                        "uuid": gen.get("generationUUID", ""),
                        "gen_type": gen.get("type", "unknown"),
                    }
                )

        all_items.sort(key=lambda x: x.get("timestamp", 0))

        if all_items:
            min_timestamp = min(item.get("timestamp", 0) for item in all_items)
            max_timestamp = max(item.get("timestamp", 0) for item in all_items)
            conv_id = f"reconstructed_{hash(str(all_items[:5]))}"

            conversation: Dict[str, Any] = {
                "id": conv_id,
                "messages": all_items,
                "created_at": min_timestamp,
                "updated_at": max_timestamp,
                "message_count": len(all_items),
                "name": "Reconstructed Conversation",
            }
            conversations.append(conversation)

        return conversations

    def query_all_conversations(self) -> Dict[str, Any]:
        """Query conversations from all available workspace databases."""
        all_databases = self.find_workspace_databases()
        workspaces = []

        for db_path in all_databases:
            workspace_hash = db_path.parent.name
            data = self.query_conversations_from_db(db_path)

            if data["conversations"]:
                workspaces.append(
                    {
                        "workspace_hash": workspace_hash,
                        "database_path": str(db_path),
                        **data,
                    }
                )

        return {
            "workspaces": workspaces,
            "total_databases": len(all_databases),
            "cursor_data_path": str(self.cursor_data_path),
        }

    def _format_timestamp(self, timestamp: int) -> str:
        """Format timestamp for display."""
        return datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")

    def _create_message_map(
        self, prompts: List[Dict], generations: List[Dict]
    ) -> Dict[str, Dict[str, List]]:
        """Create a mapping of conversation IDs to their messages."""
        message_map: Dict[str, Dict[str, List]] = {}

        for prompt in prompts:
            conv_id = prompt.get("conversationId")
            if conv_id:
                if conv_id not in message_map:
                    message_map[conv_id] = {"prompts": [], "generations": []}
                message_map[conv_id]["prompts"].append(prompt)

        for generation in generations:
            conv_id = generation.get("conversationId")
            if conv_id:
                if conv_id not in message_map:
                    message_map[conv_id] = {"prompts": [], "generations": []}
                message_map[conv_id]["generations"].append(generation)

        return message_map

    def format_as_cursor_markdown(self, data: Dict[str, Any]) -> str:
        """Format conversation data as Cursor-style markdown."""
        output = []
        output.append("# Cursor Conversations Export")
        output.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(f"Cursor Data Path: {data.get('cursor_data_path', 'Unknown')}")
        output.append(f"Total Databases: {data.get('total_databases', 0)}")
        output.append("")

        for workspace in data.get("workspaces", []):
            workspace_hash = workspace.get("workspace_hash", "Unknown")
            conversations = workspace.get("conversations", [])
            prompts = workspace.get("prompts", [])
            generations = workspace.get("generations", [])

            output.append(f"## Workspace: {workspace_hash}")
            output.append(f"Database: {workspace.get('database_path', 'Unknown')}")
            output.append(f"Conversations: {len(conversations)}")
            output.append("")

            message_map = self._create_message_map(prompts, generations)

            for conversation in conversations:
                conv_id = conversation.get("id")
                name = conversation.get("name", "Untitled")
                created_at = conversation.get("createdAt", 0)
                updated_at = conversation.get("lastUpdatedAt", 0)

                output.append(f"### {name}")
                output.append(f"**ID:** {conv_id}")
                output.append(f"**Created:** {self._format_timestamp(created_at)}")
                output.append(f"**Updated:** {self._format_timestamp(updated_at)}")
                output.append("")

                if conv_id in message_map:
                    messages = message_map[conv_id]
                    all_messages = []

                    for prompt in messages.get("prompts", []):
                        all_messages.append(
                            (
                                "user",
                                prompt.get("text", ""),
                                prompt.get("createdAt", 0),
                            )
                        )

                    for generation in messages.get("generations", []):
                        all_messages.append(
                            (
                                "assistant",
                                generation.get("text", ""),
                                generation.get("createdAt", 0),
                            )
                        )

                    all_messages.sort(key=lambda x: x[2])

                    for role, text, timestamp in all_messages:
                        output.append(
                            f"**{role.title()}:** {self._format_timestamp(timestamp)}"
                        )
                        output.append(text)
                        output.append("")

                output.append("---")
                output.append("")

        return "\n".join(output)

    def format_as_markdown(self, data: Dict[str, Any]) -> str:
        """Format conversation data as simple markdown."""
        output = []
        output.append("# Conversations Export")
        output.append("")

        for workspace in data.get("workspaces", []):
            conversations = workspace.get("conversations", [])
            for conversation in conversations:
                name = conversation.get("name", "Untitled")
                output.append(f"## {name}")
                output.append("")

        return "\n".join(output)

    def export_to_file(
        self,
        data: Dict[str, Any],
        output_path: Path,
        format_type: str = "json",
    ) -> None:
        """Export conversation data to file."""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if format_type == "json":
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            elif format_type == "cursor":
                formatted_data = self.format_as_cursor_markdown(data)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(formatted_data)
            elif format_type == "markdown":
                formatted_data = self.format_as_markdown(data)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(formatted_data)
            else:
                raise ValueError(f"Unsupported format: {format_type}")

            if not self.silent:
                print(f"Data exported to: {output_path}")

        except (OSError, IOError, ValueError, TypeError) as e:
            if not self.silent:
                print(f"Export failed: {e}")
            raise


def main() -> int:
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description="Query Cursor chat conversations")
    parser.add_argument("--output", "-o", help="Output file path (optional)")
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "markdown", "cursor"],
        default="json",
    )
    parser.add_argument("--cursor-path", help="Custom Cursor data path")
    parser.add_argument(
        "--list-workspaces",
        action="store_true",
        help="List available workspaces",
    )
    parser.add_argument(
        "--silent", action="store_true", help="Suppress output messages"
    )

    args = parser.parse_args()

    try:
        query_tool = CursorQuery(silent=args.silent)

        if args.cursor_path:
            query_tool.set_cursor_data_path(Path(args.cursor_path))

        if args.list_workspaces:
            data = query_tool.query_all_conversations()
            for workspace in data.get("workspaces", []):
                print(f"Workspace: {workspace.get('workspace_hash')}")
                print(f"  Database: {workspace.get('database_path')}")
                print(f"  Conversations: {len(workspace.get('conversations', []))}")
            return 0

        data = query_tool.query_all_conversations()

        if args.output:
            query_tool.export_to_file(data, Path(args.output), args.format)
        else:
            print(json.dumps(data, indent=2))

    except (FileNotFoundError, ValueError, OSError, IOError) as e:
        print(f"Error: {e}")
        return 1

    return 0


def list_cursor_workspaces() -> Dict[str, Any]:
    """
    Standalone function to list Cursor workspaces.
    Returns workspace information as a dictionary.
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

        return {
            "total_workspaces": len(workspaces),
            "workspaces": workspaces,
        }

    except (OSError, IOError, ValueError, TypeError, AttributeError) as e:
        raise ValueError(f"Error listing workspace databases: {str(e)}")
