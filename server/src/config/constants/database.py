"""Database SQL queries, keys, and metadata."""

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

# Windsurf database keys, supporting multiple versions
WINDSURF_KEY_CHAT_SESSION_STORE = [
    "chat.ChatSessionStore.index",  # Current format
    "windsurf.chatSessionStore",  # Legacy format
]


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
