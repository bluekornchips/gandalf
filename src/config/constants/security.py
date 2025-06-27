"""
File security and filtering configuration for Gandalf MCP server.
Combines file access security, filtering patterns, and operational limits.
"""

# Input validation limits
MAX_STRING_LENGTH = 50000
MAX_ARRAY_LENGTH = 100
MAX_QUERY_LENGTH = 100
MAX_PATH_DEPTH = 20

# File operation limits
MAX_FILE_TYPES = 20
MAX_FILE_EXTENSION_LENGTH = 10
MAX_FILES_LIMIT = 10000
MAX_FILE_SIZE_BYTES = 1048576  # 1MB

# Filename sanitization constants
FILENAME_INVALID_CHARS_PATTERN = r'[<>:"/\\|?*]'
FILENAME_CONTROL_CHARS_PATTERN = r"[\x00-\x1f\x7f-\x9f]"
FILENAME_MAX_LENGTH = 100

# Timestamp conversion constants
TIMESTAMP_MILLISECOND_THRESHOLD = (
    1e10  # Threshold to detect millisecond vs second timestamps
)

# Platform identifiers
PLATFORM_LINUX = "linux"
PLATFORM_MACOS = "macos"
PLATFORM_WSL = "wsl"

# Display limits
HIGH_PRIORITY_DISPLAY_LIMIT = 20
MEDIUM_PRIORITY_DISPLAY_LIMIT = 15
LOW_PRIORITY_DISPLAY_LIMIT = 10
TOP_FILES_DISPLAY_LIMIT = 15

# Security: Blocked system paths

# Common paths blocked across all platforms
COMMON_BLOCKED_PATHS = {
    "/etc",
    "/sys",
    "/proc",
    "/dev",
    "/root",
    "/boot",
    "/var/log",
    "/var/run",
    "/usr/bin",
    "/usr/sbin",
}

# Platform-specific blocked paths
LINUX_SPECIFIC_BLOCKED_PATHS = {
    "/snap",
    "/run",
    "/lib",
    "/lib64",
}

MACOS_SPECIFIC_BLOCKED_PATHS = {
    "/private/etc",
    "/private/var/log",
    "/private/var/run",
    "/System",
    "/Library/System",
    "/Applications/Utilities",
}

WSL_SPECIFIC_BLOCKED_PATHS = {
    "/mnt/c/Windows",
    "/mnt/c/Program Files",
    "/mnt/c/Program Files (x86)",
    "/mnt/c/Users",
    "/mnt/c/System Volume Information",
}

# Combined blocked paths for runtime use
BLOCKED_PATHS = (
    COMMON_BLOCKED_PATHS
    | LINUX_SPECIFIC_BLOCKED_PATHS
    | MACOS_SPECIFIC_BLOCKED_PATHS
    | WSL_SPECIFIC_BLOCKED_PATHS
)

# Note: /tmp removed from all sets to allow temporary directory usage for testing

# Security: Blocked file extensions (dangerous/unwanted files)
BLOCKED_EXTENSIONS = {
    # Executable files
    ".exe",
    ".com",
    ".bat",
    ".cmd",
    ".scr",
    ".pif",
    ".msi",
    ".deb",
    ".rpm",
    ".dmg",
    ".pkg",
    ".app",
    # Binary/Compiled files
    ".bin",
    ".dll",
    ".so",
    ".dylib",
    ".class",
    ".jar",
    ".pyc",
    ".pyo",
    ".pyd",
    # Archive files (can contain malicious content)
    ".zip",
    ".rar",
    ".7z",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    # Database files
    ".db",
    ".sqlite",
    ".sqlite3",
    # Large media files
    ".mp4",
    ".avi",
    ".mkv",
    ".mov",
    ".wmv",
    ".mp3",
    ".wav",
    ".flac",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tiff",
    ".pdf",
    # System/temporary files
    ".tmp",
    ".temp",
    ".log",
    ".cache",
    ".swp",
    ".swo",
    ".bak",
    ".old",
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
