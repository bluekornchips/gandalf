"""
Configuration data structures for Gandalf MCP server.
Contains mappings, exclusion sets, and other structured configuration data.
"""

# File filtering configuration

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

# Security configuration

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

# Technology mapping configuration

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
    "terraform": [
        "terraform",
        "tf",
        "hcl",
        "aws",
        "azure",
        "gcp",
        "infrastructure",
    ],
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

# Agentic tool configuration

# Database Patterns
CURSOR_DB_PATTERNS = ["*.vscdb", "*.db"]
CLAUDE_CONVERSATION_PATTERNS = [
    "conversations/*.json",
    "sessions/*.json",
    "history/*.json",
    "*.json",
]
WINDSURF_DB_PATTERNS = ["*.vscdb", "*.db"]

# Conversation types

CONVERSATION_TYPES = [
    "architecture",
    "debugging",
    "problem_solving",
    "technical",
    "code_discussion",
    "general",
]

# Context skip directories

CONTEXT_SKIP_DIRECTORIES = {
    ".git",
    ".svn",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "env",
    "build",
    "dist",
    "target",
    ".idea",
    ".vscode",
    ".vs",
    "logs",
    "tmp",
    "temp",
}

# File reference patterns

FILE_REFERENCE_PATTERNS = [
    r"([a-zA-Z0-9_\-/]+\.[a-zA-Z0-9]{1,4})",  # Basic file pattern
    r"(\w+/\w+\.py)",  # Python module pattern
    r"(\w+\.js)",  # JavaScript file pattern
    r"(\w+\.ts)",  # TypeScript file pattern
]
