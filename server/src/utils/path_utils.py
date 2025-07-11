"""Path utility functions."""

import os
from pathlib import Path


def get_project_root() -> Path:
    """Get project root by looking for marker files or using env var."""
    # Try environment variable first
    if root := os.getenv("GANDALF_PROJECT_ROOT"):
        return Path(root)

    # Look for project markers starting from this file
    current = Path(__file__).resolve()
    for parent in current.parents:
        # Look for project marker files (.git, pyproject.toml, setup.py, etc.)
        if any(
            (parent / marker).exists()
            for marker in [".git", "pyproject.toml", "setup.py", "README.md"]
        ):
            return parent

    # Fallback: from gandalf/server/src/utils/path_utils.py -> project root is 4 levels up
    return Path(__file__).resolve().parent.parent.parent.parent
