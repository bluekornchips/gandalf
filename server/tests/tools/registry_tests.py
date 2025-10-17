"""Test suite for tool registry implementation."""

from unittest.mock import patch
from typing import Any, Dict, List

import pytest

from src.tools.registry import ToolRegistry
from src.tools.base_tool import BaseTool
from src.protocol.models import ToolResult


class MockTool(BaseTool):
    """Mock tool for testing."""

    def __init__(self, name: str = "mock_tool", description: str = "Mock tool") -> None:
        self._name = name
        self._description = description

    @property
    def name(self) -> str:
        """Tool name."""
        return self._name

    @property
    def description(self) -> str:
        """Tool description."""
        return self._description

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Tool input schema."""
        return {"type": "object", "properties": {}}

    async def execute(self, arguments: Dict[str, Any] | None) -> List[ToolResult]:
        """Mock execute method."""
        return [ToolResult(text=f"Mock result from {self.name}")]


class FailingMockTool(BaseTool):
    """Mock tool that fails during execution."""

    @property
    def name(self) -> str:
        """Tool name."""
        return "failing_tool"

    @property
    def description(self) -> str:
        """Tool description."""
        return "Tool that fails"

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Tool input schema."""
        return {"type": "object", "properties": {}}

    async def execute(self, arguments: Dict[str, Any] | None) -> List[ToolResult]:
        """Execute method that raises an exception."""
        raise ValueError("Mock execution error")


class TestToolRegistry:
    """Test suite for ToolRegistry class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        # Mock the supported_tools to avoid importing actual tools
        with patch.object(ToolRegistry, "supported_tools", []):
            self.registry = ToolRegistry()

        # Add test tools manually
        self.mock_tool = MockTool("test_tool", "Test tool for registry")
        self.registry.register_tool(self.mock_tool)

    def test_registry_initialization(self) -> None:
        """Test that registry initializes correctly."""
        with patch.object(ToolRegistry, "supported_tools", [MockTool]):
            registry = ToolRegistry()

        assert len(registry.list_tool_names()) == 1
        assert "mock_tool" in registry.list_tool_names()

    def test_register_tool(self) -> None:
        """Test tool registration functionality."""
        new_tool = MockTool("new_tool", "New test tool")
        self.registry.register_tool(new_tool)

        assert self.registry.has_tool("new_tool")
        assert self.registry.get_tool("new_tool") == new_tool

    def test_get_tool_existing(self) -> None:
        """Test retrieving an existing tool."""
        tool = self.registry.get_tool("test_tool")

        assert tool is not None
        assert tool.name == "test_tool"
        assert tool == self.mock_tool

    def test_get_tool_nonexistent(self) -> None:
        """Test retrieving a non-existent tool returns None."""
        tool = self.registry.get_tool("nonexistent_tool")

        assert tool is None

    def test_get_all_tools(self) -> None:
        """Test getting all tools as definitions."""
        definitions = self.registry.get_all_tools()

        assert isinstance(definitions, list)
        assert len(definitions) == 1
        # Note: This assumes BaseTool has get_tool_definition method

    def test_list_tool_names(self) -> None:
        """Test listing all registered tool names."""
        names = self.registry.list_tool_names()

        assert isinstance(names, list)
        assert "test_tool" in names

    def test_has_tool_existing(self) -> None:
        """Test checking for existing tool."""
        assert self.registry.has_tool("test_tool") is True

    def test_has_tool_nonexistent(self) -> None:
        """Test checking for non-existent tool."""
        assert self.registry.has_tool("nonexistent_tool") is False

    @pytest.mark.asyncio
    async def test_execute_tool_success(self) -> None:
        """Test successful tool execution."""
        result = await self.registry.execute_tool("test_tool", {"arg": "value"})

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].text == "Mock result from test_tool"

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self) -> None:
        """Test executing unknown tool returns error."""
        result = await self.registry.execute_tool("unknown_tool", {})

        assert isinstance(result, list)
        assert len(result) == 1
        assert "Unknown tool: unknown_tool" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_tool_execution_error(self) -> None:
        """Test tool execution error handling."""
        failing_tool = FailingMockTool()
        self.registry.register_tool(failing_tool)

        result = await self.registry.execute_tool("failing_tool", {})

        assert isinstance(result, list)
        assert len(result) == 1
        assert "Tool execution error:" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_tool_with_none_arguments(self) -> None:
        """Test executing tool with None arguments."""
        result = await self.registry.execute_tool("test_tool", None)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].text == "Mock result from test_tool"

    @pytest.mark.asyncio
    async def test_execute_tool_specific_exceptions(self) -> None:
        """Test handling of specific exception types."""
        # Test AttributeError
        with patch.object(
            self.mock_tool, "execute", side_effect=AttributeError("Attribute error")
        ):
            result = await self.registry.execute_tool("test_tool", {})
            assert "Tool execution error:" in result[0].text

        # Test TypeError
        with patch.object(
            self.mock_tool, "execute", side_effect=TypeError("Type error")
        ):
            result = await self.registry.execute_tool("test_tool", {})
            assert "Tool execution error:" in result[0].text

        # Test ValueError
        with patch.object(
            self.mock_tool, "execute", side_effect=ValueError("Value error")
        ):
            result = await self.registry.execute_tool("test_tool", {})
            assert "Tool execution error:" in result[0].text

        # Test KeyError
        with patch.object(self.mock_tool, "execute", side_effect=KeyError("Key error")):
            result = await self.registry.execute_tool("test_tool", {})
            assert "Tool execution error:" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_tool_unexpected_exception(self) -> None:
        """Test handling of unexpected exception types."""
        with patch.object(
            self.mock_tool, "execute", side_effect=RuntimeError("Unexpected error")
        ):
            result = await self.registry.execute_tool("test_tool", {})
            assert "Unexpected tool execution error:" in result[0].text

    def test_multiple_tool_registration(self) -> None:
        """Test registering multiple tools."""
        tool1 = MockTool("tool1", "First tool")
        tool2 = MockTool("tool2", "Second tool")

        self.registry.register_tool(tool1)
        self.registry.register_tool(tool2)

        names = self.registry.list_tool_names()
        assert "tool1" in names
        assert "tool2" in names
        assert len(names) == 3  # Including original test_tool

    def test_tool_overwrite(self) -> None:
        """Test that registering a tool with the same name overwrites the previous one."""
        original_tool = MockTool("duplicate_name", "Original tool")
        new_tool = MockTool("duplicate_name", "New tool")

        self.registry.register_tool(original_tool)
        tool = self.registry.get_tool("duplicate_name")
        assert tool is not None
        assert tool.description == "Original tool"

        self.registry.register_tool(new_tool)
        tool = self.registry.get_tool("duplicate_name")
        assert tool is not None
        assert tool.description == "New tool"

    @pytest.mark.asyncio
    async def test_error_logging_called(self) -> None:
        """Test that error logging is called with traceback information."""
        with patch("src.tools.registry.log_error") as mock_log_error:
            # Test unknown tool error
            await self.registry.execute_tool("unknown_tool", {})
            mock_log_error.assert_called()
            args, kwargs = mock_log_error.call_args
            assert "Unknown tool: unknown_tool" in args[0]
            assert "traceback" in kwargs[0]

            # Reset mock
            mock_log_error.reset_mock()

            # Test execution error
            failing_tool = FailingMockTool()
            self.registry.register_tool(failing_tool)
            await self.registry.execute_tool("failing_tool", {})
            mock_log_error.assert_called()
            args, kwargs = mock_log_error.call_args
            assert "Tool execution error:" in args[0]
            assert "traceback" in kwargs[0]

    def test_empty_registry_operations(self) -> None:
        """Test operations on empty registry."""
        empty_registry = ToolRegistry()

        assert empty_registry.list_tool_names() == []
        assert empty_registry.get_all_tools() == []
        assert not empty_registry.has_tool("any_tool")
        assert empty_registry.get_tool("any_tool") is None
