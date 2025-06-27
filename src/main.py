"""
Gandalf MCP Entry Point

This module launches the Gandalf Model Context Protocol (MCP) server, to provide intelligent code assistance for IDEs.
It handles argument parsing, server initialization, and the main JSON-RPC loop.
All communication with IDEs is performed over stdin/stdout using the JSON-RPC protocol.
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
        help="Path to the project root (default: auto-detect from IDE workspace or git)",
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

    # Main message loop
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
                response = server.handle_request(request)

                if response:
                    print(json.dumps(response), file=original_stdout)
                    original_stdout.flush()

            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": f"Parse error: {e}"},
                    "id": None,
                }
                print(json.dumps(error_response), file=original_stdout)
                original_stdout.flush()

            except Exception as e:
                log_error(e, "Request handling")
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {e}",
                    },
                    "id": request.get("id") if "request" in locals() else None,
                }
                print(json.dumps(error_response), file=original_stdout)
                original_stdout.flush()

    except KeyboardInterrupt:
        log_info("Server shutdown requested")
    except Exception as e:
        log_error(e, "Server main loop")
        sys.exit(1)


if __name__ == "__main__":
    main()
