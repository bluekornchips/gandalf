"""
Modular MCP server implementation using only Python standard library and shell commands.
"""

import argparse
import json
import signal
import sys

from src.core.server import GandalfMCP, InitializationConfig
from src.utils.common import log_info, log_error


def create_signal_handler(server):
    """Create a signal handler closure that has access to the server instance.

    Why we need this:
    - Signal handlers must be global functions with signature (signum, frame) even if we don't directly use them
    - Access to the server instance to call server.shutdown()
    - Avoid global variables or singleton patterns
    """

    def signal_handler(signum, frame):
        """Handle shutdown signals gracefully."""
        log_info(f"Received signal '{signum}'. Shutting down gracefully...")
        try:
            server.cleanup()
        except (OSError, AttributeError) as e:
            log_error(e, "server shutdown during signal handling")
        finally:
            sys.exit(0)

    return signal_handler


def main() -> None:
    """Main entry point for Gandalf."""
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

        signal_handler = create_signal_handler(server)
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    except (TypeError, ValueError, OSError) as e:
        print(f"Failed to start server: {e}", file=sys.stderr)
        sys.exit(1)

    # Store original stdout for logging notifications
    # Why we need this:
    # - MCP protocol communicates via JSON-RPC over stdin/stdout
    # - By replacing stdout with a LoggingStdout wrapper we intercept and log JSON-RPC messages
    # - This is a common pattern for MCP servers, apparently
    original_stdout = sys.stdout

    # Intercept and log JSON-RPC messages by replacing stdout
    class LoggingStdout:
        """Wrapper for stdout that logs JSON-RPC messages."""

        def __init__(self, original_stdout):
            self.original = original_stdout

        def write(self, data):
            return self.original.write(data)

        def flush(self):
            return self.original.flush()

        def __getattr__(self, name):
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
        # Restore original stdout
        sys.stdout = original_stdout

        # Clean up resources
        server.cleanup()


if __name__ == "__main__":
    main()
