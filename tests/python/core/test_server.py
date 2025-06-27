"""Test core server functionality."""

from pathlib import Path
from unittest import mock

import pytest

from src.core.server import GandalfMCP, InitializationConfig


class TestInitializationConfig:
    """Test InitializationConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = InitializationConfig()
        assert config.project_root is None
        assert config.enable_logging is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = InitializationConfig(
            project_root="/custom/path", enable_logging=False
        )
        assert config.project_root == "/custom/path"
        assert config.enable_logging is False


class TestGandalfMCPInitialization:
    """Test GandalfMCP server initialization."""

    def setUp(self):
        """Set up test fixtures."""

    def test_init_with_project_root(self, temp_project_dir):
        """Test initialization with explicit project root."""
        server = GandalfMCP(project_root=str(temp_project_dir))

        assert server.project_root.resolve() == temp_project_dir.resolve()
        assert server.is_ready is False
        assert server.config.project_root == str(temp_project_dir)

    def test_init_with_config(self, temp_project_dir):
        """Test initialization with configuration object."""
        config = InitializationConfig(project_root=str(temp_project_dir))
        server = GandalfMCP(config=config)

        assert server.project_root.resolve() == temp_project_dir.resolve()
        assert server.config == config

    def test_init_without_project_root(self):
        """Test initialization without explicit project root."""
        server = GandalfMCP()

        assert server.project_root is not None
        assert server.is_ready is False
        assert server.config.project_root is None

    def test_init_handlers_setup(self):
        """Test that all required handlers are set up."""
        server = GandalfMCP()

        expected_handlers = {
            "initialize",
            "notifications/initialized",
            "tools/list",
            "tools/call",
            "ListOfferings",
        }

        assert set(server.handlers.keys()) == expected_handlers


class TestProjectRootDetection:
    """Test project root detection strategies through IDE adapters."""

    def test_server_uses_adapter_for_project_root(self):
        """Test that server uses IDE adapter for project root detection."""
        test_path = "/workspace/test"

        with mock.patch(
            "src.adapters.factory.AdapterFactory.create_adapter"
        ) as mock_create:
            mock_adapter = mock.Mock()
            mock_adapter.resolve_project_root.return_value = Path(test_path)
            mock_adapter.get_conversation_tools.return_value = {}
            mock_adapter.get_conversation_handlers.return_value = {}
            mock_adapter.ide_name = "test-ide"
            mock_adapter.supports_conversations.return_value = False
            mock_create.return_value = mock_adapter

            server = GandalfMCP(project_root=test_path)

            assert str(server.project_root) == test_path
            mock_adapter.resolve_project_root.assert_called_once_with(
                test_path
            )

    def test_server_adapter_integration_with_explicit_root(self):
        """Test server initialization with explicit project root."""
        test_path = "/explicit/root"

        with mock.patch(
            "src.adapters.factory.AdapterFactory.create_adapter"
        ) as mock_create:
            mock_adapter = mock.Mock()
            mock_adapter.resolve_project_root.return_value = Path(test_path)
            mock_adapter.get_conversation_tools.return_value = {}
            mock_adapter.get_conversation_handlers.return_value = {}
            mock_adapter.ide_name = "test-ide"
            mock_adapter.supports_conversations.return_value = False
            mock_create.return_value = mock_adapter

            server = GandalfMCP(project_root=test_path)

            # Verify adapter was created with the explicit root
            mock_create.assert_called_once_with(
                explicit_ide=None, project_root=test_path
            )
            assert str(server.project_root) == test_path


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
        request = {
            "method": "notifications/initialized"
        }  # No id = notification

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
        assert response["error"]["code"] == -32601
        assert "Method not found" in response["error"]["message"]

    def test_handle_malformed_request_no_method(self):
        """Test handling of malformed requests without method."""
        server = GandalfMCP()
        request = {"id": "5"}  # Missing method

        response = server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "5"
        assert response["error"]["code"] == -32600
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
        assert response["result"]["error"]["code"] == -32602
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
        assert response["result"]["error"]["code"] == -32602
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
    """Test dynamic project root updating."""

    def test_update_project_root_explicit_no_change(self):
        """Test that explicit project root is not updated."""
        server = GandalfMCP(project_root="/explicit/path")
        original_root = server.project_root

        server._update_project_root_if_needed()

        assert server.project_root == original_root

    def test_update_project_root_dynamic_change(self):
        """Test dynamic project root updating."""
        server = GandalfMCP()
        original_root = server.project_root

        server._update_project_root_if_needed()

        assert server.project_root == original_root

    def test_update_project_root_no_change(self):
        """Test no update when project root hasn't changed."""
        server = GandalfMCP()
        original_root = server.project_root

        server._update_project_root_if_needed()

        assert server.project_root == original_root


class TestComponentSetup:
    """Test component setup functionality."""

    def test_setup_components_success(self):
        """Test successful component setup."""
        server = GandalfMCP()

        # Should not raise any exceptions
        server._setup_components()

    @mock.patch("src.utils.common.log_info")
    def test_setup_components_exception_handling(self, mock_log_info):
        """Test component setup exception handling."""
        mock_log_info.side_effect = OSError("Setup error")
        server = GandalfMCP()

        # Should handle exception gracefully
        server._setup_components()


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
            assert response["error"]["code"] == -32603
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
        assert response["error"]["code"] == -32603
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

    def test_list_offerings_alias(self):
        """Test ListOfferings as alias for tools/list."""
        server = GandalfMCP()

        tools_request = {"method": "tools/list", "id": "1"}
        tools_response = server.handle_request(tools_request)

        offerings_request = {"method": "ListOfferings", "id": "2"}
        offerings_response = server.handle_request(offerings_request)

        # Should return same tools
        assert (
            tools_response["result"]["tools"]
            == offerings_response["result"]["tools"]
        )


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
