"""
Main entry point for Gandalf MCP Server.

This module launches the Gandalf Model Context Protocol (MCP) server to provide intelligent code assistance for agentic tools.

All communication with agentic tools is performed over stdin/stdout using the JSON-RPC protocol.
"""

import argparse
from pathlib import Path

from core.server import GandalfMCP


def main():
    """Run the Gandalf MCP server."""
    parser = argparse.ArgumentParser(
        description="Gandalf MCP Server - Code assistance for agentic tools"
    )

    parser.add_argument(
        "--project-root",
        type=str,
        help="Path to the project root (default: auto-detect from agentic tool workspace or git)",
        default=None,
    )

    args = parser.parse_args()

    # Set up project root - convert to string for the server
    if args.project_root:
        project_root = str(Path(args.project_root).resolve())
    else:
        project_root = None

    # Initialize and run the server
    server = GandalfMCP(project_root=project_root)
    server.run()


if __name__ == "__main__":
    main()
