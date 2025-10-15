"""
Lightweight JSON-RPC server implementation.
"""

import json
import sys
import asyncio
import traceback
from typing import Any, Dict, Optional

from src.config.constants import MCP_PROTOCOL_VERSION, SERVER_CAPABILITIES, SERVER_NAME
from src.utils.common import get_version
from src.utils.logger import log_error


class JSONRPCServer:
    """Lightweight JSON-RPC server implementation."""

    def __init__(self, name: str):
        """Initialize the JSON-RPC server."""
        self.name = name
        self.tools: Dict[str, Any] = {}
        self.request_id = 0

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming JSON-RPC requests."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        if method == "initialize":
            return self._initialize(params, request_id)
        elif method == "notifications/initialized":
            return None
        elif method == "tools/list":
            return self._list_tools(request_id)
        elif method == "tools/call":
            return await self._call_tool(params, request_id)
        else:
            return self._error_response(-32601, "Method not found", request_id)

    def _initialize(
        self, params: Dict[str, Any], request_id: Optional[int]
    ) -> Dict[str, Any]:
        """Initialize the MCP server following the official specification."""
        try:
            version = get_version()
        except (FileNotFoundError, ValueError, RuntimeError, OSError) as e:
            log_error(
                f"Failed to get version: {str(e)}",
                {"traceback": traceback.format_exc()},
            )
            version = "1.0.0"
        except Exception as e:
            log_error(
                f"Unexpected error getting version: {str(e)}",
                {"traceback": traceback.format_exc()},
            )
            version = "1.0.0"

        response = {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": SERVER_CAPABILITIES,
                "serverInfo": {"name": SERVER_NAME, "version": version},
            },
        }
        if request_id is not None:
            response["id"] = request_id
        return response

    def _list_tools(self, request_id: Optional[int]) -> Dict[str, Any]:
        """List available tools."""
        tools = []
        for tool_name, tool in self.tools.items():
            tools.append(
                {
                    "name": tool_name,
                    "description": tool.description,
                    "inputSchema": tool.input_schema,
                }
            )

        response = {"jsonrpc": "2.0", "result": {"tools": tools}}
        if request_id is not None:
            response["id"] = request_id
        return response

    async def _call_tool(
        self, params: Dict[str, Any], request_id: Optional[int]
    ) -> Dict[str, Any]:
        """Execute a tool call."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self.tools:
            return self._error_response(
                -32601, f"Unknown tool: {tool_name}", request_id
            )

        try:
            tool = self.tools[tool_name]
            result = await tool.execute(arguments)
            # Convert ToolResult objects to serializable format
            serializable_result = []
            for item in result:
                if hasattr(item, "text"):
                    serializable_result.append(
                        {
                            "type": getattr(item, "type", "text"),
                            "text": getattr(item, "text", ""),
                            "data": getattr(item, "data", None),
                        }
                    )
                else:
                    serializable_result.append(str(item))

            response = {
                "jsonrpc": "2.0",
                "result": {"content": serializable_result},
            }
            if request_id is not None:
                response["id"] = request_id
            return response
        except (AttributeError, TypeError, KeyError) as e:
            error_msg = f"Tool execution error: {str(e)}"
            log_error(error_msg, {"traceback": traceback.format_exc()})
            return self._error_response(-32603, error_msg, request_id)
        except Exception as e:
            error_msg = f"Unexpected tool execution error: {str(e)}"
            log_error(error_msg, {"traceback": traceback.format_exc()})
            return self._error_response(-32603, error_msg, request_id)

    def _error_response(
        self, code: int, message: str, request_id: Optional[int]
    ) -> Dict[str, Any]:
        """Create error response."""
        response = {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
        }
        if request_id is not None:
            response["id"] = request_id
        return response

    async def run(self) -> None:
        """Run the server with stdio communication."""
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                if not line:
                    break

                request = json.loads(line.strip())
                response = await self.handle_request(request)
                if response is not None:
                    print(json.dumps(response))
                    sys.stdout.flush()
            except json.JSONDecodeError as e:
                log_error(
                    f"JSON decode error: {str(e)}",
                    {"traceback": traceback.format_exc()},
                )
                continue
            except (OSError, IOError, ValueError) as e:
                log_error(
                    f"Server communication error: {str(e)}",
                    {"traceback": traceback.format_exc()},
                )
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": f"Communication error: {str(e)}",
                    },
                }
                print(json.dumps(error_response))
                sys.stdout.flush()
            except Exception as e:
                log_error(
                    f"Unexpected server error: {str(e)}",
                    {"traceback": traceback.format_exc()},
                )
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"},
                }
                print(json.dumps(error_response))
                sys.stdout.flush()
