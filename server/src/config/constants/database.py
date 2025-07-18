"""Database SQL queries, keys, and metadata."""

# SQLite schema queries
SQL_CHECK_ITEMTABLE_EXISTS = (
    "SELECT name FROM sqlite_master WHERE type='table' AND name='ItemTable'"
)
SQL_COUNT_TABLE_ROWS = "SELECT COUNT(*) FROM {table_name}"  # nosec B608,
# table name is validated in code

# Cursor database queries
SQL_CURSOR_GET_COMPOSER_DATA = "SELECT value FROM ItemTable WHERE key = ?"
SQL_CURSOR_GET_AI_CONVERSATIONS = "SELECT value FROM ItemTable WHERE key = ?"
SQL_CURSOR_GET_AI_PROMPTS = "SELECT value FROM ItemTable WHERE key = ?"
SQL_CURSOR_GET_AI_GENERATIONS = "SELECT value FROM ItemTable WHERE key = ?"

# Cursor database files to search for
CURSOR_DATABASE_FILES = [
    "state.vscdb",
    "workspace.db",
    "storage.db",
    "cursor.db",
]

# Cursor database keys
CURSOR_KEY_COMPOSER_DATA = "composer.composerData"
CURSOR_KEY_AI_CONVERSATIONS = "aiConversations"
CURSOR_KEY_AI_PROMPTS = "aiService.prompts"
CURSOR_KEY_AI_GENERATIONS = "aiService.generations"

# Windsurf database keys
WINDSURF_KEY_CHAT_SESSION_STORE = "windsurf.chatSessionStore"

# Database metadata
CONVERSATION_TABLE_NAMES = [
    "conversations",
    "messages",
    "chat_sessions",
]

# Database limitation note
DATABASE_STRUCTURE_LIMITATION_NOTE = (
    "Note: Results based on available database structure and may not include "
    "all conversation details."
)

# Unix timestamp in milliseconds
TIMESTAMP_MILLISECOND_THRESHOLD = 1000000000000
