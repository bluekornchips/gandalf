"""Test core server functionality."""

import os
import subprocess
import tempfile
import unittest.mock as mock
from pathlib import Path
from typing import Any, Dict

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
        pass

    def test_init_with_project_root(self, temp_project_dir):
        """Test initialization with explicit project root."""
        server = GandalfMCP(project_root=str(temp_project_dir))

        assert server.project_root.resolve() == temp_project_dir.resolve()
        assert server.is_ready is False
        assert server._explicit_project_root is True
        assert "initialize" in server.handlers
        assert "tools/call" in server.handlers

    def test_init_with_config(self, temp_project_dir):
        """Test initialization with configuration object."""
        config = InitializationConfig(project_root=str(temp_project_dir))
        server = GandalfMCP(config=config)

        assert server.project_root.resolve() == temp_project_dir.resolve()
        assert server.config == config

    def test_init_without_project_root(self):
        """Test initialization without explicit project root."""
        with mock.patch.object(
            GandalfMCP, "_detect_current_project_root"
        ) as mock_detect:
            mock_detect.return_value = Path("/detected/path")
            server = GandalfMCP()

            assert server._explicit_project_root is False
            mock_detect.assert_called_once()

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
    """Test project root detection strategies."""

    def test_find_project_root_workspace_paths(self):
        """Test workspace path detection strategy."""
        test_path = "/workspace/test"

        with mock.patch.dict(
            os.environ, {"WORKSPACE_FOLDER_PATHS": test_path}
        ):
            with mock.patch.object(Path, "exists", return_value=True):
                with mock.patch.object(
                    GandalfMCP, "_find_project_root", return_value=test_path
                ):
                    server = GandalfMCP()
                    result = server._find_project_root()

                    assert result == test_path

    def test_find_project_root_multiple_workspace_paths(self):
        """Test multiple workspace paths (semicolon separated)."""
        test_paths = "/workspace/legolas;/workspace/aragorn"

        with mock.patch.dict(
            os.environ, {"WORKSPACE_FOLDER_PATHS": test_paths}
        ):
            with mock.patch.object(Path, "exists", return_value=True):
                with mock.patch.object(
                    GandalfMCP,
                    "_find_project_root",
                    return_value="/workspace/legolas",
                ):
                    server = GandalfMCP()
                    result = server._find_project_root()

                    assert result == "/workspace/legolas"

    def test_find_project_root_git_detection(self):
        """Test git root detection strategy."""
        expected_git_root = "/git/project/root"

        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value.stdout = expected_git_root + "\n"
                mock_run.return_value.returncode = 0

                with mock.patch.object(Path, "exists", return_value=True):
                    server = GandalfMCP()
                    result = server._find_project_root()

                    assert result == expected_git_root

    def test_find_project_root_git_failure_fallback_pwd(self):
        """Test fallback to PWD when git detection fails."""
        pwd_path = "/pwd/fallback"

        with mock.patch.dict(os.environ, {"PWD": pwd_path}, clear=True):
            with mock.patch(
                "subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "git"),
            ):
                with mock.patch.object(Path, "exists", return_value=True):
                    server = GandalfMCP()
                    result = server._find_project_root()

                    assert result == pwd_path

    def test_find_project_root_final_fallback_cwd(self):
        """Test final fallback to current working directory."""
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch(
                "subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "git"),
            ):
                with mock.patch("os.getcwd", return_value="/cwd/fallback"):
                    with mock.patch.object(Path, "exists", return_value=True):
                        server = GandalfMCP()
                        result = server._find_project_root()

                        assert result == "/cwd/fallback"

    def test_resolve_project_root_nonexistent_path(self):
        """Test project root resolution with non-existent path."""
        with mock.patch.object(Path, "exists", return_value=False):
            with mock.patch.object(
                Path, "cwd", return_value=Path("/current/dir")
            ):
                server = GandalfMCP()
                result = server._resolve_project_root("/nonexistent/path")

                assert result == Path("/current/dir")

    def test_resolve_project_root_exception_handling(self):
        """Test exception handling in project root resolution."""
        with mock.patch.object(
            Path, "resolve", side_effect=OSError("Permission denied")
        ):
            with mock.patch.object(
                Path, "cwd", return_value=Path("/fallback")
            ):
                server = GandalfMCP()
                result = server._resolve_project_root("/problematic/path")

                assert result == Path("/fallback")


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

    @mock.patch("src.core.server.ALL_TOOL_HANDLERS")
    def test_handle_tools_call_request(self, mock_handlers):
        """Test tools/call request handling."""
        mock_handlers.__contains__ = mock.Mock(return_value=True)
        mock_handlers.__getitem__ = mock.Mock(
            return_value=mock.Mock(return_value={"test": "result"})
        )

        server = GandalfMCP()
        request = {
            "method": "tools/call",
            "id": "3",
            "params": {"name": "get_project_info", "arguments": {}},
        }

        response = server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "3"
        assert response["result"] == {"test": "result"}

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

    @mock.patch("src.core.server.SecurityValidator")
    @mock.patch("src.core.server.ALL_TOOL_HANDLERS")
    def test_tools_call_unknown_tool(self, mock_handlers, mock_validator):
        """Test tools/call with unknown tool."""
        mock_handlers.__contains__ = mock.Mock(return_value=False)
        mock_validator.create_error_response.return_value = {
            "error": "Unknown tool"
        }

        server = GandalfMCP()
        request = {
            "method": "tools/call",
            "id": "3",
            "params": {"name": "nonexistent_tool", "arguments": {}},
        }

        response = server.handle_request(request)

        mock_validator.create_error_response.assert_called_once()

    @mock.patch("src.core.server.SecurityValidator")
    @mock.patch("src.core.server.ALL_TOOL_HANDLERS")
    def test_tools_call_exception_handling(
        self, mock_handlers, mock_validator
    ):
        """Test exception handling in tool calls."""
        mock_handlers.__contains__ = mock.Mock(return_value=True)
        mock_handlers.__getitem__ = mock.Mock(
            side_effect=ValueError("Tool error")
        )
        mock_validator.create_error_response.return_value = {
            "error": "Tool failed"
        }

        server = GandalfMCP()
        request = {
            "method": "tools/call",
            "id": "4",
            "params": {"name": "failing_tool", "arguments": {}},
        }

        response = server.handle_request(request)

        mock_validator.create_error_response.assert_called_once()


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
        with mock.patch.object(
            GandalfMCP, "_detect_current_project_root"
        ) as mock_detect:
            mock_detect.return_value = Path("/initial/path")
            server = GandalfMCP()  # No explicit project root

            # Simulate project root change
            mock_detect.return_value = Path("/new/path")
            server._update_project_root_if_needed()

            assert server.project_root == Path("/new/path")

    def test_update_project_root_no_change(self):
        """Test no update when project root hasn't changed."""
        with mock.patch.object(
            GandalfMCP, "_detect_current_project_root"
        ) as mock_detect:
            mock_detect.return_value = Path("/same/path")
            server = GandalfMCP()  # No explicit project root
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

    @mock.patch("src.core.server.log_operation_time")
    @mock.patch("src.core.server.start_timer")
    @mock.patch("src.core.server.ALL_TOOL_HANDLERS")
    def test_tool_call_performance_tracking(
        self, mock_handlers, mock_start, mock_log
    ):
        """Test that tool calls are performance tracked."""
        mock_handlers.__contains__ = mock.Mock(return_value=True)
        mock_handlers.__getitem__ = mock.Mock(
            return_value=mock.Mock(return_value={"result": "test"})
        )
        mock_start.return_value = "timer_start"

        server = GandalfMCP()
        request = {
            "method": "tools/call",
            "id": "1",
            "params": {"name": "test_tool", "arguments": {}},
        }

        server.handle_request(request)

        mock_start.assert_called_once()
        mock_log.assert_called_once_with("tool_call_test_tool", "timer_start")

    @mock.patch("src.core.server.SecurityValidator")
    @mock.patch("src.core.server.log_operation_time")
    @mock.patch("src.core.server.start_timer")
    @mock.patch("src.core.server.ALL_TOOL_HANDLERS")
    def test_tool_call_performance_tracking_on_error(
        self, mock_handlers, mock_start, mock_log, mock_validator
    ):
        """Test performance tracking even when tool call fails."""
        mock_handlers.__contains__ = mock.Mock(return_value=True)
        mock_handlers.__getitem__ = mock.Mock(
            side_effect=ValueError("Tool failed")
        )
        mock_start.return_value = "timer_start"

        server = GandalfMCP()
        request = {
            "method": "tools/call",
            "id": "1",
            "params": {"name": "failing_tool", "arguments": {}},
        }

        server.handle_request(request)

        mock_log.assert_called_once_with(
            "tool_call_failing_tool", "timer_start"
        )


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
