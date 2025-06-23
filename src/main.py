"""
Gandalf MCP Entry Point

This module launches the Gandalf Model Context Protocol (MCP) server, to provide intelligent code assistance for the Cursor IDE.
It handles argument parsing, server initialization, and the main JSON-RPC loop.
All communication with Cursor is performed over stdin/stdout using the JSON-RPC protocol.
Logging is handled via the project logging utilities, except for JSON-RPC responses which are printed directly to stdout as required by the protocol.
"""

import argparse
import json
import sys

from src.core.server import GandalfMCP, InitializationConfig
from src.utils.common import log_error, log_info


def main() -> None:
    """Main entry point for Gandalf MCP server.

    Parses command-line arguments, initializes the server, and enters the main JSON-RPC loop. All protocol messages are handled via stdin/stdout. Errors during startup are logged and cause immediate exit.
    """
    parser = argparse.ArgumentParser(description="Gandalf")
    parser.add_argument(
        "--project-root",
        "-p",
        default=None,
        help="Path to the project root (default: auto-detect from Cursor workspace or git)",
    )

    try:
        args = parser.parse_args()
        config = InitializationConfig(project_root=args.project_root)
        server = GandalfMCP(args.project_root, config)

    except (TypeError, ValueError, OSError) as e:
        log_error(e, "Failed to start server")
        sys.exit(1)

    # Store original stdout for logging notifications
    original_stdout = sys.stdout

    class LoggingStdout:
        """Wrapper for stdout that logs JSON-RPC messages.

        Args:
            original_stdout (TextIO): The original sys.stdout object to wrap.
        """

        def __init__(self, original_stdout: object) -> None:
            self.original = original_stdout

        def write(self, data: str) -> int:
            return self.original.write(data)

        def flush(self) -> None:
            return self.original.flush()

        def __getattr__(self, name: str) -> object:
            return getattr(self.original, name)

    # Configure stdin/stdout for JSON-RPC communication
    try:
        sys.stdin.reconfigure(line_buffering=True)
        sys.stdout.reconfigure(line_buffering=False)
    except AttributeError:
        pass  # reconfigure not available in older Python versions

    sys.stdout = LoggingStdout(original_stdout)

    try:
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    request = json.loads(line)
                    response = server.handle_request(request)
                    if response is not None:
                        print(json.dumps(response))
                        sys.stdout.flush()
                except json.JSONDecodeError:
                    error = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32700, "message": "Parse error"},
                        "id": None,
                    }
                    print(json.dumps(error))
                    sys.stdout.flush()
            except (BrokenPipeError, EOFError, KeyboardInterrupt):
                log_info("Gandalf shutting down")
                break
            except (OSError, UnicodeDecodeError, ValueError) as e:
                log_error(e, "main server loop")
                continue
    finally:
        sys.stdout = original_stdout


if __name__ == "__main__":
    main()
