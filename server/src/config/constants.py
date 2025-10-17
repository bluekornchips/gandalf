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
MAX_CONVERSATIONS = 8
MAX_KEYWORDS = 8
MAX_RESULTS_LIMIT = 1000  # Hard cap on total results returned
INCLUDE_PROMPTS_DEFAULT = True
# Exclude the AI generations by default unless GANDALF_INCLUDE_GENERATIONS env var is set.
# AI generations are verbose and not as useful as user prompts.
INCLUDE_GENERATIONS_DEFAULT = (
    os.getenv("GANDALF_INCLUDE_GENERATIONS", "false").lower() == "true"
)

# Optimization constants for concise conversation recall
MAX_SUMMARY_LENGTH = 200  # Truncate summaries to 200 chars for token efficiency
MAX_SUMMARY_ENTRIES = 2

IGNORED_KEYWORDS = [
    # Articles
    "the",
    "a",
    "an",
    # Prepositions
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "up",
    "about",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "between",
    "among",
    "under",
    "over",
    "across",
    "around",
    "near",
    "far",
    "inside",
    "outside",
    "within",
    "without",
    "upon",
    "toward",
    "towards",
    # Conjunctions
    "and",
    "or",
    "but",
    "so",
    "yet",
    "nor",
    "for",
    "because",
    "since",
    "although",
    "though",
    "unless",
    "if",
    "when",
    "where",
    "while",
    "as",
    "than",
    "that",
    "whether",
    # Pronouns
    "i",
    "you",
    "he",
    "she",
    "it",
    "we",
    "they",
    "me",
    "him",
    "her",
    "us",
    "them",
    "my",
    "your",
    "his",
    "her",
    "its",
    "our",
    "their",
    "mine",
    "yours",
    "hers",
    "ours",
    "theirs",
    "myself",
    "yourself",
    "himself",
    "herself",
    "itself",
    "ourselves",
    "yourselves",
    "themselves",
    # Common verbs
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "must",
    "can",
    "shall",
    "ought",
    # Demonstratives
    "this",
    "that",
    "these",
    "those",
    # Interrogatives
    "what",
    "which",
    "who",
    "whom",
    "whose",
    "where",
    "when",
    "why",
    "how",
    # Quantifiers
    "all",
    "some",
    "any",
    "many",
    "much",
    "few",
    "little",
    "several",
    "most",
    "each",
    "every",
    "both",
    "either",
    "neither",
    "none",
    "no",
    "one",
    "two",
    "three",
    "first",
    "second",
    "last",
]
