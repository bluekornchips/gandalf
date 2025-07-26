"""
MCP server implementation for Gandalf.
Focuses on core conversation aggregation and project context.
"""

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from src.config.core_constants import (
    MCP_PROTOCOL_VERSION,
    SERVER_CAPABILITIES,
    SERVER_INFO,
)
from src.config.enums import ErrorCodes
from src.config.tool_config import FILE_SYSTEM_CONTEXT_INDICATORS
from src.config.weights import WeightsManager
from src.core.tool_registry import get_registered_agentic_tools
from src.tool_calls.aggregator import (
    CONVERSATION_AGGREGATOR_TOOL_DEFINITIONS,
    CONVERSATION_AGGREGATOR_TOOL_HANDLERS,
)
from src.tool_calls.export import (
    CONVERSATION_EXPORT_TOOL_DEFINITIONS,
    CONVERSATION_EXPORT_TOOL_HANDLERS,
)
from src.tool_calls.file_tools import (
    FILE_TOOL_DEFINITIONS,
    FILE_TOOL_HANDLERS,
)
from src.tool_calls.project_operations import (
    PROJECT_TOOL_DEFINITIONS,
    PROJECT_TOOL_HANDLERS,
)
from src.utils.access_control import AccessValidator
from src.utils.common import initialize_session_logging, log_error, log_info
from src.utils.database_pool import DatabaseService
from src.utils.jsonrpc import (
    create_error_response,
    create_success_response,
)
from src.utils.performance import log_operation_time, start_timer

TOOL_DEFINITIONS = [
    # Core conversation aggregation
    *CONVERSATION_AGGREGATOR_TOOL_DEFINITIONS,
    # Project context
    *PROJECT_TOOL_DEFINITIONS,
    # File operations
    *FILE_TOOL_DEFINITIONS,
    # Export functionality
    *CONVERSATION_EXPORT_TOOL_DEFINITIONS,
]

# Tool Handlers
TOOL_HANDLERS: dict[str, Any] = {
    **CONVERSATION_AGGREGATOR_TOOL_HANDLERS,
    "get_project_info": PROJECT_TOOL_HANDLERS["get_project_info"],
    "get_server_version": PROJECT_TOOL_HANDLERS["get_server_version"],
    "list_project_files": FILE_TOOL_HANDLERS["list_project_files"],
    "export_individual_conversations": CONVERSATION_EXPORT_TOOL_HANDLERS[
        "export_individual_conversations"
    ],
}


class GandalfMCP:
    """Gandalf MCP server with 6 essential tools for conversation aggregation
    and project context."""

    def __init__(self, project_root: Path | str | None = None):
        """Initialize the Gandalf MCP server."""
        # Validate project_root if provided as string
        if isinstance(project_root, str):
            if len(project_root.strip()) < 1:
                raise ValueError("Invalid project_root: must be at least 1 characters")
            project_root = Path(project_root)

        self.project_root = self._resolve_project_root(project_root)
        self.tool_definitions = TOOL_DEFINITIONS
        self.tool_handlers = TOOL_HANDLERS
        self.is_ready = False
        self.client_info = None  # Store client information for formatting

        self.db_service = DatabaseService()
        self.db_service.initialize()

        # Request handlers
        self.handlers = {
            "initialize": self._initialize,
            "notifications/initialized": self._notifications_initialized,
            "tools/list": self._tools_list,
            "tools/call": self._tools_call,
            "logging/setLevel": self._logging_setlevel,
        }

        self._validate_configuration()

    def _validate_configuration(self) -> None:
        """Validate server configuration during startup."""
        try:
            weights_config = WeightsManager.get_default()
            validation_status = weights_config.get_weights_validation_status()

            if validation_status["has_errors"]:
                log_info("Configuration validation found issues")
                log_info(f"Validation message: {validation_status['message']}")

                # Log a helpful message about configuration issues
                log_info(
                    f"gandalf-weights.yaml has "
                    f"{validation_status['error_count']} errors. "
                    "Server will use default values for invalid settings. "
                    "Check the logs above for detailed error information."
                )
            else:
                log_info("Configuration validation passed - all settings are valid")

        except (OSError, ValueError, TypeError, AttributeError) as e:
            log_error(e, "Error during configuration validation")
            log_info("Configuration validation failed, continuing with defaults")

    def _ensure_registry_initialized(self) -> None:
        """Ensure agentic tools registry is initialized on server startup."""
        try:
            registered_tools = get_registered_agentic_tools()

            if not registered_tools:
                log_info("Registry is empty, attempting auto-registration...")

                # Try to run auto-registration script
                import subprocess  # nosec B404 - safe registry script execution with fixed commands
                from pathlib import Path

                # Find the registry script relative to the server
                server_root = Path(__file__).parent.parent.parent
                registry_script = server_root / "tools" / "bin" / "registry"

                if registry_script.exists() and registry_script.is_file():
                    try:
                        # Run auto-registration
                        result = subprocess.run(  # nosec B603,B607 - safe registry script with validated path and fixed arguments
                            [str(registry_script), "auto-register"],
                            capture_output=True,
                            text=True,
                            timeout=30,
                        )

                        if result.returncode == 0:
                            log_info(
                                "Registry auto-registration completed successfully"
                            )
                            # Verify registration worked
                            updated_tools = get_registered_agentic_tools()
                            log_info(f"Registered tools: {updated_tools}")
                        else:
                            log_info(
                                f"Registry auto-registration failed: {result.stderr}"
                            )

                    except subprocess.TimeoutExpired:
                        log_info("Registry auto-registration timed out")
                    except (OSError, ValueError) as e:
                        log_info(f"Registry auto-registration error: {e}")
                else:
                    log_info(f"Registry script not found at: {registry_script}")
            else:
                log_info(f"Registry already initialized with tools: {registered_tools}")

        except Exception as e:
            log_error(e, "Error during registry initialization")
            log_info(
                "Registry initialization failed, continuing without auto-registration"
            )

    def _resolve_project_root(self, explicit_root: Path | None = None) -> Path:
        """Resolve project root directory with intelligent fallback logic."""
        if explicit_root:
            return explicit_root.resolve()

        workspace_paths = os.environ.get("WORKSPACE_FOLDER_PATHS")
        if workspace_paths:
            for workspace_path in workspace_paths.split(":"):
                workspace_path = workspace_path.strip()
                if workspace_path:
                    path_obj = Path(workspace_path).resolve()
                    if path_obj.exists():
                        return path_obj

        cwd = Path.cwd()

        # Look for git repository indicator
        current = cwd
        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent

        # Look for common project indicators
        current = cwd
        while current != current.parent:
            if any(
                (current / indicator).exists()
                for indicator in FILE_SYSTEM_CONTEXT_INDICATORS
            ):
                return current
            current = current.parent

        # Try PWD environment variable as fallback
        pwd_path = os.environ.get("PWD")
        if pwd_path:
            pwd_resolved = Path(pwd_path).resolve()
            if pwd_resolved.exists():
                return pwd_resolved

        return cwd

    def _initialize(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle initialization request."""
        # Capture client information for formatting decisions
        if "params" in request and "clientInfo" in request["params"]:
            client_info = request["params"]["clientInfo"]
            if client_info and isinstance(client_info, dict):
                self.client_info = client_info
                log_info(f"Client connected: {client_info.get('name', 'unknown')}")
            else:
                self.client_info = None
                log_info("Client connected: unknown (no client info provided)")

        return {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": SERVER_CAPABILITIES,
            "serverInfo": SERVER_INFO,
        }

    def _notifications_initialized(self, request: dict[str, Any]) -> None:
        """Handle initialized notification."""
        if self.is_ready:
            return None

        # Ensure registry is initialized on server startup
        self._ensure_registry_initialized()

        self.is_ready = True
        return None

    def _tools_list(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle tools list request."""
        response = {"tools": self.tool_definitions}
        return response

    def _logging_setlevel(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle logging/setLevel request."""
        if "params" not in request or "level" not in request["params"]:
            return {
                "error": {
                    "code": ErrorCodes.INVALID_PARAMS,
                    "message": "Invalid params: missing level parameter",
                }
            }

        level = request["params"]["level"]

        from src.utils.common import set_min_log_level

        if set_min_log_level(level):
            return {}  # Empty success response
        else:
            return {
                "error": {
                    "code": ErrorCodes.INVALID_PARAMS,
                    "message": f"Invalid log level: {level}. Must be one of: debug, info, notice, warning, error, critical, alert, emergency",
                }
            }

    def _tools_call(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle tool call request."""
        if "params" not in request:
            return {
                "error": {
                    "code": ErrorCodes.INVALID_PARAMS,
                    "message": "Invalid params: missing params",
                }
            }

        params = request["params"]
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            return {
                "error": {
                    "code": ErrorCodes.INVALID_PARAMS,
                    "message": "Invalid params: missing tool name",
                }
            }

        timer = start_timer()
        operation_name = f"tool_call_{tool_name}"

        kwargs = {
            "project_root": self.project_root,
            "server_instance": self,
            "client_info": self.client_info,
        }

        try:
            if tool_name in self.tool_handlers:
                result: dict[str, Any] = self.tool_handlers[tool_name](
                    arguments, **kwargs
                )
            else:
                result = AccessValidator.create_error_response(
                    f"Unknown tool: {tool_name}"
                )

            log_operation_time(operation_name, timer)
            return result

        except (KeyError, TypeError, ValueError, AttributeError) as e:
            log_error(e, f"tool call: {tool_name}")
            log_operation_time(operation_name, timer)
            return AccessValidator.create_error_response(
                f"Error executing {tool_name}: {str(e)}"
            )

    def handle_request(self, request: Any) -> dict[str, Any] | None:
        """Handle incoming MCP requests with validation and error handling."""
        # Input validation
        if not isinstance(request, dict):
            return create_error_response(
                ErrorCodes.INVALID_REQUEST,
                "Invalid request: must be a dictionary",
                None,
            )

        method = request.get("method")
        if not method:
            request_id = request.get("id")
            return create_error_response(
                ErrorCodes.INVALID_REQUEST,
                "Invalid request: missing method",
                request_id,
            )

        request_id = request.get("id")
        is_notification = request_id is None

        # Route to handler
        try:
            if method in self.handlers:
                result = self.handlers[method](request)

                # Notifications don't return responses
                if is_notification:
                    return None

                # Format successful response using utility
                return create_success_response(result, request_id)
            else:
                # Unknown method
                if is_notification:
                    # Unknown notifications ignored
                    return None

                return create_error_response(
                    ErrorCodes.METHOD_NOT_FOUND,
                    f"Method not found: {method}",
                    request_id,
                )

        except (KeyError, TypeError, ValueError, AttributeError) as e:
            log_error(e, f"Error handling request: {method}")

            if is_notification:
                return None

            return create_error_response(
                ErrorCodes.INTERNAL_ERROR,
                f"Internal error: {str(e)}",
                request_id,
            )

    def send_notification(self, method: str, params: dict[str, Any]) -> None:
        """Send an MCP notification"""
        # placeholder, likely won't implement for a long time.
        pass

    def send_tools_list_changed_notification(self) -> None:
        """Send tools/list_changed notification according to MCP 2025-06-18"""
        if hasattr(self, "output_stream"):
            notification = {
                "jsonrpc": "2.0",
                "method": "notifications/tools/list_changed",
            }

            print(
                json.dumps(notification),
                file=getattr(self, "output_stream", sys.stdout),
            )
            if hasattr(self, "output_stream"):
                self.output_stream.flush()

            log_info("Sent tools/list_changed notification")

    def update_tool_definitions(self, new_definitions: list[dict[str, Any]]) -> None:
        """Update tool definitions and notify clients of changes"""
        old_count = len(self.tool_definitions)
        self.tool_definitions = new_definitions
        new_count = len(self.tool_definitions)

        if old_count != new_count:
            log_info(f"Tool definitions updated: {old_count} -> {new_count} tools")
            self.send_tools_list_changed_notification()

    def run(self) -> None:
        """Run the server."""
        from src.core.message_loop import MessageLoopHandler

        session_id = str(uuid.uuid4())[:8]
        initialize_session_logging(session_id, self)

        message_loop = MessageLoopHandler(self)
        message_loop.run_message_loop()

    def shutdown(self) -> None:
        """Shutdown the server and cleanup resources."""
        if self.db_service:
            self.db_service.shutdown()
            log_info("Server shutdown completed")
