"""
Core MCP server implementation for Gandalf.
Handles JSON-RPC communication and tool dispatch.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
import subprocess

from config.constants.core import (
    MCP_PROTOCOL_VERSION,
    SERVER_INFO,
    SERVER_CAPABILITIES,
    WORKSPACE_FOLDER_PATHS,
)
from src.utils.common import log_debug, log_info, log_error
from src.utils.performance import log_operation_time, start_timer
from src.utils.security import SecurityValidator

from src.tool_calls.conversation_ingestion import (
    CONVERSATION_INGESTION_TOOL_HANDLERS,
    CONVERSATION_INGESTION_TOOL_DEFINITIONS,
)

from src.tool_calls.file_tools import (
    FILE_TOOL_HANDLERS,
    FILE_TOOL_DEFINITIONS,
)

from src.tool_calls.project_operations import (
    PROJECT_TOOL_HANDLERS,
    PROJECT_TOOL_DEFINITIONS,
)

from src.tool_calls.cursor_query import (
    CURSOR_QUERY_TOOL_HANDLERS,
    CURSOR_QUERY_TOOL_DEFINITIONS,
)

ALL_TOOL_HANDLERS = {
    **FILE_TOOL_HANDLERS,
    **PROJECT_TOOL_HANDLERS,
    **CONVERSATION_INGESTION_TOOL_HANDLERS,
    **CURSOR_QUERY_TOOL_HANDLERS,
}

ALL_TOOL_DEFINITIONS = (
    FILE_TOOL_DEFINITIONS
    + PROJECT_TOOL_DEFINITIONS
    + CONVERSATION_INGESTION_TOOL_DEFINITIONS
    + CURSOR_QUERY_TOOL_DEFINITIONS
)


@dataclass
class InitializationConfig:
    """Configuration for server initialization."""

    project_root: Optional[str] = None
    enable_logging: bool = True


class GandalfMCP:
    """Gandalf MCP server for code assistance."""

    def __init__(
        self, project_root: str = None, config: Optional[InitializationConfig] = None
    ):
        """Initialize GandalfMCP"""
        self.config = config or InitializationConfig(project_root=project_root)

        # Core state
        self.is_ready = False
        # Track if project_root was explicitly provided (either directly or via config)
        config_project_root = self.config.project_root if self.config else None
        self._explicit_project_root = (
            project_root is not None or config_project_root is not None
        )

        # Use project_root from parameter first, then config, then detect
        effective_project_root = project_root or config_project_root
        self.project_root = self._resolve_project_root(effective_project_root)

        # Request handlers
        self.handlers = {
            "initialize": self._initialize,
            "notifications/initialized": self._notifications_initialized,
            "tools/list": self._tools_list,
            "tools/call": self._tools_call,
            "ListOfferings": self._list_offerings,
        }

        log_info(
            f"Gandalf MCP server initialized with project root: {self.project_root}"
        )

    def _find_project_root(self) -> str:
        """
        Find the project root using multiple strategies, prioritizing Cursor's workspace detection.

        1. WORKSPACE_FOLDER_PATHS env var from Cursor
        2. Git root detection in workspace paths first, then current directory
        3. PWD
        4. Current working directory
        """
        log_debug("Starting project root detection")

        # Strategy 1: Use WORKSPACE_FOLDER_PATHS from Cursor
        workspace_paths = WORKSPACE_FOLDER_PATHS
        if workspace_paths:
            log_info(f"Found WORKSPACE_FOLDER_PATHS: {workspace_paths}")
            paths = (
                workspace_paths.split(";")
                if ";" in workspace_paths
                else workspace_paths.split(":")
            )
            if paths and paths[0]:
                workspace_path = paths[0].strip()
                if Path(workspace_path).exists():
                    log_debug(f"Using workspace path: {workspace_path}")
                    return workspace_path
                else:
                    log_debug(f"Workspace path does not exist: {workspace_path}")
        else:
            log_debug("No WORKSPACE_FOLDER_PATHS environment variable found")

        # Strategy 2: Try git root (reliable for git projects)
        # First try workspace paths if available, then current directory
        git_check_paths = []

        # Add workspace paths to check for git
        if workspace_paths:
            workspace_check_paths = (
                workspace_paths.split(";")
                if ";" in workspace_paths
                else workspace_paths.split(":")
            )
            git_check_paths.extend(
                [p.strip() for p in workspace_check_paths if p.strip()]
            )

        # Also check current working directory as fallback
        git_check_paths.append(os.getcwd())

        for check_path in git_check_paths:
            try:
                log_debug(f"Checking for git repository in: {check_path}")

                result = subprocess.run(
                    ["git", "rev-parse", "--show-toplevel"],
                    cwd=check_path,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=10,
                )
                git_root = result.stdout.strip()
                if git_root and Path(git_root).exists() and git_root != "/":
                    log_info(f"Using git root: {git_root}")
                    return git_root
            except (
                subprocess.CalledProcessError,
                FileNotFoundError,
                subprocess.TimeoutExpired,
                OSError,
            ) as e:
                log_error(f"Git root detection failed for {check_path}: {e}")
                continue

        log_error("Git root detection failed for all paths")

        # Strategy 3: Use PWD environment variable
        pwd = os.getenv("PWD")
        if pwd and Path(pwd).exists() and pwd != "/":
            log_info(f"Using PWD: {pwd}")
            return pwd

        # Strategy 4: Fall back to current working directory
        cwd = os.getcwd()
        if Path(cwd).exists() and cwd != "/":
            log_info(f"Using current working directory: {cwd}")
            return cwd

        # Final fallback
        log_error("All detection strategies failed, using current working directory")
        return cwd

    def _detect_current_project_root(self) -> Path:
        """Detect the current project root using multiple strategies."""
        return Path(self._find_project_root()).resolve()

    def _resolve_project_root(self, project_root: Optional[str]) -> Path:
        """Resolve project root to Path object."""
        try:
            if project_root:
                resolved = Path(project_root).resolve()
                if not resolved.exists():
                    log_debug(
                        f"Warning: Project root does not exist yet: {resolved}. Falling back to current working directory: {Path.cwd()}"
                    )
                    return Path.cwd()
                return resolved
            else:
                return self._detect_current_project_root()
        except (OSError, ValueError, PermissionError) as e:
            log_error(e, "resolving project root")
            log_debug(f"Exception fallback to current working directory: {Path.cwd()}")
            return Path.cwd()

    def _setup_components(self) -> None:
        """Set up components with graceful error handling."""
        try:
            log_info("Components initialized successfully (using direct Cursor query)")

        except (OSError, ImportError, AttributeError) as e:
            log_error(e, "component initialization")

    def _update_project_root_if_needed(self) -> None:
        """Update project root if it has changed (for dynamic mode)."""
        # Don't change project root if it was explicitly provided
        if hasattr(self, "_explicit_project_root") and self._explicit_project_root:
            return

        current_project_root = self._detect_current_project_root()

        if current_project_root != self.project_root:
            log_debug(
                f"Project root changed from {self.project_root} to {current_project_root}"
            )
            self.project_root = current_project_root

    def _initialize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialization request."""
        self._update_project_root_if_needed()

        return {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": SERVER_CAPABILITIES,
            "serverInfo": SERVER_INFO,
        }

    def _notifications_initialized(self, request: Dict[str, Any]) -> None:
        """Handle initialized notification. If client is ready to receive notifications, setup components and mark as ready."""
        if self.is_ready:
            return None

        self._setup_components()

        self.is_ready = True

        log_info("Gandalf MCP server is ready to receive requests!")
        return None

    def _tools_list(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools list request."""
        response = {"tools": ALL_TOOL_DEFINITIONS}
        return response

    def _list_offerings(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list offerings request (tools/list alias)."""
        return self._tools_list(request)

    def _tools_call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool call request with centralized performance logging."""
        self._update_project_root_if_needed()

        if "params" not in request:
            log_debug("Missing params in tools/call request")
            return {
                "error": {
                    "code": -32602,
                    "message": "Invalid params: missing params",
                }
            }

        params = request["params"]
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            log_debug("Missing tool name in tools/call request")
            return {
                "error": {
                    "code": -32602,
                    "message": "Invalid params: missing tool name",
                }
            }

        # Centralized performance tracking starts here
        start_time = start_timer()
        operation_name = f"tool_call_{tool_name}"

        # Pass project root to tool handlers
        kwargs = {
            "project_root": Path(self.project_root),
            "server_instance": self,
        }

        try:
            if tool_name in ALL_TOOL_HANDLERS:
                result = ALL_TOOL_HANDLERS[tool_name](arguments, **kwargs)
            else:
                result = SecurityValidator.create_error_response(
                    f"Unknown tool: {tool_name}"
                )

            log_operation_time(operation_name, start_time)
            return result

        except (KeyError, TypeError, ValueError, OSError) as e:
            log_error(e, f"tool call: {tool_name}")
            log_operation_time(operation_name, start_time)
            return SecurityValidator.create_error_response(
                f"Error executing {tool_name}: {str(e)}"
            )

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming MCP requests."""
        try:

            method = request.get("method")
            if not method:
                log_debug("Invalid request - missing method")
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32600,
                        "message": "Invalid request: missing method",
                    },
                    "id": request.get("id"),
                }

            # No id field means it's a notification
            is_notification = "id" not in request

            # Find handler
            handler = self.handlers.get(method)
            if not handler:
                log_debug(f"No handler found for method: {method}")

                if is_notification:
                    return None

                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                    "id": request.get("id"),
                }

            # Call handler
            try:
                result = handler(request)

                # For notifications, don't return a response
                if is_notification:
                    return None

                # Wrap result in proper JSON-RPC format for requests
                response = {"jsonrpc": "2.0", "result": result, "id": request.get("id")}

                return response

            except (TypeError, KeyError, ValueError, AttributeError) as e:
                log_error(e, f"handler for {method}")

                if is_notification:
                    return None

                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}",
                    },
                    "id": request.get("id"),
                }

        except (KeyError, TypeError, AttributeError) as e:
            log_error(e, "request handling")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}",
                },
                "id": request.get("id") if isinstance(request, dict) else None,
            }

    def cleanup(self):
        """Clean up resources."""
        log_info("Gandalf MCP server cleaned up successfully")
