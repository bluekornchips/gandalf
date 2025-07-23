"""
Main entry point for Gandalf MCP Server.
"""

import argparse
import sys
from pathlib import Path

from src.core.server import GandalfMCP


def main() -> None:
    """Run the Gandalf MCP server."""
    parser = argparse.ArgumentParser(
        description="Gandalf MCP Server - Code assistance for agentic tools"
    )

    parser.add_argument(
        "--project-root",
        type=str,
        help="Path to project root (default: auto-detect from workspace or git)",
        default=None,
    )

    try:
        args = parser.parse_args()
    except SystemExit:
        return

    # Validate and convert project root to Path
    project_root = None
    if args.project_root:
        try:
            project_root = Path(args.project_root).resolve()
            # Don't exit on nonexistent project root, let individual tools handle validation
            if project_root.exists() and not project_root.is_dir():
                print(
                    f"Error: Project root is not a directory: {project_root}",
                    file=sys.stderr,
                )
                sys.exit(1)
        except (OSError, ValueError) as e:
            print(f"Error: Invalid project root path: {e}", file=sys.stderr)
            sys.exit(1)

    server: GandalfMCP | None = None
    try:
        server = GandalfMCP(project_root=project_root)
        server.run()
    except KeyboardInterrupt:
        print("Server interrupted by user (SIGINT)", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to start server: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if server:
            server.shutdown()


if __name__ == "__main__":
    main()
