"""Tool-specific configuration and patterns.

This module contains configuration for all agentic tools including database queries,
conversation patterns, file system context detection, and tool-specific settings.
"""

from pathlib import Path
from typing import Final

# ============================================================================
# FILE SYSTEM CONTEXT CONFIGURATION
# ============================================================================

FILE_SYSTEM_CONTEXT_INDICATORS: Final[list[str]] = [
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "requirements.txt",
    "setup.py",
    "Makefile",
    "README.md",
    ".git",
    ".gitignore",
]

MIN_CONTEXT_ROOT_DEPTH: Final[int] = 1
MAX_CONTEXT_ROOT_DEPTH: Final[int] = 10
USE_CURRENT_WORKING_DIRECTORY_AS_FALLBACK: Final[bool] = True

# ============================================================================
# DATABASE CONFIGURATION AND QUERIES
# ============================================================================

# SQLite schema queries
SQL_CHECK_ITEMTABLE_EXISTS = (
    "SELECT name FROM sqlite_master WHERE type='table' AND name='ItemTable'"
)
SQL_COUNT_TABLE_ROWS = "SELECT COUNT(*) FROM {table_name}"  # nosec B608,
# table name is validated in code

# Generic database queries
SQL_GET_VALUE_BY_KEY = "SELECT value FROM ItemTable WHERE key = ?"
SQL_GET_ALL_KEYS = "SELECT key FROM ItemTable"
SQL_COUNT_ITEMTABLE_ROWS = "SELECT COUNT(*) FROM ItemTable"
SQL_SELECT_ONE = "SELECT 1"

# Table information queries
SQL_GET_TABLE_NAMES = "SELECT name FROM sqlite_master WHERE type='table'"
SQL_CHECK_TABLE_EXISTS = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"

# Standard conversation table
CONVERSATION_TABLE_NAMES = [
    "conversations",
    "sessions",
    "chat",
]

# Database limitation note
DATABASE_STRUCTURE_LIMITATION_NOTE = (
    "Note: Results based on available database structure and may not include "
    "all conversation details."
)

# Unix timestamp in milliseconds
TIMESTAMP_MILLISECOND_THRESHOLD = 1000000000000

# Database operation timeout in seconds
DATABASE_OPERATION_TIMEOUT = 30

# ============================================================================
# CURSOR TOOL CONFIGURATION
# ============================================================================

# Cursor database files to search for
CURSOR_DATABASE_FILES = [
    "state.vscdb",
    "workspace.db",
    "storage.db",
    "cursor.db",
]

# Cursor database keys, supporting multiple versions
CURSOR_KEY_COMPOSER_DATA = [
    "composer.composerData",  # Modern AI conversations
    "interactive.sessions",  # Interactive sessions
]

CURSOR_CONVERSATION_KEYS = CURSOR_KEY_COMPOSER_DATA

# Cursor database paths
CURSOR_DATABASE_PATHS = [
    str(
        Path.home()
        / "Library"
        / "Application Support"
        / "Cursor"
        / "User"
        / "workspaceStorage"
    ),
    str(
        Path.home() / "AppData" / "Roaming" / "Cursor" / "User" / "workspaceStorage"
    ),  # Windows
    str(Path.home() / ".config" / "Cursor" / "User" / "workspaceStorage"),  # Linux
]

# ============================================================================
# CLAUDE CODE TOOL CONFIGURATION
# ============================================================================

# Claude Code database paths
CLAUDE_CODE_DATABASE_PATHS = [
    str(Path.home() / ".claude"),
    str(Path.home() / "Library" / "Application Support" / "Claude"),
    str(Path.home() / "AppData" / "Roaming" / "Claude"),  # Windows
    str(Path.home() / ".config" / "claude"),  # Linux
]

# Claude Code conversation patterns and keys
CLAUDE_CODE_CONVERSATION_KEYS = [
    "conversations",
    "chat_history",
    "sessions",
]

# ============================================================================
# WINDSURF TOOL CONFIGURATION
# ============================================================================

# Windsurf database paths
WINDSURF_DATABASE_PATHS = [
    str(
        Path.home()
        / "Library"
        / "Application Support"
        / "Windsurf"
        / "User"
        / "workspaceStorage"
    ),
    str(
        Path.home()
        / "Library"
        / "Application Support"
        / "Windsurf"
        / "User"
        / "globalStorage"
    ),
    str(
        Path.home() / "AppData" / "Roaming" / "Windsurf" / "User" / "workspaceStorage"
    ),  # Windows
    str(
        Path.home() / "AppData" / "Roaming" / "Windsurf" / "User" / "globalStorage"
    ),  # Windows
    str(Path.home() / ".config" / "Windsurf" / "User" / "workspaceStorage"),  # Linux
    str(Path.home() / ".config" / "Windsurf" / "User" / "globalStorage"),  # Linux
]

# Windsurf database keys, supporting multiple versions
WINDSURF_KEY_CHAT_SESSION_STORE = [
    "chat.ChatSessionStore.index",  # Current format
    "windsurf.chatSessionStore",  # Legacy format
]

# Windsurf-specific conversation patterns
WINDSURF_CONVERSATION_PATTERNS = {
    "chat",
    "conversation",
    "message",
    "session",
    "dialog",
    "ai",
    "assistant",
    "windsurf",
    "cascade",
    "codeium",
    "history",
    "input",
    "output",
    "response",
    "query",
    "prompt",
    "brain",
    "config",
}

WINDSURF_STRONG_CONVERSATION_INDICATORS = {
    "messages",
    "content",
    "text",
    "input",
    "output",
    "prompt",
    "response",
    "user",
    "assistant",
    "ai",
    "human",
    "question",
    "answer",
    "chat",
    "conversation",
    "brain",
    "config",
    "session",
    "entries",
}

WINDSURF_FALSE_POSITIVE_INDICATORS = {
    "workbench",
    "panel",
    "view",
    "container",
    "storage",
    "settings",
    "layout",
    "editor",
    "terminal",
    "debug",
    "extension",
    "plugin",
    "theme",
    "color",
    "font",
    "keybinding",
    "menu",
    "toolbar",
    "statusbar",
    "sidebar",
    "explorer",
    "search",
}

WINDSURF_CONTENT_KEYS = {
    "messages",
    "content",
    "text",
    "input",
    "output",
    "body",
    "message",
    "entries",
    "data",
}

WINDSURF_MESSAGE_INDICATORS = {
    "message",
    "content",
    "text",
    "user",
    "assistant",
    "conversation",
    "chat",
}

# ============================================================================
# TOOL DETECTION AND AVAILABILITY
# ============================================================================

# Tool detection priority order
TOOL_DETECTION_PRIORITY = [
    "cursor",
    "windsurf",
    "claude-code",
]

# Tool-specific file patterns for detection
TOOL_FILE_PATTERNS = {
    "cursor": [
        "**/Cursor/User/workspaceStorage/**/*.vscdb",
        "**/Cursor/User/workspaceStorage/**/state.vscdb",
    ],
    "windsurf": [
        "**/Windsurf/User/workspaceStorage/**/*.db",
        "**/Windsurf/User/globalStorage/**/*.db",
    ],
    "claude-code": [
        "**/.claude/**/*.db",
        "**/Claude/**/*.db",
    ],
}

# Tool capability matrix
TOOL_CAPABILITIES = {
    "cursor": {
        "conversation_extraction": True,
        "file_context": True,
        "code_analysis": True,
        "workspace_detection": True,
    },
    "windsurf": {
        "conversation_extraction": True,
        "file_context": True,
        "code_analysis": True,
        "workspace_detection": True,
    },
    "claude-code": {
        "conversation_extraction": True,
        "file_context": False,
        "code_analysis": True,
        "workspace_detection": False,
    },
}

# Tool-specific timeout configurations
TOOL_TIMEOUTS = {
    "cursor": 30,  # seconds
    "windsurf": 30,  # seconds
    "claude-code": 20,  # seconds
}

# Maximum conversations per tool
TOOL_MAX_CONVERSATIONS = {
    "cursor": 1000,
    "windsurf": 1000,
    "claude-code": 500,
}
