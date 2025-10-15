"""
Gandalf aggregates conversations from multiple agentic tools
and provides intelligent context for AI-assisted development.
"""

import asyncio
import sys
import traceback

from src.protocol.jsonrpc_server import JSONRPCServer
from src.tools.registry import ToolRegistry
from src.config.constants import SERVER_NAME
from src.utils.logger import log_info, log_error


class GandalfServer:
    """Main server implementation."""

    def __init__(self) -> None:
        """Initialize the server."""
        self.server = JSONRPCServer(SERVER_NAME)
        self.tool_registry = ToolRegistry()
        self._setup_tools()

    def _setup_tools(self) -> None:
        """Set up all available tools."""
        for tool_name in self.tool_registry.list_tool_names():
            tool = self.tool_registry.get_tool(tool_name)
            self.server.tools[tool_name] = tool

    async def run(self) -> None:
        """Run the server."""
        log_info("Starting Gandalf Server")
        await self.server.run()


def main() -> None:
    """Main entry point for the server."""
    # Broad exception handling is intentional here because this is the
    # top-level process boundary and it's easy.
    # We convert unexpected errors to a non-zero exit status and avoid
    # leaking stack traces to stdout/stderr. I assume this is generally good because PII.
    try:
        server = GandalfServer()
        asyncio.run(server.run())
    except KeyboardInterrupt:
        log_info("Server stopped by user.")
        sys.exit(0)
    except (OSError, RuntimeError, ValueError) as e:
        log_error(f"Server error: {str(e)}", {"traceback": traceback.format_exc()})
        sys.exit(1)
    except Exception as e:
        log_error(
            f"Unexpected server error: {str(e)}", {"traceback": traceback.format_exc()}
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
