"""Core MCP server implementation for Gandalf."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from src.config.constants.server import (
    GANDALF_LOCAL_DIR,
    GANDALF_SCOPE,
    MCP_PROTOCOL_VERSION,
    SERVER_CAPABILITIES,
    SERVER_INFO,
    WORKSPACE_FOLDER_PATHS,
)
from src.config.enums import ErrorCodes
from src.config.weights import WeightsManager
from src.core.message_loop import MessageLoopHandler
from src.tool_calls.aggregator import (
    CONVERSATION_AGGREGATOR_TOOL_DEFINITIONS,
    CONVERSATION_AGGREGATOR_TOOL_HANDLERS,
)
from src.tool_calls.export import (
    CONVERSATION_EXPORT_TOOL_DEFINITIONS,
    CONVERSATION_EXPORT_TOOL_HANDLERS,
)
from src.tool_calls.file_tools import FILE_TOOL_DEFINITIONS, FILE_TOOL_HANDLERS
from src.tool_calls.project_operations import (
    PROJECT_TOOL_DEFINITIONS,
    PROJECT_TOOL_HANDLERS,
)
from src.utils.access_control import AccessValidator
from src.utils.common import log_error, log_info
from src.utils.jsonrpc import create_error_response, create_success_response
from src.utils.performance import log_operation_time, start_timer


class GandalfMCP:
    """Gandalf MCP server with 6 essential tools for conversation aggregation
    and project context."""

    TOOL_DEFINITIONS = [
        *CONVERSATION_AGGREGATOR_TOOL_DEFINITIONS,
        *PROJECT_TOOL_DEFINITIONS,
        *FILE_TOOL_DEFINITIONS,
        *CONVERSATION_EXPORT_TOOL_DEFINITIONS,
    ]

    TOOL_HANDLERS = {
        **CONVERSATION_AGGREGATOR_TOOL_HANDLERS,
        "get_project_info": PROJECT_TOOL_HANDLERS["get_project_info"],
        "get_server_version": PROJECT_TOOL_HANDLERS["get_server_version"],
        "list_project_files": FILE_TOOL_HANDLERS["list_project_files"],
        "export_individual_conversations": CONVERSATION_EXPORT_TOOL_HANDLERS[
            "export_individual_conversations"
        ],
    }

    def __init__(self, project_root: Optional[Path] = None) -> None:
        if isinstance(project_root, str):
            if len(project_root.strip()) < 1:
                raise ValueError("Invalid project_root: must be at least 1 characters")
            project_root = Path(project_root)

        self.project_root = self._resolve_project_root(project_root)
        self.tool_definitions = self.TOOL_DEFINITIONS
        self.tool_handlers = self.TOOL_HANDLERS
        self.is_ready = False

        self.handlers = {
            "initialize": self._initialize,
            "notifications/initialized": self._notifications_initialized,
            "tools/list": self._tools_list,
            "tools/call": self._tools_call,
        }

        self._validate_configuration()

    def _validate_configuration(self) -> None:
        try:
            weights_config = WeightsManager.get_default()
            validation_status = weights_config.get_weights_validation_status()

            if validation_status["has_errors"]:
                log_info("Configuration validation found issues")
                msg = validation_status["message"]
                log_info(f"Message: {msg}")

                if validation_status["error_count"] > 0:
                    count = validation_status["error_count"]
                    log_info(f"gandalf-weights.yaml: {count} errors")
                    log_info("Using default values")
            else:
                log_info("Configuration validation passed")

        except (ImportError, AttributeError, KeyError, TypeError) as e:
            log_error(e, "Error during configuration validation")
            log_info("Configuration validation failed, using defaults")

    def _resolve_project_root(self, explicit_root: Optional[Path] = None) -> Path:
        if explicit_root:
            return explicit_root.resolve()

        if GANDALF_SCOPE == "local" and GANDALF_LOCAL_DIR:
            local_path = Path(GANDALF_LOCAL_DIR).resolve()
            if local_path.exists():
                return local_path

        workspace_paths = WORKSPACE_FOLDER_PATHS
        if workspace_paths:
            for workspace_path in workspace_paths.split(":"):
                workspace_path = workspace_path.strip()
                if workspace_path:
                    path_obj = Path(workspace_path).resolve()
                    if path_obj.exists():
                        return path_obj

        cwd = Path.cwd()

        current = cwd
        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent

        pwd_path = os.environ.get("PWD")
        if pwd_path:
            pwd_resolved = Path(pwd_path).resolve()
            if pwd_resolved.exists():
                return pwd_resolved

        return cwd

    def _initialize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        _ = request
        return {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": SERVER_CAPABILITIES,
            "serverInfo": SERVER_INFO,
        }

    def _notifications_initialized(self, request: Dict[str, Any]) -> None:
        _ = request
        if self.is_ready:
            return
        self.is_ready = True

    def _tools_list(self, request: Dict[str, Any]) -> Dict[str, Any]:
        _ = request
        return {"tools": self.tool_definitions}

    def _tools_call(self, request: Dict[str, Any]) -> Dict[str, Any]:
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
            log_error(e, f"Error executing tool: {tool_name}")
            log_operation_time(operation_name, timer)
            return AccessValidator.create_error_response(
                f"Error executing {tool_name}: {str(e)}"
            )

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming MCP requests with validation and error handling."""
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

        try:
            if method in self.handlers:
                result = self.handlers[method](request)

                if is_notification:
                    return None

                return create_success_response(result, request_id)
            else:
                if is_notification:
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

    def run(self) -> None:
        """Run the server."""
        message_loop = MessageLoopHandler(self)
        message_loop.run_message_loop()
