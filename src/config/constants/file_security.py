"""
File security and filtering configuration for Gandalf MCP server.
Combines file access security, filtering patterns, and operational limits.
"""

# Input validation limits
SECURITY_MAX_STRING_LENGTH = 50000
SECURITY_MAX_ARRAY_LENGTH = 100
SECURITY_MAX_QUERY_LENGTH = 100
SECURITY_MAX_PATH_DEPTH = 20

# File operation limits
MAX_FILE_TYPES = 20
MAX_FILE_EXTENSION_LENGTH = 10
MAX_FILES_LIMIT = 10000
MAX_FILE_SIZE_BYTES = 1048576  # 1MB

# Display limits
HIGH_PRIORITY_DISPLAY_LIMIT = 20
MEDIUM_PRIORITY_DISPLAY_LIMIT = 15
LOW_PRIORITY_DISPLAY_LIMIT = 10
TOP_FILES_DISPLAY_LIMIT = 15

# Security: Blocked system paths
SECURITY_BLOCKED_PATHS = {
    "/etc",
    "/sys",
    "/proc",
    "/dev",
    "/root",
    "/boot",
    "/var/log",
    "/var/run",
    # "/tmp",  # Removed to allow temporary directory usage for testing
    "/usr/bin",
    "/usr/sbin",
}

# Security: Safe file extensions for operations
SECURITY_SAFE_EXTENSIONS = {
    # Primary languages
    ".py",
    ".pyi",
    ".js",
    ".ts",
    ".tsx",
    ".cjs",
    ".mjs",
    ".cts",
    ".mts",
    # Infrastructure & Configuration
    ".tf",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    # Web Technologies
    ".html",
    ".css",
    ".scss",
    ".less",
    # Documentation & Text
    ".md",
    ".mdx",
    ".txt",
    # Scripts
    ".sh",
    # Other formats
    ".xml",
    ".svg",
}

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

# Filtering: Combined unsafe file patterns (for both security and performance)
UNSAFE_FILE_PATTERNS = {
    # From FIND_EXCLUDE_PATTERNS
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
    # Additional security patterns
    "*.exe",
    "*.bin",
    "*.class",
    "*.jar",
}

# Filtering: Combined unsafe directory patterns
UNSAFE_DIRECTORY_PATTERNS = set(
    FIND_EXCLUDE_DIRS
    + [
        # Additional security-sensitive directories
        "secrets",
        "private",
        "confidential",
        ".env",
    ]
)
