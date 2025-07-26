"""Security and access control configuration.

This module contains all security-related settings including blocked paths,
validation patterns, threat detection patterns, and access control rules.
"""

from typing import Final

# ============================================================================
# BLOCKED PATHS AND ACCESS CONTROL
# ============================================================================

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
    "/tmp/.X11-unix",  # nosec B108 - intentional blocked path for security
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

# ============================================================================
# VALIDATION PATTERNS AND RULES
# ============================================================================

# File and project name validation
FILE_EXTENSION_MAX_LENGTH = 10
PROJECT_NAME_MAX_LENGTH = 100
FILE_EXTENSION_PATTERN = r"^\.[a-z0-9]+$"

# Character validation patterns
FILENAME_CONTROL_CHARS_PATTERN = r"[\x00-\x1f\x7f-\x9f]"
FILENAME_INVALID_CHARS_PATTERN = r'[<>:"/\\|?*\x00-\x1f\x7f-\x9f]'

# Input sanitization patterns
QUERY_SANITIZE_PATTERN = r'[<>"\';\\]'
PROJECT_NAME_SANITIZE_PATTERN = r"[^a-zA-Z0-9._-]"

# ============================================================================
# SECURITY THREAT DETECTION
# ============================================================================

# General security threat detection patterns
DANGEROUS_PATTERNS = [
    r"\.\./",  # Directory traversal
    r"<script",  # script injection
    r"javascript:",  # js injection
    r"data:",  # data urls
    r"file://",  # file urls
    r"\x00",  # null bytes
    r"[;&|`$()]",  # shell metacharacters
]

# Conversation-specific threat patterns
CONVERSATION_DANGEROUS_PATTERNS = [
    r"<script[^>]*>.*</script>",  # complete script tags
    r"javascript:[^\"'\s]+",  # js urls
    r"data:text/html",  # html data urls
    r"vbscript:",  # vbscript urls
    r"\${.*}",  # Template injection patterns
]

# ============================================================================
# SECURITY CONFIGURATION CONSTANTS
# ============================================================================

# Access control limits
MAX_CONCURRENT_REQUESTS: Final[int] = 10
REQUEST_TIMEOUT_SECONDS: Final[int] = 30
MAX_REQUEST_SIZE_BYTES: Final[int] = 10_485_760  # 10MB

# Path traversal protection
MAX_PATH_TRAVERSAL_DEPTH: Final[int] = 3
ALLOWED_FILE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".vue",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".cfg",
    ".ini",
    ".conf",
}

# Content validation limits
MAX_CONTENT_SCAN_SIZE: Final[int] = 1_048_576  # 1MB
MAX_REGEX_MATCHES_PER_SCAN: Final[int] = 1000

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE: Final[int] = 100
RATE_LIMIT_BURST_SIZE: Final[int] = 10

# Security headers and policies
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}

# Content Security Policy
CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)
