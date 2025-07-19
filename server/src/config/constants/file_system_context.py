"""Constants for file system context root detection and management.

The file system context root is the top-level directory where MCP commands query from.
This is typically the project root directory that contains the code being analyzed.
"""

from typing import Final

FILE_SYSTEM_CONTEXT_INDICATORS: Final[list[str]] = [
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "requirements.txt",
    "setup.py",
    "Makefile",
    "README.md",
    ".git",
    ".gitignore",
]

MIN_CONTEXT_ROOT_DEPTH: Final[int] = 1
MAX_CONTEXT_ROOT_DEPTH: Final[int] = 10
USE_CURRENT_WORKING_DIRECTORY_AS_FALLBACK: Final[bool] = True
