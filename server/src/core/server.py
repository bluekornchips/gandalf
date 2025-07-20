"""
MCP server implementation for Gandalf.
Focuses on core conversation aggregation and project context.
"""

import os
from pathlib import Path
from typing import Any

from src.config.constants.file_system_context import FILE_SYSTEM_CONTEXT_INDICATORS
from src.config.constants.server import (
    MCP_PROTOCOL_VERSION,
    SERVER_CAPABILITIES,
    SERVER_INFO,
)
from src.config.enums import ErrorCodes
from src.config.weights import WeightsManager
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
from src.utils.common import log_error, log_info
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
TOOL_HANDLERS = {
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

    def __init__(self, project_root: Path | None = None):
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

        # Request handlers
        self.handlers = {
            "initialize": self._initialize,
            "notifications/initialized": self._notifications_initialized,
            "tools/list": self._tools_list,
            "tools/call": self._tools_call,
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
                if validation_status["error_count"] > 0:
                    log_info(
                        f"gandalf-weights.yaml has "
                        f"{validation_status['error_count']} errors. "
                        "Server will use default values for invalid settings. "
                        "Check the logs above for detailed error information."
                    )
            else:
                # Configuration is valid, log success message
                log_info("Configuration validation passed - all settings are valid")

        except Exception as e:
            log_error(e, "Error during configuration validation")
            log_info("Configuration validation failed, continuing with defaults")

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
        return {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": SERVER_CAPABILITIES,
            "serverInfo": SERVER_INFO,
        }

    def _notifications_initialized(self, request: dict[str, Any]) -> None:
        """Handle initialized notification."""
        if self.is_ready:
            return None

        self.is_ready = True
        return None

    def _tools_list(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle tools list request."""
        response = {"tools": self.tool_definitions}
        return response

    def _tools_call(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle tool call request."""
        # Check for missing params
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

        # Centralized performance tracking starts here
        timer = start_timer()
        operation_name = f"tool_call_{tool_name}"

        # Pass project root to tool handlers
        kwargs = {
            "project_root": self.project_root,  # Already a Path object
            "server_instance": self,
        }

        try:
            if tool_name in self.tool_handlers:
                result = self.tool_handlers[tool_name](arguments, **kwargs)
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

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
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

    def run(self):
        """Run the server."""
        from src.core.message_loop import MessageLoopHandler

        message_loop = MessageLoopHandler(self)
        message_loop.run_message_loop()
