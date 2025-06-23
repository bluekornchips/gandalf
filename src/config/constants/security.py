"""
Security configuration constants for Gandalf MCP server.
Contains validation limits, blocked paths, and safe file extensions.
Based on analysis of commonly used file types in modern development projects.
"""

# Input validation limits
SECURITY_MAX_STRING_LENGTH = 50000
SECURITY_MAX_ARRAY_LENGTH = 100
SECURITY_MAX_QUERY_LENGTH = 100
SECURITY_MAX_PATH_DEPTH = 20

# Blocked system paths for security
SECURITY_BLOCKED_PATHS = {
    "/etc",
    "/sys",
    "/proc",
    "/dev",
    "/root",
    "/boot",
    "/var/log",
    "/var/run",
    "/tmp",
    "/usr/bin",
    "/usr/sbin",
}

# Safe file extensions for file operations
# Based on common file types I can pull out of my head
SECURITY_SAFE_EXTENSIONS = {
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
    # Web
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
