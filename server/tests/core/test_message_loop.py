"""Test message loop functionality."""

import json
from io import StringIO
from unittest.mock import Mock, patch

import pytest

from src.config.enums import ErrorCodes
from src.core.message_loop import MessageLoopHandler


class TestMessageLoopHandler:
    """Test MessageLoopHandler class functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_server = Mock()
        self.output_stream = StringIO()
        self.handler = MessageLoopHandler(self.mock_server, self.output_stream)

    def test_init_default_output_stream(self):
        """Test initialization with default output stream."""
        handler = MessageLoopHandler(self.mock_server)
        assert handler.server == self.mock_server
        assert handler.output_stream is not None

    def test_init_custom_output_stream(self):
        """Test initialization with custom output stream."""
        custom_stream = StringIO()
        handler = MessageLoopHandler(self.mock_server, custom_stream)
        assert handler.server == self.mock_server
        assert handler.output_stream == custom_stream


class TestSingleRequestHandling:
    """Test single request handling functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_server = Mock()
        self.output_stream = StringIO()
        self.handler = MessageLoopHandler(self.mock_server, self.output_stream)

    def test_handle_empty_line(self):
        """Test handling empty lines."""
        result = self.handler.handle_single_request("")
        assert result is True
        self.mock_server.handle_request.assert_not_called()

    def test_handle_whitespace_only_line(self):
        """Test handling whitespace-only lines."""
        result = self.handler.handle_single_request("   \n\t  ")
        assert result is True
        self.mock_server.handle_request.assert_not_called()

    def test_handle_valid_request_with_response(self):
        """Test handling valid JSON-RPC request that returns a response."""
        request = {"jsonrpc": "2.0", "method": "tools/list", "id": "frodo_1"}
        response = {"jsonrpc": "2.0", "result": {"tools": []}, "id": "frodo_1"}

        self.mock_server.handle_request.return_value = response

        result = self.handler.handle_single_request(json.dumps(request))

        assert result is True
        self.mock_server.handle_request.assert_called_once_with(request)

        # Check response was written to output
        output = self.output_stream.getvalue()
        assert json.dumps(response) in output

    def test_handle_valid_request_no_response(self):
        """Test handling valid JSON-RPC request that returns no response (notification)."""
        request = {"jsonrpc": "2.0", "method": "notifications/initialized"}

        self.mock_server.handle_request.return_value = None

        result = self.handler.handle_single_request(json.dumps(request))

        assert result is True
        self.mock_server.handle_request.assert_called_once_with(request)

        # Check no response was written
        output = self.output_stream.getvalue()
        assert output == ""

    def test_handle_json_decode_error(self):
        """Test handling invalid JSON input."""
        invalid_json = '{"jsonrpc": "2.0", "method": "broken_json"'

        result = self.handler.handle_single_request(invalid_json)

        assert result is True
        self.mock_server.handle_request.assert_not_called()

        # Check error response was written
        output = self.output_stream.getvalue()
        response = json.loads(output)

        assert response["jsonrpc"] == "2.0"
        assert response["error"]["code"] == ErrorCodes.PARSE_ERROR
        assert "Parse error" in response["error"]["message"]
        assert response["id"] is None

    def test_handle_server_exception(self):
        """Test handling server exceptions during request processing."""
        request = {"jsonrpc": "2.0", "method": "tools/call", "id": "bilbo_2"}

        self.mock_server.handle_request.side_effect = RuntimeError(
            "The precious is lost!"
        )

        with patch("src.core.message_loop.log_error") as mock_log_error:
            result = self.handler.handle_single_request(json.dumps(request))

        assert result is True
        mock_log_error.assert_called_once()

        # Check error response was written
        output = self.output_stream.getvalue()
        response = json.loads(output)

        assert response["jsonrpc"] == "2.0"
        assert response["error"]["code"] == ErrorCodes.INTERNAL_ERROR
        assert "Internal error" in response["error"]["message"]
        assert "The precious is lost!" in response["error"]["message"]
        assert response["id"] == "bilbo_2"

    def test_handle_server_exception_no_request_id(self):
        """Test handling server exceptions when request ID extraction fails."""
        # Invalid JSON that will cause a parse error first, then an exception
        invalid_request = "not json at all"

        result = self.handler.handle_single_request(invalid_request)

        assert result is True

        # Should get a parse error response
        output = self.output_stream.getvalue()
        response = json.loads(output)
        assert response["error"]["code"] == ErrorCodes.PARSE_ERROR


class TestMessageLoop:
    """Test the main message loop functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_server = Mock()
        self.output_stream = StringIO()
        self.handler = MessageLoopHandler(self.mock_server, self.output_stream)

    def test_run_message_loop_single_request(self):
        """Test running message loop with single request."""
        request = {"jsonrpc": "2.0", "method": "initialize", "id": "sam_1"}
        response = {
            "jsonrpc": "2.0",
            "result": {"status": "ready"},
            "id": "sam_1",
        }

        input_stream = StringIO(json.dumps(request) + "\n")
        self.mock_server.handle_request.return_value = response

        self.handler.run_message_loop(input_stream)

        self.mock_server.handle_request.assert_called_once_with(request)
        output = self.output_stream.getvalue()
        assert json.dumps(response) in output

    def test_run_message_loop_multiple_requests(self):
        """Test running message loop with multiple requests."""
        requests = [
            {"jsonrpc": "2.0", "method": "initialize", "id": "merry_1"},
            {"jsonrpc": "2.0", "method": "tools/list", "id": "pippin_2"},
        ]

        input_lines = [json.dumps(req) for req in requests]
        input_stream = StringIO("\n".join(input_lines) + "\n")

        self.mock_server.handle_request.return_value = {
            "jsonrpc": "2.0",
            "result": {},
        }

        self.handler.run_message_loop(input_stream)

        assert self.mock_server.handle_request.call_count == 2
        self.mock_server.handle_request.assert_any_call(requests[0])
        self.mock_server.handle_request.assert_any_call(requests[1])

    def test_run_message_loop_keyboard_interrupt(self):
        """Test message loop handling keyboard interrupt gracefully."""
        # Create a mock input stream that raises KeyboardInterrupt
        mock_input_stream = Mock()
        mock_input_stream.__iter__ = Mock(side_effect=KeyboardInterrupt)

        with patch("src.core.message_loop.log_info") as mock_log_info:
            try:
                self.handler.run_message_loop(mock_input_stream)
            except KeyboardInterrupt:
                pytest.fail("KeyboardInterrupt should be handled internally and not propagate")
            mock_log_info.assert_called_once_with("Server shutdown requested")

    def test_run_message_loop_unexpected_exception(self):
        """Test message loop handling unexpected exceptions."""
        # Create a mock input stream that raises an unexpected exception
        mock_input_stream = Mock()
        mock_input_stream.__iter__ = Mock(side_effect=RuntimeError("Sauron's eye!"))

        with patch("src.core.message_loop.log_error") as mock_log_error:
            with pytest.raises(RuntimeError):
                self.handler.run_message_loop(mock_input_stream)

            mock_log_error.assert_called_once()

    def test_run_message_loop_exception_in_processing(self):
        """Test message loop handling exceptions during request processing."""
        # Create input with a valid request
        input_stream = StringIO('{"jsonrpc": "2.0", "method": "test", "id": 1}\n')

        # Mock handle_single_request to raise an exception
        with patch.object(
            self.handler,
            "handle_single_request",
            side_effect=RuntimeError("Processing error"),
        ):
            with patch("src.core.message_loop.log_error") as mock_log_error:
                with pytest.raises(RuntimeError, match="Processing error"):
                    self.handler.run_message_loop(input_stream)

                mock_log_error.assert_called_once()

    def test_run_message_loop_early_termination(self):
        """Test message loop termination when handle_single_request returns False."""
        # Create input with multiple requests
        input_lines = [
            '{"jsonrpc": "2.0", "method": "initialize", "id": "aragorn_1"}',
            '{"jsonrpc": "2.0", "method": "tools/list", "id": "legolas_2"}',
        ]
        input_stream = StringIO("\n".join(input_lines) + "\n")

        # Mock handle_single_request to return False on the first call
        with patch.object(
            self.handler, "handle_single_request", return_value=False
        ) as mock_handle:
            self.handler.run_message_loop(input_stream)

            # Should only be called once before breaking
            assert mock_handle.call_count == 1

    def test_run_message_loop_mixed_valid_invalid(self):
        """Test message loop with mix of valid and invalid requests."""
        input_lines = [
            '{"jsonrpc": "2.0", "method": "initialize", "id": "legolas_1"}',
            "invalid json here",
            '{"jsonrpc": "2.0", "method": "tools/list", "id": "gimli_2"}',
            "",  # empty line
        ]

        input_stream = StringIO("\n".join(input_lines) + "\n")
        self.mock_server.handle_request.return_value = {
            "jsonrpc": "2.0",
            "result": {},
        }

        self.handler.run_message_loop(input_stream)

        # Should have processed 2 valid requests (ignoring invalid and empty)
        assert self.mock_server.handle_request.call_count == 2

        # Should have one error response for the invalid JSON
        output = self.output_stream.getvalue()
        responses = [json.loads(line) for line in output.strip().split("\n") if line]

        error_responses = [r for r in responses if "error" in r]
        assert len(error_responses) == 1
        assert error_responses[0]["error"]["code"] == ErrorCodes.PARSE_ERROR


class TestResponseSending:
    """Test response sending functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_server = Mock()
        self.output_stream = StringIO()
        self.handler = MessageLoopHandler(self.mock_server, self.output_stream)

    def test_send_response_writes_json(self):
        """Test that responses are written as JSON."""
        response = {
            "jsonrpc": "2.0",
            "result": {"message": "Hello from the Shire"},
            "id": "test",
        }

        self.handler._send_response(response)

        output = self.output_stream.getvalue()
        parsed = json.loads(output)
        assert parsed == response

    def test_send_response_flushes_output(self):
        """Test that output stream is flushed after sending response."""
        response = {"jsonrpc": "2.0", "result": {}, "id": "test"}

        # Mock the flush method to verify it's called
        with patch.object(self.output_stream, "flush") as mock_flush:
            self.handler._send_response(response)
            mock_flush.assert_called_once()


class TestIntegrationScenarios:
    """Test integration scenarios for the message loop handler."""

    def test_realistic_mcp_session(self):
        """Test a realistic MCP session flow."""
        mock_server = Mock()
        output_stream = StringIO()
        handler = MessageLoopHandler(mock_server, output_stream)

        # Simulate a typical MCP session
        session_requests = [
            '{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "2024-11-05"}, "id": 1}',
            '{"jsonrpc": "2.0", "method": "notifications/initialized"}',
            '{"jsonrpc": "2.0", "method": "tools/list", "id": 2}',
            '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "get_project_info", "arguments": {}}, "id": 3}',
        ]

        # Mock server responses
        mock_responses = [
            {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                },
                "id": 1,
            },
            None,  # Notification - no response
            {
                "jsonrpc": "2.0",
                "result": {"tools": [{"name": "get_project_info"}]},
                "id": 2,
            },
            {
                "jsonrpc": "2.0",
                "result": {"content": [{"type": "text", "text": "Project info"}]},
                "id": 3,
            },
        ]

        mock_server.handle_request.side_effect = mock_responses

        input_stream = StringIO("\n".join(session_requests) + "\n")
        handler.run_message_loop(input_stream)

        assert mock_server.handle_request.call_count == 4

        output_lines = [
            line for line in output_stream.getvalue().strip().split("\n") if line
        ]
        assert len(output_lines) == 3  # 3 responses (notification has no response)
