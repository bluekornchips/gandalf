"""Database configuration, queries, and keys."""

# SQLite schema queries
SQL_CHECK_ITEMTABLE_EXISTS = (
    "SELECT name FROM sqlite_master WHERE type='table' AND name='ItemTable'"
)
SQL_COUNT_TABLE_ROWS = "SELECT COUNT(*) FROM {table_name}"  # nosec B608,
# table name is validated in code

# Cursor database queries
# These are all repetitive, we only need one constant.
SQL_CURSOR_GET_COMPOSER_DATA = "SELECT value FROM ItemTable WHERE key = ?"
SQL_CURSOR_GET_AI_CONVERSATIONS = "SELECT value FROM ItemTable WHERE key = ?"
SQL_CURSOR_GET_AI_PROMPTS = "SELECT value FROM ItemTable WHERE key = ?"
SQL_CURSOR_GET_AI_GENERATIONS = "SELECT value FROM ItemTable WHERE key = ?"

# Cursor database keys
CURSOR_KEY_COMPOSER_DATA = "composer.composerData"
CURSOR_KEY_AI_CONVERSATIONS = "aiConversations"
CURSOR_KEY_AI_PROMPTS = "aiService.prompts"
CURSOR_KEY_AI_GENERATIONS = "aiService.generations"

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

# Windsurf
CHAT_SESSION_STORE_KEY = "windsurf.chatSessionStore"
CONVERSATION_PATTERNS = {
    "role",
    "content",
    "message",
    "user",
    "assistant",
    "system",
}
STRONG_CONVERSATION_INDICATORS = {"assistant", "user", "role", "content"}
FALSE_POSITIVE_INDICATORS = {"settings", "config", "preferences", "metadata"}
CONTENT_KEYS = {"content", "text", "message", "data"}
MESSAGE_INDICATORS = {"messages", "chat", "conversation", "dialog"}
MIN_CONTENT_LENGTH = 5
MAX_ANALYSIS_LENGTH = 1000
FALSE_POSITIVE_RATIO_THRESHOLD = 0.3
MAX_LIST_ITEMS_TO_CHECK = 100
