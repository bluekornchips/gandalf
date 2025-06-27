"""
Core MCP server implementation for Gandalf.
Handles JSON-RPC communication and tool dispatch.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from src.adapters.factory import AdapterFactory
from src.config.constants.core import (
    MCP_PROTOCOL_VERSION,
    SERVER_CAPABILITIES,
    SERVER_INFO,
)
from src.tool_calls.conversation_aggregator import (
    CONVERSATION_AGGREGATOR_TOOL_DEFINITIONS,
    CONVERSATION_AGGREGATOR_TOOL_HANDLERS,
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
from src.utils.common import log_debug, log_error, log_info
from src.utils.performance import (
    log_operation_time,
    start_timer,
)

# Base tool handlers and definitions (conversation tools added dynamically)
BASE_TOOL_HANDLERS = {
    **FILE_TOOL_HANDLERS,
    **PROJECT_TOOL_HANDLERS,
    **CONVERSATION_AGGREGATOR_TOOL_HANDLERS,  # Add conversation tools first
}

BASE_TOOL_DEFINITIONS = (
    FILE_TOOL_DEFINITIONS
    + PROJECT_TOOL_DEFINITIONS
    + CONVERSATION_AGGREGATOR_TOOL_DEFINITIONS  # Add conversation tools first
)


@dataclass
class InitializationConfig:
    """Configuration for server initialization."""

    project_root: Optional[str] = None
    enable_logging: bool = True
    explicit_ide: Optional[str] = None


class GandalfMCP:
    """Gandalf MCP server for code assistance."""

    def __init__(
        self,
        project_root: Optional[str] = None,
        config: Optional[InitializationConfig] = None,
        explicit_ide: Optional[str] = None,
    ):
        """Initialize GandalfMCP"""
        self.config = config or InitializationConfig(
            project_root=project_root, explicit_ide=explicit_ide
        )

        self.is_ready = False

        # Create IDE adapter for environment-specific behavior
        config_explicit_ide = self.config.explicit_ide if self.config else None
        effective_explicit_ide = explicit_ide or config_explicit_ide
        config_project_root = self.config.project_root if self.config else None
        effective_project_root = project_root or config_project_root

        self.primary_adapter = AdapterFactory.create_adapter(
            explicit_ide=effective_explicit_ide,
            project_root=effective_project_root,
        )

        # Use adapter to resolve project root
        self.project_root = self.primary_adapter.resolve_project_root(
            effective_project_root
        )

        # Build tool handlers and definitions - dynamically detect available conversation tools
        self.tool_handlers = {
            **BASE_TOOL_HANDLERS,
        }

        self.tool_definitions = list(BASE_TOOL_DEFINITIONS)

        # Dynamically add conversation tools based on what's available
        self._detect_and_add_conversation_tools()

        # Request handlers
        self.handlers = {
            "initialize": self._initialize,
            "notifications/initialized": self._notifications_initialized,
            "tools/list": self._tools_list,
            "tools/call": self._tools_call,
            "ListOfferings": self._list_offerings,
        }

        log_info(
            f"Gandalf MCP server initialized:\n"
            f"  Primary IDE: {self.primary_adapter.ide_name}\n"
            f"  Project root: {self.project_root}\n"
            f"  Conversation support: {self.primary_adapter.supports_conversations()}\n"
            f"  Total tools available: {len(self.tool_definitions)}"
        )

    def _detect_and_add_conversation_tools(self) -> None:
        """Dynamically detect and add available conversation tools based on environment."""
        try:
            # Always add tools from the primary adapter
            primary_handlers = self.primary_adapter.get_conversation_handlers()
            primary_tools = self.primary_adapter.get_conversation_tools()

            if primary_handlers:
                self.tool_handlers.update(primary_handlers)
                self.tool_definitions.extend(primary_tools.values())
                log_info(
                    f"Added {len(primary_handlers)} conversation tools from {self.primary_adapter.ide_name}"
                )

            # Try to detect and add tools from other available IDEs
            self._try_add_secondary_ide_tools()

        except Exception as e:
            log_error(e, "Error detecting conversation tools")

    def _try_add_secondary_ide_tools(self) -> None:
        """Try to add conversation tools from other available IDEs."""
        try:
            # Determine what other IDEs might be available
            other_ides = []
            if self.primary_adapter.ide_name == "cursor":
                other_ides = ["claude-code"]
            elif self.primary_adapter.ide_name == "claude-code":
                other_ides = ["cursor"]

            for ide_name in other_ides:
                try:
                    # Try to create adapter for secondary IDE
                    secondary_adapter = AdapterFactory.create_adapter(
                        explicit_ide=ide_name,
                        project_root=str(self.project_root),
                    )

                    # Check if this IDE is actually available/detected
                    if secondary_adapter.detect_ide():
                        secondary_handlers = (
                            secondary_adapter.get_conversation_handlers()
                        )
                        secondary_tools = (
                            secondary_adapter.get_conversation_tools()
                        )

                        if secondary_handlers:
                            # Add tools with prefixes to avoid naming conflicts
                            prefix = f"{ide_name.replace('-', '_')}_"

                            for (
                                handler_name,
                                handler_func,
                            ) in secondary_handlers.items():
                                prefixed_name = f"{prefix}{handler_name}"
                                self.tool_handlers[prefixed_name] = (
                                    handler_func
                                )

                            for tool_name, tool_def in secondary_tools.items():
                                prefixed_tool = tool_def.copy()
                                prefixed_tool["name"] = f"{prefix}{tool_name}"
                                prefixed_tool["description"] = (
                                    f"[{ide_name.upper()}] {tool_def.get('description', '')}"
                                )
                                self.tool_definitions.append(prefixed_tool)

                            log_info(
                                f"Added {len(secondary_handlers)} conversation tools "
                                f"from {ide_name} (with prefix)"
                            )

                except Exception as e:
                    log_debug(f"Could not add tools from {ide_name}: {e}")

        except Exception as e:
            log_debug(f"Error trying to add secondary IDE tools: {e}")

    def _setup_components(self) -> None:
        """Set up components with graceful error handling."""
        try:
            log_info(
                "Components initialized successfully using direct Cursor query"
            )

        except (OSError, ImportError, AttributeError) as e:
            log_error(e, "component initialization")

    def _update_project_root_if_needed(self) -> None:
        """Update project root if needed (now handled by adapter)."""
        # Project root detection is handled by the IDE adapter
        # This method is kept for compatibility but no longer updates the root

    def _initialize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialization request."""
        self._update_project_root_if_needed()

        return {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": SERVER_CAPABILITIES,
            "serverInfo": SERVER_INFO,
        }

    def _notifications_initialized(self, request: Dict[str, Any]) -> None:
        """Handle initialized notification.

        If client is ready to receive notifications, setup components and
        mark as ready.
        """
        if self.is_ready:
            return None

        self._setup_components()

        self.is_ready = True

        log_info("Gandalf MCP server is ready to receive requests!")
        return None

    def _tools_list(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools list request."""
        response = {"tools": self.tool_definitions}
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
            if tool_name in self.tool_handlers:
                result = self.tool_handlers[tool_name](arguments, **kwargs)
            else:
                result = AccessValidator.create_error_response(
                    f"Unknown tool: {tool_name}"
                )

            log_operation_time(operation_name, start_time)
            return result

        except (KeyError, TypeError, ValueError, OSError) as e:
            log_error(e, f"tool call: {tool_name}")
            log_operation_time(operation_name, start_time)
            return AccessValidator.create_error_response(
                f"Error executing {tool_name}: {str(e)}"
            )

    def handle_request(
        self, request: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
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
                response = {
                    "jsonrpc": "2.0",
                    "result": result,
                    "id": request.get("id"),
                }

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
