"""Test core server functionality."""

from unittest import mock

import pytest

from src.config.enums import ErrorCodes
from src.core.server import GandalfMCP


class TestGandalfMCPInputValidation:
    """Test input validation in GandalfMCP constructor."""

    def test_valid_project_root(self, temp_project_dir):
        """Test that valid project root is accepted."""
        server = GandalfMCP(project_root=str(temp_project_dir))
        assert server.project_root is not None

    def test_none_project_root(self):
        """Test that None project root is accepted."""
        server = GandalfMCP(project_root=None)
        assert server.project_root is not None

    def test_empty_project_root_raises_error(self):
        """Test that empty project root raises ValueError."""
        with pytest.raises(
            ValueError,
            match="Invalid project_root.*must be at least 1 characters",
        ):
            GandalfMCP(project_root="")

    def test_whitespace_project_root_raises_error(self):
        """Test that whitespace-only project root raises ValueError."""
        with pytest.raises(
            ValueError,
            match="Invalid project_root.*must be at least 1 characters",
        ):
            GandalfMCP(project_root="   ")

    def test_valid_explicit_ide(self):
        """Test that server initializes without explicit IDE parameter (removed)."""
        server = GandalfMCP()
        assert server.project_root is not None

    def test_none_explicit_ide(self):
        """Test that server initializes without explicit IDE parameter (removed)."""
        server = GandalfMCP()
        assert server.project_root is not None


class TestGandalfMCPInitialization:
    """Test GandalfMCP server initialization."""

    def setUp(self):
        """Set up test fixtures."""

    def test_init_with_project_root(self, temp_project_dir):
        """Test initialization with explicit project root."""
        server = GandalfMCP(project_root=str(temp_project_dir))

        assert server.project_root.resolve() == temp_project_dir.resolve()
        assert server.is_ready is False

    def test_init_without_project_root(self):
        """Test initialization without explicit project root."""
        server = GandalfMCP()

        assert server.project_root is not None
        assert server.is_ready is False

    def test_init_handlers_setup(self):
        """Test that all required handlers are set up."""
        server = GandalfMCP()

        expected_handlers = {
            "initialize",
            "notifications/initialized",
            "tools/list",
            "tools/call",
        }

        assert set(server.handlers.keys()) == expected_handlers


class TestProjectRootDetection:
    """Test project root detection functionality."""

    def test_server_project_root_resolution(self, temp_project_dir):
        """Test that server resolves project root correctly."""
        server = GandalfMCP(project_root=str(temp_project_dir))
        assert server.project_root.resolve() == temp_project_dir.resolve()

    def test_server_project_root_with_git(self, temp_project_dir):
        """Test server finds git repository root."""
        # Create a git repository
        git_dir = temp_project_dir / ".git"
        git_dir.mkdir(exist_ok=True)

        # Create a subdirectory
        sub_dir = temp_project_dir / "subdir"
        sub_dir.mkdir()

        # Initialize server from subdirectory - should find git root
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(str(sub_dir))
            server = GandalfMCP()
            assert server.project_root.resolve() == temp_project_dir.resolve()
        finally:
            os.chdir(original_cwd)


class TestMCPProtocolHandling:
    """Test MCP protocol request handling."""

    def test_handle_initialize_request(self):
        """Test initialize request handling."""
        server = GandalfMCP()
        request = {"method": "initialize", "id": "1"}

        response = server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "1"
        assert "protocolVersion" in response["result"]
        assert "capabilities" in response["result"]
        assert "serverInfo" in response["result"]

    def test_handle_tools_list_request(self):
        """Test tools/list request handling."""
        server = GandalfMCP()
        request = {"method": "tools/list", "id": "2"}

        response = server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "2"
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) > 0

    def test_handle_notifications_initialized(self):
        """Test notifications/initialized handling."""
        server = GandalfMCP()
        request = {"method": "notifications/initialized"}  # No id = notification

        response = server.handle_request(request)

        assert response is None  # Notifications don't return responses
        assert server.is_ready is True

    def test_handle_tools_call_request(self):
        """Test handling tools/call requests."""
        mock_tool = mock.Mock(
            return_value={"content": [{"type": "text", "text": "result"}]}
        )

        server = GandalfMCP()
        # Mock the tool handlers directly on the server instance
        server.tool_handlers = {"test_tool": mock_tool}

        request = {
            "jsonrpc": "2.0",
            "id": "test",
            "method": "tools/call",
            "params": {"name": "test_tool", "arguments": {"arg": "value"}},
        }

        response = server.handle_request(request)

        assert "result" in response
        assert "content" in response["result"]
        mock_tool.assert_called_once()

    def test_handle_unknown_method(self):
        """Test handling of unknown methods."""
        server = GandalfMCP()
        request = {"method": "unknown_method", "id": "4"}

        response = server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "4"
        assert response["error"]["code"] == ErrorCodes.METHOD_NOT_FOUND
        assert "Method not found" in response["error"]["message"]

    def test_handle_malformed_request_no_method(self):
        """Test handling of malformed requests without method."""
        server = GandalfMCP()
        request = {"id": "5"}  # Missing method

        response = server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "5"
        assert response["error"]["code"] == ErrorCodes.INVALID_REQUEST
        assert "missing method" in response["error"]["message"]

    def test_handle_notification_unknown_method(self):
        """Test notification with unknown method returns None."""
        server = GandalfMCP()
        request = {"method": "unknown_notification"}  # No id = notification

        response = server.handle_request(request)

        assert response is None


class TestToolCallHandling:
    """Test tool call specific functionality."""

    def test_tools_call_missing_params(self):
        """Test tools/call with missing params."""
        server = GandalfMCP()
        request = {"method": "tools/call", "id": "1"}  # Missing params

        response = server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "1"
        assert "error" in response["result"]
        assert response["result"]["error"]["code"] == ErrorCodes.INVALID_PARAMS
        assert "missing params" in response["result"]["error"]["message"]

    def test_tools_call_missing_tool_name(self):
        """Test tools/call with missing tool name."""
        server = GandalfMCP()
        request = {
            "method": "tools/call",
            "id": "2",
            "params": {"arguments": {}},  # Missing name
        }

        response = server.handle_request(request)

        assert "error" in response["result"]
        assert response["result"]["error"]["code"] == ErrorCodes.INVALID_PARAMS
        assert "missing tool name" in response["result"]["error"]["message"]

    def test_tools_call_unknown_tool(self):
        """Test tools/call with unknown tool."""
        server = GandalfMCP()
        # Don't add the tool to the handlers, so it remains unknown

        request = {
            "jsonrpc": "2.0",
            "id": "test",
            "method": "tools/call",
            "params": {"name": "unknown_tool", "arguments": {}},
        }

        response = server.handle_request(request)

        assert "result" in response
        assert "error" in response["result"]
        assert "Unknown tool" in response["result"]["error"]

    def test_tools_call_exception_handling(self):
        """Test tools/call exception handling."""
        mock_tool = mock.Mock(side_effect=ValueError("Test error"))

        server = GandalfMCP()
        server.tool_handlers = {"test_tool": mock_tool}

        request = {
            "jsonrpc": "2.0",
            "id": "test",
            "method": "tools/call",
            "params": {"name": "test_tool", "arguments": {}},
        }

        response = server.handle_request(request)

        assert "result" in response
        assert "error" in response["result"]
        assert "Test error" in response["result"]["error"]


class TestProjectRootUpdating:
    """Test project root behavior."""

    def test_project_root_set_during_initialization(self):
        """Test that project root is set during initialization."""
        server = GandalfMCP(project_root="/explicit/path")

        # Project root should be resolved during initialization
        assert server.project_root is not None
        # The adapter may resolve the path differently, but it should be set

    def test_project_root_dynamic_detection(self):
        """Test dynamic project root detection."""
        server = GandalfMCP()

        # Project root should be automatically detected
        assert server.project_root is not None

    def test_project_root_consistency(self):
        """Test project root remains consistent."""
        server = GandalfMCP()
        original_root = server.project_root

        # Project root should remain stable
        assert server.project_root == original_root


class TestComponentSetup:
    """Test component setup and initialization."""

    def test_server_initialization_success(self):
        """Test that server initializes successfully with all components."""
        server = GandalfMCP()

        # Server should initialize without exceptions
        assert server.is_ready is False
        assert server.project_root is not None
        assert len(server.tool_handlers) > 0
        assert len(server.tool_definitions) > 0

    def test_server_ready_state_handling(self):
        """Test server ready state handling."""
        server = GandalfMCP()

        # Initially not ready
        assert server.is_ready is False

        # Send initialized notification
        request = {"method": "notifications/initialized"}
        response = server.handle_request(request)

        # Should be ready now
        assert response is None  # Notifications return None
        assert server.is_ready is True


class TestRequestHandlingEdgeCases:
    """Test edge cases in request handling."""

    def test_handle_request_exception_in_handler(self):
        """Test exception handling within request handlers."""
        server = GandalfMCP()

        # Replace the handler in the handlers dictionary to raise an exception
        original_handler = server.handlers["initialize"]

        def failing_handler(request):
            raise ValueError("Handler error")

        server.handlers["initialize"] = failing_handler

        try:
            request = {"method": "initialize", "id": "1"}
            response = server.handle_request(request)

            assert "error" in response
            assert response["error"]["code"] == ErrorCodes.INTERNAL_ERROR
            assert "Internal error" in response["error"]["message"]
        finally:
            # Restore original handler
            server.handlers["initialize"] = original_handler

    def test_handle_request_exception_in_notification_handler(self):
        """Test exception in notification handler returns None."""
        server = GandalfMCP()

        with mock.patch.object(
            server,
            "_notifications_initialized",
            side_effect=ValueError("Handler error"),
        ):
            request = {"method": "notifications/initialized"}  # Notification
            response = server.handle_request(request)

            assert response is None

    def test_handle_request_top_level_exception(self):
        """Test top-level exception handling."""
        server = GandalfMCP()

        # Test with a request that causes an exception during JSON handling
        # malformed request that can't be processed
        request = {
            "method": "initialize",
            "id": 1,
            "malformed": object(),
        }  # object() can't be JSON serialized
        response = server.handle_request(request)

        # Should still return a valid response structure even if there's an internal error
        assert "jsonrpc" in response
        assert response["id"] == 1

    def test_handle_request_non_dict_input(self):
        """Test handling of non-dict input."""
        server = GandalfMCP()

        response = server.handle_request("not a dict")

        assert "error" in response
        assert response["error"]["code"] == ErrorCodes.INVALID_REQUEST
        assert response["id"] is None


class TestIntegrationScenarios:
    """Integration test scenarios."""

    def test_full_initialization_flow(self, temp_project_dir):
        """Test complete initialization flow."""
        server = GandalfMCP(project_root=str(temp_project_dir))

        # Initialize
        init_request = {"method": "initialize", "id": "1"}
        init_response = server.handle_request(init_request)

        assert init_response["result"]["protocolVersion"]
        assert not server.is_ready

        # Send initialized notification
        notif_request = {"method": "notifications/initialized"}
        notif_response = server.handle_request(notif_request)

        assert notif_response is None
        assert server.is_ready

        # List tools
        tools_request = {"method": "tools/list", "id": "2"}
        tools_response = server.handle_request(tools_request)

        assert len(tools_response["result"]["tools"]) > 0


class TestPerformanceTracking:
    """Test performance tracking in tool calls."""

    def test_tool_call_performance_tracking(self):
        """Test tool call performance tracking."""
        mock_tool = mock.Mock(
            return_value={"content": [{"type": "text", "text": "result"}]}
        )

        server = GandalfMCP()
        server.tool_handlers = {"test_tool": mock_tool}

        request = {
            "jsonrpc": "2.0",
            "id": "test",
            "method": "tools/call",
            "params": {"name": "test_tool", "arguments": {}},
        }

        with mock.patch("src.core.server.log_operation_time") as mock_log_time:
            server.handle_request(request)
            mock_log_time.assert_called_once()

    def test_tool_call_performance_tracking_on_error(self):
        """Test tool call performance tracking on error."""
        mock_tool = mock.Mock(side_effect=ValueError("Test error"))

        server = GandalfMCP()
        server.tool_handlers = {"test_tool": mock_tool}

        request = {
            "jsonrpc": "2.0",
            "id": "test",
            "method": "tools/call",
            "params": {"name": "test_tool", "arguments": {}},
        }

        with mock.patch("src.core.server.log_operation_time") as mock_log_time:
            server.handle_request(request)
            mock_log_time.assert_called_once()


# Test fixtures and utilities
@pytest.fixture
def mock_tool_handlers():
    """Mock tool handlers for testing."""
    return {
        "test_tool": mock.Mock(return_value={"success": True}),
        "failing_tool": mock.Mock(side_effect=ValueError("Tool error")),
    }


@pytest.fixture
def sample_requests():
    """Sample MCP requests for testing."""
    return {
        "initialize": {"method": "initialize", "id": "1"},
        "tools_list": {"method": "tools/list", "id": "2"},
        "notification": {"method": "notifications/initialized"},
        "tool_call": {
            "method": "tools/call",
            "id": "3",
            "params": {"name": "test_tool", "arguments": {}},
        },
    }
