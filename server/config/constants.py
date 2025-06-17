from pathlib import Path
import os

########################################################
# Project Constants (rarely change)
########################################################

# Project name and paths
MCP_SERVER_NAME = os.getenv('MCP_SERVER_NAME', 'gandalf')
GANDALF_HOME = Path(os.getenv('HOME', str(Path.home()))) / f".{MCP_SERVER_NAME}"
CONVERSATIONS_BASE_DIR = GANDALF_HOME / "conversations"
CACHE_FILE_NAME = GANDALF_HOME / "file_cache.json"

# MCP Protocol constants
MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_VERSION = "0.3.0"
SERVER_INFO = {"name": "gandalf-mcp", "version": SERVER_VERSION}
SERVER_CAPABILITIES = {"tools": {"listChanged": True}, "logging": {}}

# File system constants
MAX_FILE_SIZE_BYTES = 1048576  # 1MB

# Directory exclusion patterns for find command
FIND_EXCLUDE_DIRS = [
    "__pycache__", ".git", "node_modules", ".venv", ".cache",
    ".pytest_cache", ".mypy_cache", ".tox", ".coverage",
    "dist", "build", "target", ".gradle", ".idea", ".vscode",
    "tmp", "temp", "logs", "log",
]

# File exclusion patterns
FIND_EXCLUDE_PATTERNS = [
    "*.pyc", "*.pyo", "*.pyd", "*.so", "*.dylib", "*.dll",
    "*.log", "*.tmp", "*.temp", "*.swp", "*.swo", "*~",
    ".DS_Store", "Thumbs.db", "desktop.ini", "*.lock",
]

########################################################
# System Configuration (environment-driven)
########################################################

# Server settings
MCP_DEBUG = os.getenv('MCP_DEBUG', 'true').lower() in ('true', '1', 'yes', 'on')

# Dynamic project detection settings
# Note: GANDALF_DISABLE_DYNAMIC_DETECTION is checked at runtime in _tools_call()
# rather than being evaluated at import time, to support test environments
# since the environment variable is set after module import
DISABLE_DYNAMIC_DETECTION = os.getenv('GANDALF_DISABLE_DYNAMIC_DETECTION', 'false').lower() in ('true', '1', 'yes', 'on')

# File processing limits
RECENT_FILE_COUNT_LIMIT = int(os.getenv('RECENT_FILE_COUNT_LIMIT', '20'))
MAX_PROJECT_FILES = int(os.getenv('MAX_PROJECT_FILES', '1000'))
MCP_CACHE_TTL = int(os.getenv('MCP_CACHE_TTL', '300'))
MCP_CONVERSATION_LIMIT = int(os.getenv('MCP_CONVERSATION_LIMIT', '20'))
MAX_CONVERSATION_HISTORY = int(os.getenv('MAX_CONVERSATION_HISTORY', '100'))

# Git operation defaults
GIT_INCLUDE_UNTRACKED = os.getenv('GIT_INCLUDE_UNTRACKED', 'true').lower() in ('true', '1', 'yes', 'on')
GIT_VERBOSE = os.getenv('GIT_VERBOSE', 'false').lower() in ('true', '1', 'yes', 'on')
GIT_INCLUDE_MERGED = os.getenv('GIT_INCLUDE_MERGED', 'true').lower() in ('true', '1', 'yes', 'on')
GIT_COMMIT_LIMIT = int(os.getenv('GIT_COMMIT_LIMIT', '50'))
GIT_TIMEOUT = int(os.getenv('GIT_TIMEOUT', '10'))
GIT_BRANCH_TIMEOUT = int(os.getenv('GIT_BRANCH_TIMEOUT', '8'))

# Conversation storage settings
STORE_CONVERSATIONS = os.getenv('STORE_CONVERSATIONS', 'true').lower() in ('true', '1', 'yes', 'on')
# Disable conversation storage during tests
DISABLE_TEST_CONVERSATIONS = os.getenv('GANDALF_TEST_MODE', 'false').lower() in ('true', '1', 'yes', 'on')
CONVERSATION_CLEANUP_DAYS = int(os.getenv('CONVERSATION_CLEANUP_DAYS', '30'))
CONVERSATION_MAX_SIZE_MB = int(os.getenv('CONVERSATION_MAX_SIZE_MB', '10'))
SESSION_CONTEXT_MESSAGES = int(os.getenv('SESSION_CONTEXT_MESSAGES', '15'))
AUTO_STORE_THRESHOLD = int(os.getenv('AUTO_STORE_THRESHOLD', '1'))

# Conversation file names
CONVERSATION_METADATA_FILE = "conversation.json"
CONVERSATION_MESSAGES_FILE = "messages.json"
