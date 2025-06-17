from typing import Any, Dict, List
from config.constants import MAX_PROJECT_FILES, MCP_CONVERSATION_LIMIT

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "list_project_files",
        "description": "List files in the git repository with intelligent filtering and relevance scoring for better context prioritization",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_types": {
                    "type": "array",
                    "items": {"type": "string", "pattern": "^\\.[a-zA-Z0-9]+$"},
                    "description": "Filter by specific file extensions (e.g., ['.py', '.js'])",
                    "default": []
                },
                "include_hidden": {
                    "type": "boolean",
                    "description": "Include hidden files and directories",
                    "default": False
                },
                "max_files": {
                    "type": "integer",
                    "description": "Maximum number of files to return",
                    "default": MAX_PROJECT_FILES,
                    "minimum": 1,
                    "maximum": 10000
                },
                "use_relevance_scoring": {
                    "type": "boolean",
                    "description": "Enable intelligent relevance scoring and prioritization of files",
                    "default": True
                }
            },
            "required": []
        }
    },
    {
        "name": "get_project_info",
        "description": "Get comprehensive project information including git status, metadata, and statistics",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_stats": {
                    "type": "boolean",
                    "description": "Include file count and size statistics",
                    "default": True
                }
            },
            "required": []
        }
    },
    {
        "name": "get_git_status",
        "description": "Get current git repository status, changes, and branch information",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_untracked": {
                    "type": "boolean",
                    "description": "Include untracked files in the status",
                    "default": True
                },
                "verbose": {
                    "type": "boolean",
                    "description": "Include detailed diff information",
                    "default": False
                }
            },
            "required": []
        }
    },
    {
        "name": "get_git_commit_history",
        "description": "Get git commit history with intelligent limitations. EXPENSIVE OPERATION - only use when explicitly asked about git history, past commits, or when commit context is specifically needed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of commits to return",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100
                },
                "since": {
                    "type": "string",
                    "description": "Get commits since this date/time (e.g., '2024-01-01', '1 week ago', '2 days ago')",
                    "maxLength": 50
                },
                "author": {
                    "type": "string",
                    "description": "Filter commits by author name or email",
                    "maxLength": 100
                },
                "branch": {
                    "type": "string",
                    "description": "Specific branch to query (default: current branch)",
                    "maxLength": 100
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 15,
                    "minimum": 5,
                    "maximum": 30
                }
            },
            "required": []
        }
    },
    {
        "name": "get_git_branches",
        "description": "Get git branch information including local and remote branches. POTENTIALLY EXPENSIVE - only use when explicitly asked about branches, branch comparisons, or branch-specific context.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_remote": {
                    "type": "boolean",
                    "description": "Include remote branches in the result",
                    "default": True
                },
                "include_merged": {
                    "type": "boolean",
                    "description": "Include branches that have been merged",
                    "default": True
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 10,
                    "minimum": 5,
                    "maximum": 20
                }
            },
            "required": []
        }
    },
    {
        "name": "get_git_diff",
        "description": "Get git diff for commits or files to see actual code changes and comments. Useful for understanding what was changed in specific commits.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "commit_hash": {
                    "type": "string",
                    "description": "Specific commit hash to show diff for. Use 'HEAD' for latest commit, or full/partial hash.",
                    "maxLength": 40
                },
                "file_path": {
                    "type": "string",
                    "description": "Specific file to show diff for (optional)",
                    "maxLength": 500
                },
                "staged": {
                    "type": "boolean",
                    "description": "Show staged changes instead of committed changes",
                    "default": False
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds",
                    "default": 15,
                    "minimum": 5,
                    "maximum": 30
                }
            },
            "required": []
        }
    },
    {
        "name": "get_conversation_context",
        "description": "Get recent conversation history for contextual awareness and continuity",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of conversations to include",
                    "default": MCP_CONVERSATION_LIMIT,
                    "minimum": 1,
                    "maximum": 50
                },
                "include_messages": {
                    "type": "boolean",
                    "description": "Include actual message content (otherwise just metadata)",
                    "default": False
                },
                "search_query": {
                    "type": "string",
                    "description": "Search for conversations containing specific keywords",
                    "maxLength": 100
                },
                "type": {
                    "type": "string",
                    "enum": ["real", "analytics", "all"],
                    "description": "Type of conversations to retrieve: 'real' (actual conversations), 'analytics' (tool usage sessions), or 'all'",
                    "default": "all"
                }
            },
            "required": []
        }
    },
    {
        "name": "store_conversation",
        "description": "Store current conversation for future reference and context building. Supports both real conversations and analytics data.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "conversation_id": {
                    "type": "string",
                    "description": "Unique identifier for the conversation",
                    "minLength": 1,
                    "maxLength": 100,
                    "pattern": "^[a-zA-Z0-9_-]+$"
                },
                "messages": {
                    "type": "array",
                    "description": "Array of message objects in the conversation",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {
                                "type": "string",
                                "enum": ["user", "assistant", "system"],
                                "description": "Role of the message sender"
                            },
                            "content": {
                                "type": "string",
                                "description": "Content of the message",
                                "minLength": 1,
                                "maxLength": 50000
                            },
                            "timestamp": {
                                "type": "string",
                                "format": "date-time",
                                "description": "ISO timestamp of when the message was created"
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Additional metadata for the message",
                                "properties": {
                                    "file_context": {"type": "string"},
                                    "git_branch": {"type": "string"},
                                    "cursor_position": {"type": "object"}
                                }
                            }
                        },
                        "required": ["role", "content"],
                        "additionalProperties": False
                    },
                    "minItems": 1,
                    "maxItems": 100
                },
                "title": {
                    "type": "string",
                    "description": "Optional title for the conversation",
                    "maxLength": 200
                },
                "tags": {
                    "type": "array",
                    "description": "Tags for categorizing the conversation",
                    "items": {"type": "string", "maxLength": 50},
                    "maxItems": 10
                },
                "type": {
                    "type": "string",
                    "enum": ["real", "analytics"],
                    "description": "Type of conversation: 'real' for actual conversations, 'analytics' for tool usage sessions",
                    "default": "real"
                }
            },
            "required": ["conversation_id", "messages"],
            "additionalProperties": False
        }
    },
    {
        "name": "list_conversations",
        "description": "List recent conversations for this project with metadata and search capabilities",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of conversations to return",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100
                },
                "type": {
                    "type": "string",
                    "enum": ["real", "analytics", "all"],
                    "description": "Type of conversations to list: 'real', 'analytics', or 'all'",
                    "default": "all"
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["created_at", "updated_at", "message_count", "title"],
                    "description": "Sort conversations by field",
                    "default": "created_at"
                },
                "sort_order": {
                    "type": "string",
                    "enum": ["asc", "desc"],
                    "description": "Sort order",
                    "default": "desc"
                },
                "filter_tags": {
                    "type": "array",
                    "description": "Filter by conversation tags",
                    "items": {"type": "string"},
                    "maxItems": 5
                },
                "date_from": {
                    "type": "string",
                    "format": "date",
                    "description": "Filter conversations from this date (YYYY-MM-DD)"
                },
                "date_to": {
                    "type": "string",
                    "format": "date",
                    "description": "Filter conversations to this date (YYYY-MM-DD)"
                }
            },
            "required": []
        }
    },
    {
        "name": "search_conversations",
        "description": "Search conversations by content, title, or tags with advanced filtering",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to find in conversation content, titles, or tags",
                    "minLength": 1,
                    "maxLength": 100
                },
                "type": {
                    "type": "string",
                    "enum": ["real", "analytics", "all"],
                    "description": "Type of conversations to search: 'real', 'analytics', or 'all'",
                    "default": "all"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of search results to return",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_conversation_summary",
        "description": "Get a detailed summary of a specific conversation including metadata and key messages",
        "inputSchema": {
            "type": "object",
            "properties": {
                "conversation_id": {
                    "type": "string",
                    "description": "Unique identifier for the conversation to summarize",
                    "minLength": 1,
                    "maxLength": 100
                }
            },
            "required": ["conversation_id"]
        }
    }
]

# Tool categories for better organization
TOOL_CATEGORIES = {
    "project": ["list_project_files", "get_project_info"],
    "git": ["get_git_status", "get_git_commit_history", "get_git_branches", "get_git_diff"],
    "conversation": ["get_conversation_context", "store_conversation", "list_conversations"],
}

# Tool permissions (future use)
TOOL_PERMISSIONS = {
    "read_only": ["list_project_files", "get_project_info", "get_git_status", "get_git_commit_history", "get_git_branches", "get_git_diff", "get_conversation_context", "list_conversations"],
    "write": ["store_conversation"],
    "expensive": ["get_git_commit_history", "get_git_branches"],  # Mark expensive operations
} 