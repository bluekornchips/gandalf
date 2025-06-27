"""
File filtering constants for Gandalf MCP server.

Contains patterns and directories to exclude during file operations.
"""

# Filtering: Directory exclusion patterns for find operations
FIND_EXCLUDE_DIRS = [
    "__pycache__",
    ".git",
    "node_modules",
    ".venv",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".coverage",
    "dist",
    "build",
    "target",
    ".gradle",
    ".idea",
    ".vscode",
    "logs",
    "log",
]

# Filtering: File exclusion patterns for find operations
FIND_EXCLUDE_PATTERNS = [
    # Compiled/Generated files
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.so",
    "*.dylib",
    "*.dll",
    # Temporary files
    "*.log",
    "*.tmp",
    "*.temp",
    "*.swp",
    "*.swo",
    "*~",
    # System files
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    # Lock files
    "*.lock",
]
