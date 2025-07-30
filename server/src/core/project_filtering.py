"""
Project filtering and ignore patterns for the Gandalf MCP server.
"""

import fnmatch
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

from src.config.config_data import EXCLUDE_DIRECTORIES, EXCLUDE_FILE_PATTERNS
from src.config.core_constants import FIND_COMMAND_TIMEOUT, MAX_PROJECT_FILES
from src.utils.common import log_debug, log_error


def filter_project_files(project_root: Path) -> list[str]:
    """Get filtered list of files using pathlib with exclusion patterns."""
    if not isinstance(project_root, Path):
        raise TypeError("project_root must be a Path object")

    if not project_root.exists():
        raise ValueError(f"Project root does not exist: {project_root}")

    if not project_root.is_dir():
        raise ValueError(f"Project root is not a directory: {project_root}")

    try:
        files = []
        start_time = time.time()

        for file_path in _iterate_project_files(project_root):
            files.append(str(file_path))

            # Early termination if we have enough files or timeout
            if len(files) >= MAX_PROJECT_FILES:
                log_debug(f"Reached maximum file limit: {MAX_PROJECT_FILES}")
                break

            if time.time() - start_time > FIND_COMMAND_TIMEOUT:
                log_debug(f"File scanning timeout reached: {FIND_COMMAND_TIMEOUT}s")
                break

        log_debug(f"Found {len(files)} files in {time.time() - start_time:.2f}s")
        return files

    except (OSError, PermissionError, ValueError) as e:
        log_error(e, "filter_project_files")
        return []


def _iterate_project_files(project_root: Path) -> Generator[Path, None, None]:
    """Efficiently iterate through project files with exclusion patterns."""

    def _should_exclude_directory(dir_path: Path) -> bool:
        """Check if directory should be excluded."""
        dir_name = dir_path.name
        return dir_name in EXCLUDE_DIRECTORIES

    def _should_exclude_file(file_path: Path) -> bool:
        """Check if file should be excluded based on patterns."""
        filename = file_path.name
        for pattern in EXCLUDE_FILE_PATTERNS:
            if fnmatch.fnmatch(filename, pattern):
                return True
        return False

    def _walk_directory(
        directory: Path, max_depth: int = 10
    ) -> Generator[Path, None, None]:
        """Recursively walk directory with depth limit and exclusion filters."""
        if max_depth <= 0:
            return

        try:
            # Use iterdir() for better performance than rglob()
            # claude suggested this, I did not come up with it.
            for item in directory.iterdir():
                if item.is_file():
                    if not _should_exclude_file(item):
                        yield item
                elif item.is_dir():
                    if not _should_exclude_directory(item):
                        # recursion recursion recursion
                        yield from _walk_directory(item, max_depth - 1)
        except (PermissionError, OSError):
            pass

    yield from _walk_directory(project_root)


def get_excluded_patterns() -> dict[str, Any]:
    """Get current exclusion patterns for debugging and testing purposes."""
    return {
        "directories": list(EXCLUDE_DIRECTORIES),
        "file_patterns": list(EXCLUDE_FILE_PATTERNS),
        "max_files": MAX_PROJECT_FILES,
        "timeout": FIND_COMMAND_TIMEOUT,
    }
