"""
Server info tool implementation.
"""

from typing import Any, Dict, List

from src.tools.base_tool import BaseTool
from src.protocol.types import ToolResult
from src.config.constants import SERVER_CAPABILITIES, SERVER_DESCRIPTION, SERVER_NAME
from src.utils.common import get_version
from src.utils.logger import log_info


class ServerInfoTool(BaseTool):
    """Server info tool that returns server information."""

    @property
    def name(self) -> str:
        return "get_server_info"

    @property
    def description(self) -> str:
        return "Get information about the Gandalf MCP server"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, arguments: Dict[str, Any] | None) -> List[ToolResult]:
        log_info("Server info tool called")
        version = get_version()
        info = {
            "name": SERVER_NAME,
            "version": version,
            "description": SERVER_DESCRIPTION,
            "capabilities": SERVER_CAPABILITIES,
        }
        return [ToolResult(text=str(info))]
