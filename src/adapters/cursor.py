"""
Cursor IDE adapter implementation.
"""

import os
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config.constants.ide_constants import (
    CURSOR_APP_PATHS,
    CURSOR_DATA_DIR,
    CURSOR_ENV_INDICATORS,
    CURSOR_VSCODE_ENV_INDICATORS,
    CURSOR_VSCODE_PATH_VARS,
    CURSOR_WORKSPACE_LOCATIONS,
    PROJECT_ROOT_INDICATOR,
    SQLITE_TABLE_QUERY,
)
from src.tool_calls.conversation_export import (
    CONVERSATION_EXPORT_TOOL_DEFINITIONS,
    CONVERSATION_EXPORT_TOOL_HANDLERS,
)
from src.tool_calls.conversation_recall import (
    CONVERSATION_RECALL_TOOL_DEFINITIONS,
    CONVERSATION_RECALL_TOOL_HANDLERS,
)
from src.tool_calls.cursor_query import (
    CURSOR_QUERY_TOOL_DEFINITIONS,
    CURSOR_QUERY_TOOL_HANDLERS,
)
from src.utils.common import log_debug, log_info
from src.utils.cursor_chat_query import CursorQuery

from .base import IDEAdapter


class CursorAdapter(IDEAdapter):
    """Adapter for Cursor IDE."""

    @property
    def ide_name(self) -> str:
        return "cursor"

    def detect_ide(self) -> bool:
        """Detect if Cursor IDE is running or installed."""

        # Strong indicators: Cursor-specific environment variables
        has_cursor_env = any(
            os.environ.get(var) for var in CURSOR_ENV_INDICATORS
        )

        # Check VSCode environment indicators; Cursor uses vscode infrastructure
        has_vscode_env = all(
            os.environ.get(var) == value
            for var, value in CURSOR_VSCODE_ENV_INDICATORS
        )

        # Check for Cursor in VSCode-related paths; Cursor reuses VSCode infrastructure
        vscode_paths = [
            os.environ.get(var, "") for var in CURSOR_VSCODE_PATH_VARS
        ]
        has_cursor_in_paths = any(
            "Cursor" in path for path in vscode_paths if path
        )

        # Check for Cursor processes
        has_cursor_process = False
        try:
            result = subprocess.run(
                ["pgrep", "-f", "Cursor"], capture_output=True, text=True
            )
            has_cursor_process = result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            pass

        has_cursor_app = any(Path(p).exists() for p in CURSOR_APP_PATHS)
        has_cursor_data = CURSOR_DATA_DIR.exists()

        detected = (
            has_cursor_env
            or has_vscode_env
            or has_cursor_in_paths
            or has_cursor_process
            or has_cursor_app
            or has_cursor_data
        )

        log_debug(
            f"Cursor detection: cursor_env={has_cursor_env}, "
            f"vscode_env={has_vscode_env}, cursor_in_paths={has_cursor_in_paths}, "
            f"process={has_cursor_process}, app={has_cursor_app}, data={has_cursor_data}, "
            f"detected={detected}"
        )

        return detected

    def detect_conversation_databases(self) -> bool:
        """Detect if Cursor has accessible conversation databases."""
        try:
            query_tool = CursorQuery(silent=True)
            databases = query_tool.find_workspace_databases()

            for db_path in databases:
                try:
                    workspace_data = query_tool.query_conversations_from_db(
                        db_path
                    )
                    if workspace_data.get("conversations"):
                        log_debug(
                            f"Found conversations in database: {db_path}"
                        )
                        return True
                except Exception as e:
                    log_debug(f"Error checking database {db_path}: {e}")
                    continue

            log_debug("No conversation databases found for Cursor")
            return False

        except Exception as e:
            log_debug(f"Error detecting Cursor conversation databases: {e}")
            return False

    def get_workspace_folders(self) -> List[Path]:
        """Get Cursor workspace folder paths."""
        workspace_paths = []

        for workspace_dir in CURSOR_WORKSPACE_LOCATIONS:
            if workspace_dir.exists():
                workspace_paths.extend(
                    [p for p in workspace_dir.iterdir() if p.is_dir()]
                )

        return workspace_paths

    def resolve_project_root(
        self, explicit_root: Optional[str] = None
    ) -> Path:
        """Resolve project root for Cursor."""
        if explicit_root:
            return Path(explicit_root).resolve()

        # Check WORKSPACE_FOLDER_PATHS first, highest priority
        workspace_paths = os.environ.get("WORKSPACE_FOLDER_PATHS")
        if workspace_paths:
            for workspace_path in workspace_paths.split(":"):
                workspace_path = workspace_path.strip()
                if workspace_path:
                    path_obj = Path(workspace_path).resolve()
                    if path_obj.exists():
                        log_info(
                            f"Using WORKSPACE_FOLDER_PATHS project root: {path_obj}"
                        )
                        return path_obj

        # Try to get from Cursor workspace environment
        cursor_workspace = os.environ.get("CURSOR_WORKSPACE")
        if cursor_workspace:
            return Path(cursor_workspace).resolve()

        # Try to detect from current working directory
        cwd = Path.cwd()

        # Look for git repository indicator
        current = cwd
        while current != current.parent:
            if (current / PROJECT_ROOT_INDICATOR).exists():
                log_info(
                    f"Found project root via {PROJECT_ROOT_INDICATOR}: {current}"
                )
                return current
            current = current.parent

        # Try PWD environment variable as fallback
        pwd_path = os.environ.get("PWD")
        if pwd_path:
            pwd_resolved = Path(pwd_path).resolve()
            if pwd_resolved.exists():
                log_info(
                    f"Using PWD environment variable as project root: {pwd_resolved}"
                )
                return pwd_resolved

        # default to cwd
        log_info(f"Using current directory as project root: {cwd}")
        return cwd

    def get_conversation_tools(self) -> Dict[str, Any]:
        """Get Cursor conversation tool definitions."""
        return {
            **{
                tool["name"]: tool
                for tool in CONVERSATION_EXPORT_TOOL_DEFINITIONS
            },
            **{
                tool["name"]: tool
                for tool in CONVERSATION_RECALL_TOOL_DEFINITIONS
            },
            **{tool["name"]: tool for tool in CURSOR_QUERY_TOOL_DEFINITIONS},
        }

    def get_conversation_handlers(self) -> Dict[str, Any]:
        """Get Cursor conversation tool handlers."""
        return {
            **CONVERSATION_EXPORT_TOOL_HANDLERS,
            **CONVERSATION_RECALL_TOOL_HANDLERS,
            **CURSOR_QUERY_TOOL_HANDLERS,
        }

    def get_configuration_paths(self) -> Dict[str, Path]:
        """Get Cursor configuration paths."""
        return {
            "user_data": CURSOR_DATA_DIR,
            "databases": CURSOR_DATA_DIR / "databases",
            "workspaceStorage": CURSOR_DATA_DIR / "workspaceStorage",
            "extensions": Path.home() / ".cursor" / "extensions",
            "settings": CURSOR_DATA_DIR / "User" / "settings.json",
        }

    def get_conversation_database_path(self) -> Optional[Path]:
        """Get path to Cursor conversation database."""
        config_paths = self.get_configuration_paths()

        # Common Cursor database locations
        database_candidates = [
            config_paths["databases"] / "conversations.db",
            config_paths["databases"] / "cursor.db",
            config_paths["user_data"] / "conversations.db",
            config_paths["workspaceStorage"] / "conversations.db",
        ]

        for db_path in database_candidates:
            if db_path.exists():
                # Verify it's a valid SQLite database
                try:
                    with sqlite3.connect(str(db_path)) as conn:
                        cursor = conn.cursor()
                        cursor.execute(SQLITE_TABLE_QUERY)
                        tables = [row[0] for row in cursor.fetchall()]
                        if any(
                            "conversation" in table.lower() for table in tables
                        ):
                            return db_path
                except sqlite3.Error:
                    continue

        return None
