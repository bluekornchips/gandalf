"""Security and access control configuration."""

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

FILENAME_CONTROL_CHARS_PATTERN = r"[\x00-\x1f\x7f-\x9f]"
FILENAME_INVALID_CHARS_PATTERN = r'[<>:"/\\|?*\x00-\x1f\x7f-\x9f]'

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

FILE_EXTENSION_MAX_LENGTH = 10
PROJECT_NAME_MAX_LENGTH = 100
FILE_EXTENSION_PATTERN = r"^\.[a-z0-9]+$"
QUERY_SANITIZE_PATTERN = r'[<>"\';\\]'

# Project name validation pattern
PROJECT_NAME_SANITIZE_PATTERN = r"[^a-zA-Z0-9._-]"

# Security threat detection patterns
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
