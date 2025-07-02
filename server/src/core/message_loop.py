"""
JSON-RPC message loop handler for Gandalf MCP server.
"""

import json
import sys
from typing import Any, Dict, TextIO

from config.constants import ErrorCodes
from core.server import GandalfMCP
from utils.common import log_error, log_info
from utils.jsonrpc import create_error_response


class MessageLoopHandler:
    """Handles JSON-RPC message loop for MCP communication."""

    def __init__(self, server: GandalfMCP, output_stream: TextIO = sys.stdout):
        """Initialize message loop handler."""
        self.server = server
        self.output_stream = output_stream

    def handle_single_request(self, line: str) -> bool:
        """Process a single JSON-RPC request line."""
        line = line.strip()
        if not line:
            return True

        request_id = None

        try:
            request = json.loads(line)
            request_id = request.get("id")
            response = self.server.handle_request(request)

            if response:
                self._send_response(response)

        except json.JSONDecodeError as e:
            error_response = create_error_response(
                ErrorCodes.PARSE_ERROR, f"Parse error: {e}", request_id
            )
            self._send_response(error_response)

        except (
            RuntimeError,
            ValueError,
            TypeError,
            AttributeError,
            KeyError,
        ) as e:
            log_error(e, "Request handling")
            error_response = create_error_response(
                ErrorCodes.INTERNAL_ERROR, f"Internal error: {e}", request_id
            )
            self._send_response(error_response)

        return True

    def run_message_loop(self, input_stream: TextIO = sys.stdin) -> None:
        """Run the main JSON-RPC message loop."""
        try:
            for line in input_stream:
                if not self.handle_single_request(line):
                    break

        except KeyboardInterrupt:
            log_info("Server shutdown requested")
        except (RuntimeError, ValueError, TypeError, OSError) as e:
            log_error(e, "Server main loop")
            raise

    def _send_response(self, response: Dict[str, Any]) -> None:
        """Send JSON-RPC response to output stream."""
        print(json.dumps(response), file=self.output_stream)
        self.output_stream.flush()
