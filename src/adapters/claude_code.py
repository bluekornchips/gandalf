"""
Claude Code adapter implementation.
"""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config.constants.ide_constants import (
    CLAUDE_CONFIG_DIR,
    CLAUDE_CONFIG_PATHS,
    CLAUDE_CONTEXT_ENV_VARS,
    CLAUDE_HOME,
    CLAUDE_INDICATORS,
    PROJECT_ROOT_INDICATOR,
)
from src.tool_calls.claude_code_query import (
    CLAUDE_CODE_QUERY_TOOL_DEFINITIONS,
    CLAUDE_CODE_QUERY_TOOL_HANDLERS,
)
from src.tool_calls.claude_code_recall import (
    CLAUDE_CODE_RECALL_TOOL_DEFINITIONS,
    CLAUDE_CODE_RECALL_TOOL_HANDLERS,
)
from src.utils.common import log_debug, log_info

from .base import IDEAdapter


class ClaudeCodeAdapter(IDEAdapter):
    """Adapter for Claude Code."""

    @property
    def ide_name(self) -> str:
        return "claude-code"

    def detect_ide(self) -> bool:
        """Detect if Claude Code is running."""
        claudecode_env = os.environ.get("CLAUDECODE") == "1"
        claude_entrypoint = os.environ.get("CLAUDE_CODE_ENTRYPOINT") == "cli"

        has_claude_process = False
        try:
            result = subprocess.run(
                ["pgrep", "-f", "claude"], capture_output=True, text=True
            )
            has_claude_process = (
                result.returncode == 0 and "claude" in result.stdout
            )
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            pass

        # Check for Claude Code configuration
        has_claude_config = any(p.exists() for p in CLAUDE_CONFIG_PATHS)

        # Strong indicators: environment variables or active processes
        strong_indicators = (
            claudecode_env or claude_entrypoint or has_claude_process
        )

        # If we have explicit Claude Code environment variables, prioritize them
        if claudecode_env or claude_entrypoint:
            detected = True
        else:
            # Check for competing IDE indicators like Cursor
            has_cursor_indicators = self._has_cursor_indicators()

            # If we have strong Cursor indicators, don't detect Claude Code unless we have other strong indicators
            if has_cursor_indicators and not (has_claude_process):
                detected = False
            else:
                # Only detect Claude Code if we have strong indicators, or if we have weak indicators
                # AND we're in a context that suggests Claude Code usage
                detected = strong_indicators or (
                    has_claude_config and self._has_claude_context()
                )

        log_debug(
            f"Claude Code detection: env={claudecode_env}, "
            f"entrypoint={claude_entrypoint}, process={has_claude_process}, "
            f"config={has_claude_config}, detected={detected}"
        )

        return detected

    def detect_conversation_databases(self) -> bool:
        """Detect if Claude Code has accessible conversation storage."""
        try:
            config_paths = self.get_configuration_paths()

            # Check for memory, sessions, or projects directories with content
            storage_paths = [
                config_paths.get("memory"),
                config_paths.get("sessions"),
                config_paths.get("projects"),
            ]

            for storage_path in storage_paths:
                if storage_path and storage_path.exists():
                    # Check if directory has any files indicating conversation data
                    try:
                        if any(storage_path.iterdir()):
                            log_debug(
                                f"Found conversation storage in: {storage_path}"
                            )
                            return True
                    except (OSError, PermissionError):
                        continue

            log_debug("No conversation storage found for Claude Code")
            return False

        except Exception as e:
            log_debug(f"Error detecting Claude Code conversation storage: {e}")
            return False

    def _has_cursor_indicators(self) -> bool:
        """Check if there are strong Cursor IDE indicators present."""
        env_vars = os.environ

        # Strong Cursor indicators
        cursor_indicators = [
            env_vars.get("CURSOR_TRACE_ID"),
            env_vars.get("VSCODE_INJECTION") == "1",
            env_vars.get("TERM_PROGRAM") == "vscode",
        ]

        # Check for Cursor in paths
        vscode_paths = [
            env_vars.get("VSCODE_GIT_ASKPASS_NODE", ""),
            env_vars.get("VSCODE_GIT_ASKPASS_MAIN", ""),
        ]
        has_cursor_in_paths = any(
            "Cursor" in path for path in vscode_paths if path
        )

        return any(cursor_indicators) or has_cursor_in_paths

    def _has_claude_context(self) -> bool:
        """Check if we're in a context that suggests Claude Code usage."""
        # Check for Claude-specific environment variables
        for env_var in CLAUDE_CONTEXT_ENV_VARS:
            if os.environ.get(env_var):
                return True

        # Check if current working directory or parent directories have Claude indicators
        current = Path.cwd()
        while current != current.parent:
            for indicator in CLAUDE_INDICATORS:
                if (current / indicator).exists():
                    return True
            current = current.parent

        return False

    def get_workspace_folders(self) -> List[Path]:
        """Get Claude Code workspace folder paths."""
        workspace_paths = []

        claude_workspace = os.environ.get("CLAUDE_WORKSPACE")
        if claude_workspace:
            workspace_path = Path(claude_workspace)
            if workspace_path.exists():
                workspace_paths.append(workspace_path)

        # Check common Claude configuration locations
        for config_dir in CLAUDE_CONFIG_PATHS:
            if config_dir.exists():
                # Look for workspace or project directories
                workspace_dir = config_dir / "workspaces"
                if workspace_dir.exists():
                    workspace_paths.extend(
                        [p for p in workspace_dir.iterdir() if p.is_dir()]
                    )

        return workspace_paths

    def resolve_project_root(
        self, explicit_root: Optional[str] = None
    ) -> Path:
        """Resolve project root for Claude Code."""
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

        claude_project = os.environ.get("CLAUDE_PROJECT_ROOT")
        if claude_project:
            return Path(claude_project).resolve()

        claude_workspace = os.environ.get("CLAUDE_WORKSPACE")
        if claude_workspace:
            return Path(claude_workspace).resolve()

        cwd = Path.cwd()

        # Look for Claude Code specific indicators first
        for indicator in CLAUDE_INDICATORS:
            current = cwd
            while current != current.parent:
                if (current / indicator).exists():
                    log_info(
                        f"Found Claude Code project root via {indicator}: {current}"
                    )
                    return current
                current = current.parent

        # Look for git repository
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
        """Get Claude Code conversation tool definitions."""
        # Phase 2: Claude Code conversation tools are now implemented
        return {
            **{
                tool["name"]: tool
                for tool in CLAUDE_CODE_QUERY_TOOL_DEFINITIONS
            },
            **{
                tool["name"]: tool
                for tool in CLAUDE_CODE_RECALL_TOOL_DEFINITIONS
            },
        }

    def get_conversation_handlers(self) -> Dict[str, Any]:
        """Get Claude Code conversation tool handlers."""
        # Phase 2: Claude Code conversation handlers are now implemented
        return {
            **CLAUDE_CODE_QUERY_TOOL_HANDLERS,
            **CLAUDE_CODE_RECALL_TOOL_HANDLERS,
        }

    def get_configuration_paths(self) -> Dict[str, Path]:
        """Get Claude Code configuration paths."""
        return {
            "user_home": CLAUDE_HOME,
            "config_dir": CLAUDE_CONFIG_DIR,
            "settings": CLAUDE_HOME / "settings.json",
            "memory": CLAUDE_HOME / "memory",
            "sessions": CLAUDE_HOME / "sessions",
            "workspaces": CLAUDE_HOME / "workspaces",
            "projects": CLAUDE_HOME
            / "projects",  # Added for conversation storage
        }

    def supports_conversations(self) -> bool:
        """Claude Code conversation support status."""
        # Phase 2: Conversation support is now enabled
        return True

    def get_memory_path(self) -> Optional[Path]:
        """Get Claude Code memory storage path."""
        config_paths = self.get_configuration_paths()
        memory_path = config_paths["memory"]

        if memory_path.exists():
            return memory_path

        return None

    def get_session_path(self) -> Optional[Path]:
        """Get Claude Code session storage path."""
        config_paths = self.get_configuration_paths()
        sessions_path = config_paths["sessions"]

        if sessions_path.exists():
            return sessions_path

        return None

    def get_conversation_storage_path(
        self, project_root: Optional[Path] = None
    ) -> Optional[Path]:
        """Get Claude Code conversation storage path for a specific project."""
        config_paths = self.get_configuration_paths()
        projects_path = config_paths["projects"]

        if not projects_path.exists():
            return None

        if project_root:
            # Encode project path for Claude Code's naming convention
            encoded_path = str(project_root).replace("/", "-")
            project_conversations_path = projects_path / encoded_path

            if project_conversations_path.exists():
                return project_conversations_path

        return projects_path

    def get_claude_home_directory(self) -> Path:
        """Get the Claude Code home directory."""
        return CLAUDE_HOME

    def is_claude_code_environment(self) -> bool:
        """Check if we're running in a Claude Code environment."""
        # Check environment variables
        if os.environ.get("CLAUDECODE") == "1":
            return True
        if os.environ.get("CLAUDE_CODE_ENTRYPOINT") == "cli":
            return True

        # Check for Claude Code home directory
        if CLAUDE_HOME.exists():
            return True

        return False

    def get_workspace_detection_info(self) -> Dict[str, Any]:
        """Get detailed workspace detection information for debugging."""
        return {
            "claude_home": str(CLAUDE_HOME),
            "claude_home_exists": CLAUDE_HOME.exists(),
            "config_paths": [str(p) for p in CLAUDE_CONFIG_PATHS],
            "config_paths_exist": [p.exists() for p in CLAUDE_CONFIG_PATHS],
            "environment_variables": {
                "CLAUDECODE": os.environ.get("CLAUDECODE"),
                "CLAUDE_CODE_ENTRYPOINT": os.environ.get(
                    "CLAUDE_CODE_ENTRYPOINT"
                ),
                "CLAUDE_WORKSPACE": os.environ.get("CLAUDE_WORKSPACE"),
                "CLAUDE_PROJECT_ROOT": os.environ.get("CLAUDE_PROJECT_ROOT"),
                "CLAUDE_HOME": os.environ.get("CLAUDE_HOME"),
            },
            "indicators": CLAUDE_INDICATORS,
            "supports_conversations": self.supports_conversations(),
        }
