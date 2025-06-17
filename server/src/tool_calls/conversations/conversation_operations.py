"""Enhanced conversation operations for Gandalf MCP server.

1. Real conversation storage (user/assistant messages)
2. Analytics tracking (tool call sessions)
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

# Add parent directories to path for imports
current_dir = Path(__file__).parent
server_dir = current_dir.parent.parent.parent
sys.path.insert(0, str(server_dir))

from src.tool_calls.conversations.conversation_cache import (
    get_conversation_cache,
    get_conversation_context,
    store_conversation,
    store_real_conversation,
    get_real_conversation_context,
)
from src.utils import log_error


def handle_get_conversation_context(
    project_root: Path, 
    arguments: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """Get recent conversation history for context.
    
    Now supports both real conversations and analytics sessions.
    """
    try:
        limit = arguments.get("limit", 10)
        include_messages = arguments.get("include_messages", False)
        search_query = arguments.get("search_query")
        conversation_type = arguments.get("type", "all")  # "real", "analytics", or "all"
        
        cache = get_conversation_cache(str(project_root))
        
        if conversation_type == "real":
            context = get_real_conversation_context(project_root, limit, include_messages, search_query)
        elif conversation_type == "analytics":
            context = get_conversation_context(project_root, limit)
        else:
            # Combined context - real conversations first, then analytics
            real_context = get_real_conversation_context(project_root, limit // 2, include_messages, search_query)
            analytics_context = get_conversation_context(project_root, limit // 2)
            
            context = f"""# Conversation Context for {cache.project_name}

## Real Conversations
{real_context}

## Analytics Sessions (Tool Usage)
{analytics_context}
"""
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": context
                }
            ]
        }
        
    except Exception as e:
        log_error(e, "getting conversation context")
        return {
            "content": [
                {
                    "type": "text", 
                    "text": f"Error retrieving conversation context: {str(e)}"
                }
            ]
        }


def handle_store_conversation(
    project_root: Path, 
    arguments: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """Store a conversation with enhanced capabilities.
    
    Supports both real conversations and analytics sessions.
    """
    try:
        conversation_id = arguments.get("conversation_id")
        messages = arguments.get("messages", [])
        title = arguments.get("title")
        tags = arguments.get("tags", [])
        conversation_type = arguments.get("type", "real")  # "real" or "analytics"
        
        if not conversation_id:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: conversation_id is required"
                    }
                ]
            }
        
        if not messages:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: messages array is required"
                    }
                ]
            }
        
        # Validate message format
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: Message {i} must be an object"
                        }
                    ]
                }
            
            if "role" not in msg or "content" not in msg:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: Message {i} must have 'role' and 'content' fields"
                        }
                    ]
                }
            
            if msg["role"] not in ["user", "assistant", "system"]:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: Message {i} role must be 'user', 'assistant', or 'system'"
                        }
                    ]
                }
        
        # Store based on type
        if conversation_type == "real":
            result = store_real_conversation(
                project_root, 
                conversation_id, 
                messages, 
                title=title, 
                tags=tags
            )
        else:
            # Legacy analytics storage
            result = store_conversation(project_root, conversation_id, messages)
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Successfully stored {conversation_type} conversation '{conversation_id}' with {len(messages)} messages"
                }
            ]
        }
        
    except Exception as e:
        log_error(e, "storing conversation")
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error storing conversation: {str(e)}"
                }
            ]
        }


def handle_list_conversations(
    project_root: Path, 
    arguments: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """List conversations with enhanced filtering and metadata."""
    try:
        limit = arguments.get("limit", 20)
        conversation_type = arguments.get("type", "all")  # "real", "analytics", or "all"
        sort_by = arguments.get("sort_by", "created_at")  # "created_at", "updated_at", "message_count"
        sort_order = arguments.get("sort_order", "desc")  # "asc" or "desc"
        filter_tags = arguments.get("filter_tags", [])
        date_from = arguments.get("date_from")
        date_to = arguments.get("date_to")
        
        cache = get_conversation_cache(str(project_root))
        
        # Get conversations based on type
        if conversation_type == "real":
            conversations = cache.list_real_conversations(
                limit=limit,
                sort_by=sort_by,
                sort_order=sort_order,
                filter_tags=filter_tags,
                date_from=date_from,
                date_to=date_to
            )
        elif conversation_type == "analytics":
            conversations = cache.list_conversations(limit)
        else:
            # Combined list
            real_convs = cache.list_real_conversations(limit // 2)
            analytics_convs = cache.list_conversations(limit // 2)
            
            # Mark conversation types
            for conv in real_convs:
                conv["conversation_type"] = "real"
            for conv in analytics_convs:
                conv["conversation_type"] = "analytics"
            
            conversations = real_convs + analytics_convs
            
            # Sort combined list with safe timestamp handling
            conversations.sort(
                key=lambda x: x.get("timestamp", 0) or 0,
                reverse=(sort_order == "desc")
            )
            conversations = conversations[:limit]
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(conversations, indent=2)
                }
            ]
        }
        
    except Exception as e:
        log_error(e, "listing conversations")
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error listing conversations: {str(e)}"
                }
            ]
        }


def handle_search_conversations(
    project_root: Path,
    arguments: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """Search conversations by content, title, or tags."""
    try:
        query = arguments.get("query", "")
        conversation_type = arguments.get("type", "all")
        limit = arguments.get("limit", 10)
        
        if not query:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: search query is required"
                    }
                ]
            }
        
        cache = get_conversation_cache(str(project_root))
        results = cache.search_conversations(query, conversation_type, limit)
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(results, indent=2)
                }
            ]
        }
        
    except Exception as e:
        log_error(e, "searching conversations")
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error searching conversations: {str(e)}"
                }
            ]
        }


def handle_get_conversation_summary(
    project_root: Path,
    arguments: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """Get a summary of a specific conversation."""
    try:
        conversation_id = arguments.get("conversation_id")
        
        if not conversation_id:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: conversation_id is required"
                    }
                ]
            }
        
        cache = get_conversation_cache(str(project_root))
        summary = cache.get_conversation_summary(conversation_id)
        
        if summary is None:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Conversation not found: {conversation_id}"
                    }
                ]
            }
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": summary
                }
            ]
        }
        
    except Exception as e:
        log_error(e, "getting conversation summary")
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error getting conversation summary: {str(e)}"
                }
            ]
        }


# Tool handler registry
CONVERSATION_TOOL_HANDLERS = {
    "get_conversation_context": handle_get_conversation_context,
    "store_conversation": handle_store_conversation,
    "list_conversations": handle_list_conversations,
    "search_conversations": handle_search_conversations,
    "get_conversation_summary": handle_get_conversation_summary,
} 