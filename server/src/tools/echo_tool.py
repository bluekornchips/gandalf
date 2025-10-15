"""
Echo tool implementation.
"""

from typing import Any, Dict, List

from src.tools.base_tool import BaseTool
from src.protocol.models import ToolResult
from src.utils.logger import log_info


class EchoTool(BaseTool):
    """
    Echo tool that returns the input message.
    Mainly used for sanity checking.
    """

    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echo back the input text"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The message to echo back"}
            },
            "required": ["message"],
        }

    async def execute(self, arguments: Dict[str, Any] | None) -> List[ToolResult]:
        """Execute the echo tool."""
        message = arguments.get("message", "") if arguments else ""
        log_info(f"Echo tool called with message: {message}")
        return [ToolResult(text=f"Echo: {message}")]
