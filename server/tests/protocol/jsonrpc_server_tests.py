"""Test suite for JSON-RPC server implementation."""

from unittest.mock import AsyncMock, patch
from typing import Any, Dict

import pytest

from src.protocol.jsonrpc_server import JSONRPCServer
from src.protocol.models import ToolResult


class MockTool:
    """Mock tool for testing."""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description
        self.input_schema = {"type": "object", "properties": {}}

    async def execute(self, arguments: Dict[str, Any]) -> list[ToolResult]:
        """Mock execute method."""
        return [ToolResult(text=f"Mock result for {self.name}")]


class TestJSONRPCServer:
    """Test suite for JSONRPCServer class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.server = JSONRPCServer("TestServer")
        self.mock_tool = MockTool("test_tool", "Test tool description")
        self.server.tools["test_tool"] = self.mock_tool

    def test_server_initialization(self) -> None:
        """Test that server initializes correctly with required attributes."""
        assert self.server.name == "TestServer"
        assert isinstance(self.server.tools, dict)
        assert self.server.request_id == 0

    @pytest.mark.asyncio
    async def test_handle_request_initialize(self) -> None:
        """Test handling of initialize request."""
        request = {
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
            "id": 1,
        }

        with patch("src.protocol.jsonrpc_server.get_version", return_value="1.0.0"):
            response = await self.server.handle_request(request)

        assert response is not None
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert "protocolVersion" in response["result"]
        assert "capabilities" in response["result"]
        assert "serverInfo" in response["result"]

    @pytest.mark.asyncio
    async def test_handle_request_initialized_notification(self) -> None:
        """Test handling of initialized notification."""
        request = {"method": "notifications/initialized", "params": {}}

        response = await self.server.handle_request(request)

        assert response is None

    @pytest.mark.asyncio
    async def test_handle_request_list_tools(self) -> None:
        """Test handling of tools/list request."""
        request = {"method": "tools/list", "id": 2}

        response = await self.server.handle_request(request)

        assert response is not None
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) == 1
        assert response["result"]["tools"][0]["name"] == "test_tool"

    @pytest.mark.asyncio
    async def test_handle_request_call_tool_success(self) -> None:
        """Test successful tool call execution."""
        request = {
            "method": "tools/call",
            "params": {"name": "test_tool", "arguments": {}},
            "id": 3,
        }

        response = await self.server.handle_request(request)

        assert response is not None
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 3
        assert "result" in response
        assert "content" in response["result"]

    @pytest.mark.asyncio
    async def test_handle_request_call_unknown_tool(self) -> None:
        """Test calling an unknown tool returns error."""
        request = {
            "method": "tools/call",
            "params": {"name": "unknown_tool", "arguments": {}},
            "id": 4,
        }

        response = await self.server.handle_request(request)

        assert response is not None
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 4
        assert "error" in response
        assert response["error"]["code"] == -32601
        assert "Unknown tool: unknown_tool" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_handle_request_unknown_method(self) -> None:
        """Test handling of unknown method returns error."""
        request = {"method": "unknown/method", "id": 5}

        response = await self.server.handle_request(request)

        assert response is not None
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 5
        assert "error" in response
        assert response["error"]["code"] == -32601
        assert "Method not found" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_call_tool_execution_error(self) -> None:
        """Test tool execution error handling."""
        failing_tool = AsyncMock()
        failing_tool.execute.side_effect = ValueError("Test error")
        self.server.tools["failing_tool"] = failing_tool

        params = {"name": "failing_tool", "arguments": {}}

        response = await self.server._call_tool(params, 6)

        assert "error" in response
        assert response["error"]["code"] == -32603

    def test_initialize_with_version_error(self) -> None:
        """Test initialize method handles version retrieval errors."""
        with patch(
            "src.protocol.jsonrpc_server.get_version",
            side_effect=FileNotFoundError("Version file not found"),
        ):
            response = self.server._initialize({}, 7)

        assert response["result"]["serverInfo"]["version"] == "1.0.0"

    def test_list_tools_empty(self) -> None:
        """Test listing tools when no tools are available."""
        empty_server = JSONRPCServer("EmptyServer")

        response = empty_server._list_tools(8)

        assert response["result"]["tools"] == []

    def test_error_response_creation(self) -> None:
        """Test error response creation."""
        response = self.server._error_response(-32600, "Invalid Request", 9)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 9
        assert response["error"]["code"] == -32600
        assert response["error"]["message"] == "Invalid Request"

    def test_error_response_no_id(self) -> None:
        """Test error response creation without request ID."""
        response = self.server._error_response(-32600, "Invalid Request", None)

        assert response["jsonrpc"] == "2.0"
        assert "id" not in response
        assert response["error"]["code"] == -32600

    @pytest.mark.asyncio
    async def test_tool_result_serialization(self) -> None:
        """Test that ToolResult objects are properly serialized."""
        tool_result = ToolResult(text="Test result", type="text")
        mock_tool = AsyncMock()
        mock_tool.execute.return_value = [tool_result]
        self.server.tools["serialization_test"] = mock_tool

        params = {"name": "serialization_test", "arguments": {}}
        response = await self.server._call_tool(params, 10)

        assert "result" in response
        content = response["result"]["content"][0]
        assert content["type"] == "text"
        assert content["text"] == "Test result"

    @pytest.mark.asyncio
    async def test_handle_request_missing_params(self) -> None:
        """Test handling requests with missing parameters."""
        request = {"method": "tools/call", "id": 11}  # Missing params

        response = await self.server.handle_request(request)

        # Should handle gracefully, tool_name will be None and cause unknown tool error
        assert response is not None
        assert "error" in response
        assert response["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_initialize_without_request_id(self) -> None:
        """Test initialize method without request ID (notification)."""
        response = self.server._initialize({}, None)

        assert "id" not in response
        assert "result" in response

    @pytest.mark.asyncio
    async def test_list_tools_without_request_id(self) -> None:
        """Test list tools method without request ID."""
        response = self.server._list_tools(None)

        assert "id" not in response
        assert "result" in response
