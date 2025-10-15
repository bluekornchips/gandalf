"""
Tool registry for managing all available tools.
"""

import traceback
from typing import Any, Dict, List

from src.protocol.types import ToolDefinition, ToolResult
from src.tools.base_tool import BaseTool
from src.tools.echo_tool import EchoTool
from src.tools.server_info_tool import ServerInfoTool
from src.tools.recall_conversations_tool import RecallConversationsTool
from src.utils.logger import log_error


class ToolRegistry:
    """Registry for managing all available tools."""

    supported_tools = [EchoTool, ServerInfoTool, RecallConversationsTool]

    def __init__(self) -> None:
        """Initialize the tool registry."""
        self._tools: Dict[str, BaseTool] = {}
        for tool in self.supported_tools:
            self.register_tool(tool())

    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool in the registry.

        Args:
            tool: The tool instance to register
        """
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool | None:
        """Get a tool by name.

        Args:
            name: The name of the tool to retrieve

        Returns:
            The tool instance if found, None otherwise
        """
        return self._tools.get(name)

    def get_all_tools(self) -> List[ToolDefinition]:
        """Get all registered tools as definitions."""
        return [tool.get_tool_definition() for tool in self._tools.values()]

    async def execute_tool(
        self, name: str, arguments: Dict[str, Any] | None
    ) -> List[ToolResult]:
        """Execute a tool with the given arguments.

        Args:
            name: The name of the tool to execute
            arguments: The arguments to pass to the tool

        Returns:
            List of tool results
        """
        tool = self.get_tool(name)
        if tool is None:
            error_msg = f"Unknown tool: {name}"
            log_error(error_msg, {"traceback": traceback.format_exc()})
            return [ToolResult(text=f"Error: {error_msg}")]

        try:
            return await tool.execute(arguments)
        except (AttributeError, TypeError, ValueError, KeyError) as e:
            error_msg = f"Tool execution error: {str(e)}"
            log_error(error_msg, {"traceback": traceback.format_exc()})
            return [ToolResult(text=f"Error: {error_msg}")]
        except Exception as e:
            error_msg = f"Unexpected tool execution error: {str(e)}"
            log_error(error_msg, {"traceback": traceback.format_exc()})
            return [ToolResult(text=f"Error: {error_msg}")]

    def list_tool_names(self) -> List[str]:
        """List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered.

        Args:
            name: The name of the tool to check

        Returns:
            True if the tool is registered, False otherwise
        """
        return name in self._tools
