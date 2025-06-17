"""Tool handler registry for Gandalf MCP server."""

from typing import Any, Dict, Callable

# Import all tool handlers
from src.tool_calls.file.file_operations import handle_list_project_files
from src.tool_calls.git.git_operations import (
    handle_get_git_status,
    handle_get_git_commit_history,
    handle_get_git_branches,
    handle_get_git_diff,
)
from src.tool_calls.conversations.conversation_operations import (
    handle_get_conversation_context,
    handle_store_conversation,
    handle_list_conversations,
    handle_search_conversations,
    handle_get_conversation_summary,
)
from src.tool_calls.project.project_operations import handle_get_project_info

# Registry of all tool handlers
ALL_TOOL_HANDLERS: Dict[str, Callable] = {
    # File operations
    "list_project_files": handle_list_project_files,
    
    # Project operations
    "get_project_info": handle_get_project_info,
    
    # Git operations
    "get_git_status": handle_get_git_status,
    "get_git_commit_history": handle_get_git_commit_history,
    "get_git_branches": handle_get_git_branches,
    "get_git_diff": handle_get_git_diff,
    
    # Enhanced conversation operations
    "get_conversation_context": handle_get_conversation_context,
    "store_conversation": handle_store_conversation,
    "list_conversations": handle_list_conversations,
    "search_conversations": handle_search_conversations,
    "get_conversation_summary": handle_get_conversation_summary,
} 