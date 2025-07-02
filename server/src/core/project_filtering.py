"""
Project filtering and ignore patterns for the Gandalf MCP server.
"""

import subprocess
from pathlib import Path
from typing import List

from config.constants import (
    FIND_COMMAND_TIMEOUT,
    FIND_EXCLUDE_DIRS,
    FIND_EXCLUDE_PATTERNS,
    MAX_PROJECT_FILES,
)
from utils.common import log_debug, log_error


def filter_project_files(project_root: Path) -> List[str]:
    """Get filtered list of files using find command with exclusion patterns."""
    if not isinstance(project_root, Path):
        raise TypeError("project_root must be a Path object")

    if not project_root.exists():
        raise ValueError(f"Project root does not exist: {project_root}")

    if not project_root.is_dir():
        raise ValueError(f"Project root is not a directory: {project_root}")

    try:
        find_cmd = _build_find_command(project_root)

        result = subprocess.run(
            find_cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=FIND_COMMAND_TIMEOUT,
        )

        if result.returncode != 0:
            log_debug(f"Find command failed: {result.stderr}")
            return []

        files = _process_find_output(result.stdout)

        # Limit the number of files stored in the cache
        if len(files) > MAX_PROJECT_FILES:
            log_debug(f"Limiting files from {len(files)} to {MAX_PROJECT_FILES}")
            files = files[:MAX_PROJECT_FILES]

        return files

    except subprocess.TimeoutExpired as e:
        log_error(e, "filter_project_files")
        return []
    except (subprocess.SubprocessError, OSError, UnicodeDecodeError) as e:
        log_error(e, "filter_project_files")
        return []


def _build_find_command(project_root: Path) -> List[str]:
    """Build the find command with comprehensive exclusion patterns."""
    find_cmd = ["find", str(project_root), "-type", "f"]

    # Exclude directories
    for exclude_dir in FIND_EXCLUDE_DIRS:
        find_cmd.extend(["-not", "-path", f"*/{exclude_dir}/*"])

    # Exclude file patterns
    for exclude_pattern in FIND_EXCLUDE_PATTERNS:
        find_cmd.extend(["-not", "-name", exclude_pattern])

    return find_cmd


def _process_find_output(stdout: str) -> List[str]:
    """Process find command output into a clean list of file paths."""
    return [line.strip() for line in stdout.splitlines() if line.strip()]


def get_excluded_patterns() -> dict:
    """Get current exclusion patterns for debugging and testing purposes."""
    return {
        "directories": list(FIND_EXCLUDE_DIRS),
        "file_patterns": list(FIND_EXCLUDE_PATTERNS),
        "max_files": MAX_PROJECT_FILES,
        "timeout": FIND_COMMAND_TIMEOUT,
    }
