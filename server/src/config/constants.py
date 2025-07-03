"""
Unified configuration constants for Gandalf MCP server.
Contains only the constants that are actually used in the codebase.
"""

import os
from enum import Enum, IntEnum
from pathlib import Path

# =============================================================================
# CORE CONFIGURATION
# =============================================================================

# Project identity
MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "gandalf")
GANDALF_HOME = Path(os.getenv("GANDALF_HOME", str(Path.home() / f".{MCP_SERVER_NAME}")))
GANDALF_SERVER_VERSION = os.getenv("GANDALF_SERVER_VERSION", "2.0.1")

# MCP Protocol
MCP_PROTOCOL_VERSION = "2024-11-05"
JSONRPC_VERSION = "2.0"
SERVER_INFO = {"name": "gandalf-mcp", "version": GANDALF_SERVER_VERSION}
SERVER_CAPABILITIES = {"tools": {"listChanged": True}, "logging": {}}

# Environment
WORKSPACE_FOLDER_PATHS = os.getenv("WORKSPACE_FOLDER_PATHS")

# =============================================================================
# SYSTEM LIMITS & THRESHOLDS
# =============================================================================

# File Processing Limits
MAX_PROJECT_FILES = 10000
MAX_FILE_SIZE_BYTES = 1048576  # 1MB
RECENT_FILE_COUNT_LIMIT = 20
FIND_COMMAND_TIMEOUT = 30

# Database Scanner Timeouts
DATABASE_SCANNER_TIMEOUT = 30
DATABASE_OPERATION_TIMEOUT = 5

# Input Validation
MAX_STRING_LENGTH = 50000
MAX_ARRAY_LENGTH = 100
MAX_QUERY_LENGTH = 100
MAX_PATH_DEPTH = 20
MAX_FILE_TYPES = 20
MAX_FILE_EXTENSION_LENGTH = 10

# Scoring Thresholds
PRIORITY_NEUTRAL_SCORE = 0.5
CONTEXT_MIN_SCORE = 0.0

# =============================================================================
# CACHE CONFIGURATION
# =============================================================================

# Cache Directories
CACHE_ROOT_DIR = GANDALF_HOME / "cache"
CONVERSATION_CACHE_DIR = CACHE_ROOT_DIR / "conversations"
FILE_CACHE_DIR = CACHE_ROOT_DIR / "files"
GIT_CACHE_DIR = CACHE_ROOT_DIR / "git"

# Cache Files
CONVERSATION_CACHE_FILE = CONVERSATION_CACHE_DIR / "conversations.json"
CONVERSATION_CACHE_METADATA_FILE = CONVERSATION_CACHE_DIR / "metadata.json"

# Cache TTL
CONVERSATION_CACHE_TTL_HOURS = 4
CONVERSATION_CACHE_TTL_SECONDS = CONVERSATION_CACHE_TTL_HOURS * 3600
CONTEXT_CACHE_TTL_SECONDS = 300
CONTEXT_GIT_CACHE_TTL = 3600
MCP_CACHE_TTL = 3600
DATABASE_SCANNER_CACHE_TTL = 300  # 5 minutes

# Cache Limits
CONVERSATION_CACHE_MIN_SIZE = 5
CONVERSATION_CACHE_MAX_SIZE_MB = 10

# =============================================================================
# CONVERSATION PROCESSING
# =============================================================================

# Defaults
DEFAULT_FAST_MODE = False
CONVERSATION_DEFAULT_RECENT_DAYS = 7
CONVERSATION_DEFAULT_LIMIT = 20
CONVERSATION_DEFAULT_MIN_SCORE = 2.0
CONVERSATION_DEFAULT_LOOKBACK_DAYS = 30
CONVERSATION_MAX_LIMIT = 100
CONVERSATION_MAX_LOOKBACK_DAYS = 60

# Processing
CONVERSATION_BATCH_SIZE = 50
CONVERSATION_PROGRESS_LOG_INTERVAL = 25

# Context Intelligence
CONTEXT_KEYWORD_MAX_COUNT = 30
CONTEXT_MAX_FILES_TO_CHECK = 100
CONTEXT_FILE_SIZE_ACCEPTABLE_MAX = 512000  # 512KB
CONTEXT_TOP_FILES_COUNT = 20
CONTEXT_MIN_EXTENSIONS_BEFORE_DEEP_SCAN = 3
CONTEXT_SKIP_DIRECTORIES = {
    ".git",
    ".svn",
    ".hg",
    ".bzr",  # Version control
    "node_modules",
    "__pycache__",
    ".pytest_cache",  # Dependencies/cache
    ".venv",
    "venv",
    "env",  # Virtual environments
    "build",
    "dist",
    "target",  # Build outputs
    ".idea",
    ".vscode",
    ".vs",  # IDE files
    "logs",
    "tmp",
    "temp",  # Temporary files
}

# Conversation Analysis Constants
KEYWORD_MATCHES_TOP_LIMIT = 10
KEYWORD_CHECK_LIMIT = 50
KEYWORD_MATCHES_LIMIT = 15
CONTEXT_KEYWORDS_QUICK_LIMIT = 15
PATTERN_MATCHES_DEFAULT_LIMIT = 10
MATCHES_OUTPUT_LIMIT = 5

# Conversation Snippet Constants
CONVERSATION_SNIPPET_MAX_LENGTH = 200
CONVERSATION_SNIPPET_CONTEXT_CHARS = 50

# File Reference Patterns
FILE_REFERENCE_PATTERNS = [
    r"([a-zA-Z0-9_\-/]+\.[a-zA-Z0-9]{1,4})",  # Basic file pattern
    r"(\w+/\w+\.py)",  # Python module pattern
    r"(\w+\.js)",  # JavaScript file pattern
    r"(\w+\.ts)",  # TypeScript file pattern
]

# Database Structure Limitation Note
DATABASE_STRUCTURE_LIMITATION_NOTE = (
    "Note: Results based on available database structure and may not include "
    "all conversation details."
)

# =============================================================================
# FILE FILTERING
# =============================================================================

# Directory Exclusions
EXCLUDE_DIRECTORIES = {
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
    "vendor",
    ".env",
    "env",
    ".nyc_output",
    "htmlcov",
    "secrets",
    "confidential",
}

# Legacy aliases for backwards compatibility
FIND_EXCLUDE_DIRS = list(EXCLUDE_DIRECTORIES)

# File Pattern Exclusions
EXCLUDE_FILE_PATTERNS = {
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
    "*.exe",
    "*.bin",
    ".class",
    ".jar",
}

# Legacy aliases for backwards compatibility
FIND_EXCLUDE_PATTERNS = list(EXCLUDE_FILE_PATTERNS)

# Security: Blocked Extensions
BLOCKED_EXTENSIONS = {
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
    ".bin",
    ".dll",
    ".so",
    ".dylib",
    ".class",
    ".jar",
    ".pyc",
    ".pyo",
    ".pyd",
    ".zip",
    ".rar",
    ".7z",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".db",
    ".sqlite",
    ".sqlite3",
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
    ".tmp",
    ".temp",
    ".log",
    ".cache",
    ".swp",
    ".swo",
    ".bak",
    ".old",
}

# Security: Blocked Paths
BLOCKED_PATHS = {
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
    "/snap",
    "/run",
    "/lib",
    "/lib64",
    "/private/etc",
    "/private/var/log",
    "/private/var/run",
    "/System",
    "/Library/System",
    "/Applications/Utilities",
    "/mnt/c/Windows",
    "/mnt/c/Program Files",
    "/mnt/c/Program Files (x86)",
    "/mnt/c/Users",
    "/mnt/c/System Volume Information",
}

# =============================================================================
# AGENTIC TOOL CONFIGURATION
# =============================================================================

# Supported Tools
SUPPORTED_AGENTIC_TOOLS = ["cursor", "claude-code", "windsurf"]
AGENTIC_TOOL_CURSOR = "cursor"
AGENTIC_TOOL_CLAUDE_CODE = "claude-code"
AGENTIC_TOOL_WINDSURF = "windsurf"

# Registry
REGISTRY_FILENAME = "registry.json"
GANDALF_HOME_ENV = "GANDALF_HOME"
DEFAULT_GANDALF_HOME = "~/.gandalf"

# Cursor Workspace Storage Path
CURSOR_WORKSPACE_STORAGE = (
    Path.home() / "Library" / "Application Support" / "Cursor" / "workspaceStorage"
)

# Claude Code Home
CLAUDE_HOME = Path.home() / ".claude"

# Windsurf Workspace Storage Path
WINDSURF_WORKSPACE_STORAGE = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Windsurf"
    / "User"
    / "workspaceStorage"
)

# Windsurf Global Storage Path
WINDSURF_GLOBAL_STORAGE = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Windsurf"
    / "User"
    / "globalStorage"
)

# Database Locations
CURSOR_LOCATIONS = [
    "~/Library/Application Support/Cursor/workspaceStorage",
    "~/.cursor/workspaceStorage",
    "~/AppData/Roaming/Cursor/workspaceStorage",
]
CLAUDE_CODE_LOCATIONS = ["~/.claude", "~/.config/claude", "~/AppData/Roaming/Claude"]
WINDSURF_LOCATIONS = [
    "~/Library/Application Support/Windsurf/User/workspaceStorage",
    "~/Library/Application Support/Windsurf/User/globalStorage",
    "~/.windsurf/workspaceStorage",
    "~/.windsurf/globalStorage",
    "~/AppData/Roaming/Windsurf/User/workspaceStorage",
    "~/AppData/Roaming/Windsurf/User/globalStorage",
]

# Database Scanner Paths, as Path objects
CURSOR_SCANNER_PATHS = [
    Path.home()
    / "Library"
    / "Application Support"
    / "Cursor"
    / "User"
    / "workspaceStorage",
    Path.home() / ".cursor" / "workspaceStorage",
]
CLAUDE_SCANNER_PATHS = [
    Path.home() / ".claude",
    Path.home() / ".config" / "claude",
]
WINDSURF_SCANNER_PATHS = [
    Path.home()
    / "Library"
    / "Application Support"
    / "Windsurf"
    / "User"
    / "workspaceStorage",
    Path.home()
    / "Library"
    / "Application Support"
    / "Windsurf"
    / "User"
    / "globalStorage",
    Path.home() / ".windsurf" / "workspaceStorage",
    Path.home() / ".windsurf" / "globalStorage",
]

# Database Patterns
CURSOR_DB_PATTERNS = ["*.vscdb", "*.db"]
CLAUDE_CONVERSATION_PATTERNS = [
    "conversations/*.json",
    "sessions/*.json",
    "history/*.json",
    "*.json",
]
WINDSURF_DB_PATTERNS = ["*.vscdb", "*.db"]

# =============================================================================
# TECHNOLOGY MAPPING
# =============================================================================

TECHNOLOGY_EXTENSION_MAPPING = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "tsx": "react",
    "cjs": "javascript",
    "mjs": "javascript",
    "cts": "typescript",
    "mts": "typescript",
    "pyi": "python",
    "tf": "terraform",
    "yaml": "yaml",
    "yml": "yaml",
    "json": "json",
    "toml": "toml",
    "ini": "config",
    "cfg": "config",
    "conf": "config",
    "html": "html",
    "css": "css",
    "scss": "sass",
    "less": "less",
    "md": "markdown",
    "mdx": "markdown",
    "sh": "bash",
    "txt": "text",
    "xml": "xml",
    "svg": "svg",
}

TECHNOLOGY_KEYWORD_MAPPING = {
    "python": [
        "python",
        "py",
        "pip",
        "conda",
        "virtualenv",
        "pytest",
        "django",
        "flask",
    ],
    "javascript": [
        "javascript",
        "js",
        "node",
        "npm",
        "yarn",
        "react",
        "vue",
        "angular",
        "express",
    ],
    "typescript": ["typescript", "ts", "tsc", "types", "interface", "generic"],
    "terraform": ["terraform", "tf", "hcl", "aws", "azure", "gcp", "infrastructure"],
    "docker": ["docker", "dockerfile", "container", "image", "compose"],
    "kubernetes": [
        "kubernetes",
        "k8s",
        "kubectl",
        "helm",
        "deployment",
        "service",
        "kube",
    ],
}

# =============================================================================
# CONVERSATION PATTERNS
# =============================================================================

# Conversation Types
CONVERSATION_TYPES = [
    "architecture",
    "debugging",
    "problem_solving",
    "technical",
    "code_discussion",
    "general",
]

# =============================================================================
# ENUMS
# =============================================================================


class LogLevel(Enum):
    """Log level enumeration."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ErrorCodes(IntEnum):
    """JSON-RPC error codes."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


# =============================================================================
# CONTEXT INTELLIGENCE
# =============================================================================

# Context Processing Thresholds
GIT_ACTIVITY_RECENT_DAYS = 30

# Token Optimization
TOKEN_OPTIMIZATION_MAX_RESPONSE_SIZE = 16000
TOKEN_OPTIMIZATION_CONTENT_TRUNCATION_LIMIT = 1000
TOKEN_OPTIMIZATION_SUMMARY_MODE_THRESHOLD = 10
TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS = 15
TOKEN_OPTIMIZATION_MAX_TOOL_RESULT_FIELDS = 8

# =============================================================================
# DATABASE PATHS & PATTERNS
# =============================================================================

# Cursor Workspace Storage Path
CURSOR_WORKSPACE_STORAGE_PATH = "Application Support/Cursor/User/workspaceStorage"

# =============================================================================
# SECURITY & VALIDATION
# =============================================================================

# Common Blocked Paths (additional security paths)
COMMON_BLOCKED_PATHS = {
    "/etc",
    "/etc/hosts",
    "/etc/ssh",
    "/sys",
    "/proc",
    "/var/run/docker.sock",
    "C:\\Windows\\System32",
    "C:\\Program Files",
    "C:\\Users\\Administrator",
}

# Filename Control Characters Pattern
FILENAME_CONTROL_CHARS_PATTERN = r"[\x00-\x1f\x7f-\x9f]"
FILENAME_INVALID_CHARS_PATTERN = r'[<>:"/\\|?*\x00-\x1f\x7f-\x9f]'
FILENAME_MAX_LENGTH = 255

# Platform-Specific Blocked Paths
LINUX_SPECIFIC_BLOCKED_PATHS = {
    "/etc/passwd",
    "/etc/shadow",
    "/etc/sudoers",
    "/etc/ssh/sshd_config",
    "/root/.ssh",
    "/var/log/auth.log",
    "/var/log/secure",
    "/dev/random",
    "/dev/urandom",
    "/tmp/.X11-unix",
    "/snap",
}

MACOS_SPECIFIC_BLOCKED_PATHS = {
    "/System",
    "/Library/System",
    "/private/etc",
    "/private/var/log",
    "/Applications/Keychain Access.app",
    "/System/Library/Keychains",
    "/usr/bin",
    "/usr/sbin",
    "/private/var/run",
}

WSL_SPECIFIC_BLOCKED_PATHS = {
    "/mnt/c/Windows",
    "/mnt/c/Program Files",
    "/mnt/c/Program Files (x86)",
    "/mnt/c/Users/Administrator",
    "/mnt/c/System Volume Information",
    "/mnt/c/ProgramData",
    "/mnt/c/Windows/System32",
}

# =============================================================================
# LOOKBACK & SCORING DEFAULTS
# =============================================================================

# Default Lookback Days (used in various contexts)
DEFAULT_LOOKBACK_DAYS = 30

# =============================================================================
# FINAL CONSTANTS
# =============================================================================

# Conversation Text Extraction Limit
CONVERSATION_TEXT_EXTRACTION_LIMIT = 10000

# Timestamp Validation
TIMESTAMP_MILLISECOND_THRESHOLD = 1000000000000  # Unix timestamp in milliseconds
