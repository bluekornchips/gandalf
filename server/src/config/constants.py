import os

MCP_PROTOCOL_VERSION = "2025-06-18"
JSONRPC_VERSION = "2.0"

# Server info and capabilities.
SERVER_CAPABILITIES = {"tools": {"listChanged": True}, "logging": {}}
SERVER_NAME = "Gandalf"
SERVER_DESCRIPTION = """
Gandalf is an MCP Server for recalling information from the user's knowledge base based upon conversation history.
"""

# Environment variables
GANDALF_HOME = os.getenv("GANDALF_HOME", "")
GANDALF_REGISTRY_FILE = os.getenv(
    "GANDALF_REGISTRY_FILE", os.path.expanduser("~/.gandalf/registry.json")
)

# Supported database files for conversation recall.
# Matches the database files in the registry.json file.
SUPPORTED_DB_FILES = [
    "state.vscdb",
    "workspace.db",
    "storage.db",
    "cursor.db",
    "claude.db",
]

# Database query constants for recall conversations tool
RECALL_CONVERSATIONS_QUERIES = {
    "PROMPTS_QUERY": "SELECT value FROM ItemTable WHERE key = ?",
    "GENERATIONS_QUERY": "SELECT value FROM ItemTable WHERE key = ?",
    "HISTORY_QUERY": "SELECT value FROM ItemTable WHERE key = ?",
    "PROMPTS_KEY": "aiService.prompts",
    "GENERATIONS_KEY": "aiService.generations",
    "HISTORY_KEY": "history.entries",
}

# Recall conversations tool specific constants
MAX_PHRASES = 8  # Maximum number of search phrases allowed
DEFAULT_RESULTS_LIMIT = 64  # Default number of results returned
MAX_RESULTS_LIMIT = 1024  # Hard cap on total results returned
INCLUDE_PROMPTS_DEFAULT = True

# Optimization constants for concise conversation recall
MAX_SUMMARY_LENGTH = 4096  # Truncate summaries for token efficiency
MAX_SUMMARY_ENTRIES = 16  # Per-database limit when no phrases provided

# Exclude the AI generations by default unless GANDALF_INCLUDE_GENERATIONS env var is set.
# AI generations are verbose and not as useful as user prompts.
INCLUDE_GENERATIONS_DEFAULT = (
    os.getenv("GANDALF_INCLUDE_GENERATIONS", "false").lower() == "true"
)

# Recency scoring configuration
RECENCY_DECAY_RATE = float(os.getenv("GANDALF_RECENCY_DECAY_RATE", "0.1"))

# History entry filtering default
DEFAULT_INCLUDE_EDITOR_HISTORY = (
    os.getenv("GANDALF_INCLUDE_EDITOR_HISTORY", "false").lower() == "true"
)

# Spell system constants
SPELLS_DIRECTORY = (
    "spells"  # Directory name for spell YAML files (relative to project root)
)
DEFAULT_ALLOWED_PATHS: list[str] = []  # Empty by default, must be explicitly configured
DEFAULT_TIMEOUT_SECONDS = 30  # Default timeout for spell execution
MAX_TIMEOUT_SECONDS = 300  # Maximum allowed timeout
