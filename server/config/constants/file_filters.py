"""
File filtering and exclusion patterns for Gandalf MCP server.
Contains patterns for excluding directories and files during project scanning.
"""

# Directory exclusion patterns for find command
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

# File exclusion patterns
FIND_EXCLUDE_PATTERNS = [
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.so",
    "*.dylib",
    "*.dll",
    "*.log",
    "*.tmp",
    "*.temp",
    "*.swp",
    "*.swo",
    "*~",
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    "*.lock",
]

# File operation constants
MAX_FILE_TYPES = 20
MAX_FILE_EXTENSION_LENGTH = 10
MAX_FILES_LIMIT = 10000
HIGH_PRIORITY_DISPLAY_LIMIT = 20
MEDIUM_PRIORITY_DISPLAY_LIMIT = 15
LOW_PRIORITY_DISPLAY_LIMIT = 10
TOP_FILES_DISPLAY_LIMIT = 15
