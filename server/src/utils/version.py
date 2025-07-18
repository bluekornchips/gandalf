"""Version utility functions for the Gandalf MCP server."""

from pathlib import Path


def get_version() -> str:
    """Get version from VERSION file."""
    version_file = Path(__file__).parent.parent.parent.parent / "VERSION"
    try:
        return version_file.read_text().strip()
    except FileNotFoundError:
        raise FileNotFoundError("VERSION file not found")
