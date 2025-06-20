"""
Ignored files handling for Gandalf MCP server.
"""

import subprocess
from pathlib import Path
from typing import List

from config.constants.file_filters import FIND_EXCLUDE_DIRS, FIND_EXCLUDE_PATTERNS
from config.constants.system import MAX_PROJECT_FILES
from src.utils.common import log_debug, log_error


def filter_files(project_root: Path) -> List[str]:
    """Get filtered list of files using find command."""
    try:
        find_cmd = ["find", str(project_root), "-type", "f"]

        # Directories
        for exclude_dir in FIND_EXCLUDE_DIRS:
            find_cmd.extend(["-not", "-path", f"*/{exclude_dir}/*"])

        # Files
        for exclude_pattern in FIND_EXCLUDE_PATTERNS:
            find_cmd.extend(["-not", "-name", exclude_pattern])

        result = subprocess.run(
            find_cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            log_debug(f"Find command failed: {result.stderr}")
            return []

        files = [line.strip() for line in result.stdout.splitlines() if line.strip()]

        # Limit the number of files stored in the cache
        if len(files) > MAX_PROJECT_FILES:
            files = files[:MAX_PROJECT_FILES]

        return files

    except subprocess.TimeoutExpired:
        log_error(Exception("Find command timed out"), "filter_files")
        return []
    except (subprocess.SubprocessError, OSError, UnicodeDecodeError) as e:
        log_error(e, "filter_files")
        return []
