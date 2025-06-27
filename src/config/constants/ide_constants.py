"""
IDE-specific constants for adapter implementations.
"""

from pathlib import Path

# Cursor IDE Constants
CURSOR_APP_PATHS = [
    "/Applications/Cursor.app",
    "/usr/local/bin/cursor",
    "/opt/cursor",
]

CURSOR_DATA_DIR = Path.home() / "Library" / "Application Support" / "Cursor"
CURSOR_WORKSPACE_STORAGE = CURSOR_DATA_DIR / "workspaceStorage"
CURSOR_ALT_WORKSPACE_STORAGE = Path.home() / ".cursor" / "workspaceStorage"

CURSOR_WORKSPACE_LOCATIONS = [
    CURSOR_WORKSPACE_STORAGE,
    CURSOR_ALT_WORKSPACE_STORAGE,
]

# Claude Code Constants
CLAUDE_CONFIG_PATHS = [
    Path.home() / ".claude",
    Path.home() / ".config" / "claude",
]

CLAUDE_HOME = Path.home() / ".claude"
CLAUDE_CONFIG_DIR = Path.home() / ".config" / "claude"

CLAUDE_INDICATORS = [".claude", "CLAUDE.md", ".claude.toml"]

# Common Project Detection
PROJECT_ROOT_INDICATOR = (
    ".git"  # Simplified to just use git, dependency for now
)

# Database Queries
# Simple query to get table names and confirm it's a sqlite database
SQLITE_TABLE_QUERY = "SELECT name FROM sqlite_master WHERE type='table'"

# Environment Variables
CURSOR_ENV_VARS = [
    "CURSOR_WORKSPACE",
    "CURSOR_TRACE_ID",
    "VSCODE_PID",
    "VSCODE_CWD",
    "VSCODE_INJECTION",
    "VSCODE_GIT_IPC_HANDLE",
    "VSCODE_GIT_ASKPASS_NODE",
    "VSCODE_GIT_ASKPASS_MAIN",
]

CLAUDE_ENV_VARS = [
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDECODE",
    "CLAUDE_WORKSPACE",
    "CLAUDE_PROJECT_ROOT",
    "CLAUDE_HOME",
    "WORKSPACE_FOLDER_PATHS",
]

# Cursor Detection Constants
CURSOR_ENV_INDICATORS = [
    "CURSOR_TRACE_ID",
    "CURSOR_WORKSPACE",
]

CURSOR_VSCODE_ENV_INDICATORS = [
    ("VSCODE_INJECTION", "1"),
    ("TERM_PROGRAM", "vscode"),
]

CURSOR_VSCODE_PATH_VARS = [
    "VSCODE_GIT_ASKPASS_NODE",
    "VSCODE_GIT_ASKPASS_MAIN",
]

# Claude Code Detection Constants
CLAUDE_CONTEXT_ENV_VARS = [
    "CLAUDE_WORKSPACE",
    "CLAUDE_PROJECT_ROOT",
    "CLAUDE_HOME",
    "WORKSPACE_FOLDER_PATHS",
]
