"""
Common utility functions for the Gandalf MCP Server.
"""

import subprocess
from pathlib import Path


def get_version() -> str:
    """Get the version from the VERSION file.

    Uses ``git rev-parse --show-toplevel`` to discover the repository root so the
    ``VERSION`` file can be read reliably regardless of the current working
    directory.
    Git is used solely for path discovery; no repository state is
    modified.

    Returns:
        The version string from the VERSION file.

    Raises:
        FileNotFoundError: If the VERSION file is not found.
        ValueError: If the VERSION file is empty or invalid.
        RuntimeError: If git command fails or project is not a git repository.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).parent,
        )
        project_root = Path(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to find git repository root: {e}") from e
    except FileNotFoundError:
        raise RuntimeError(
            "Git command not found. Make sure git is installed and available in PATH."
        ) from None

    version_file = project_root / "VERSION"

    if not version_file.exists():
        raise FileNotFoundError(f"VERSION file not found at {version_file}")

    try:
        with open(version_file, "r", encoding="utf-8") as f:
            version = f.read().strip()

        if not version:
            raise ValueError("VERSION file is empty")

        return version
    except OSError as e:
        raise ValueError(f"Error reading VERSION file: {e}") from e
