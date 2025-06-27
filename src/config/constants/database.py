"""
Database-related constants for Gandalf MCP server.
"""

# Standard IDE database locations
CURSOR_LOCATIONS = [
    "~/Library/Application Support/Cursor/workspaceStorage",
    "~/.cursor/workspaceStorage",
    "~/AppData/Roaming/Cursor/workspaceStorage",
]

CLAUDE_CODE_LOCATIONS = [
    "~/.claude",
    "~/.config/claude",
    "~/AppData/Roaming/Claude",
]

# Database query constants
CURSOR_COMPOSER_QUERY = (
    "SELECT value FROM ItemTable WHERE key LIKE '%composer%' LIMIT 1"
)
