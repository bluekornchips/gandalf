"""
Conversation aggregator for Gandalf MCP server.

This module provides the primary conversation interface that automatically detects
and aggregates conversation data from all available IDEs (Cursor, Claude Code, etc.)
into a standardized format. This is the default conversation interface that users
should use for accessing conversation history.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from src.adapters.factory import AdapterFactory
from src.config.constants.conversations import (
    CONVERSATION_DEFAULT_RECENT_DAYS,
    CONVERSATION_MAX_LOOKBACK_DAYS,
    CONVERSATION_TYPES,
)
from src.config.constants.system import (
    CONVERSATION_DEFAULT_LIMIT,
    CONVERSATION_DEFAULT_MIN_SCORE,
    CONVERSATION_MAX_LIMIT,
    SUPPORTED_IDES,
)
from src.core.conversation_analysis import generate_shared_context_keywords
from src.core.database_scanner import get_available_ides
from src.utils.access_control import AccessValidator
from src.utils.common import log_debug, log_error, log_info
from src.utils.performance import get_duration, start_timer


def _standardize_conversation_format(
    conversation: Dict[str, Any],
    source_ide: str,
    context_keywords: List[str] = None,
) -> Dict[str, Any]:
    """Standardize conversation format across different IDEs."""
    try:
        # Common fields that should exist in standardized format
        standardized = {
            "source_ide": source_ide,
            "conversation_id": "",
            "title": "",
            "summary": "",
            "last_updated": "",
            "created_at": "",
            "working_directory": "",
            "message_count": 0,
            "relevance_score": 0.0,
            "conversation_type": "general",
            "keyword_matches": [],
            "file_references": [],
        }

        # Map IDE-specific fields to standardized format
        if source_ide == "cursor":
            standardized.update(
                {
                    "conversation_id": conversation.get("conversation_id", ""),
                    "title": conversation.get("name", ""),
                    "summary": conversation.get("name", "")[:200]
                    + (
                        "..."
                        if len(conversation.get("name", "")) > 200
                        else ""
                    ),
                    "last_updated": conversation.get("last_updated", ""),
                    "created_at": conversation.get("created_at", ""),
                    "working_directory": conversation.get(
                        "workspace_hash", ""
                    ),
                    "message_count": conversation.get("total_exchanges", 0),
                    "relevance_score": conversation.get("activity_score", 0.0),
                }
            )

        elif source_ide == "claude-code":
            standardized.update(
                {
                    "conversation_id": conversation.get("session_id", ""),
                    "title": (
                        conversation.get("summary", "").split("...")[0]
                        if conversation.get("summary")
                        else ""
                    ),
                    "summary": conversation.get("summary", ""),
                    "last_updated": conversation.get("last_modified", ""),
                    "created_at": conversation.get("start_time", ""),
                    "working_directory": conversation.get(
                        "working_directory", ""
                    ),
                    "message_count": conversation.get("message_count", 0),
                    "relevance_score": conversation.get(
                        "relevance_score", 0.0
                    ),
                    "conversation_type": conversation.get(
                        "conversation_type", "general"
                    ),
                    "keyword_matches": conversation.get("keyword_matches", []),
                    "file_references": conversation.get("file_references", []),
                }
            )

        return standardized

    except Exception as e:
        log_error(e, f"standardizing conversation from {source_ide}")
        return standardized


def _detect_available_ides() -> List[str]:
    """Detect available IDEs with fallback chain: database to environment."""
    try:
        # First try database-based detection, should be most reliable
        available_ides = get_available_ides(silent=True)
        if available_ides:
            log_debug(f"Database scanner found IDEs: {available_ides}")
            return available_ides

        log_info("No databases found, falling back to environment detection")

        # Fallback to environment-based detection
        detected_ides = []
        for ide_name in SUPPORTED_IDES:
            try:
                adapter = AdapterFactory.create_adapter(explicit_ide=ide_name)
                if adapter.detect_ide():
                    detected_ides.append(ide_name)
            except Exception as e:
                log_debug(f"Error detecting {ide_name}: {e}")

        log_debug(f"Environment detection found IDEs: {detected_ides}")
        return detected_ides

    except Exception as e:
        log_error(e, "IDE detection")
        return []


def _process_ide_conversations(
    ide_name: str,
    handler_name: str,
    arguments: Dict[str, Any],
    project_root: Path,
    context_keywords: List[str],
    **kwargs,
) -> Dict[str, Any]:
    """Process conversations from a single IDE with standardized error handling."""
    try:
        adapter = AdapterFactory.create_adapter(
            explicit_ide=ide_name, project_root=str(project_root)
        )
        handlers = adapter.get_conversation_handlers()

        # Get the appropriate handler
        handler = None
        if ide_name == "cursor":
            handler = handlers.get(f"{handler_name}_cursor_conversations")
        elif ide_name == "claude-code":
            # Try enhanced version first, then fall back to basic
            if handler_name == "search":
                handler = handlers.get(
                    "search_claude_conversations_enhanced"
                ) or handlers.get("search_claude_conversations")
            else:
                handler = handlers.get(f"{handler_name}_claude_conversations")

        if not handler:
            log_debug(f"No {handler_name} handler found for {ide_name}")
            return {"error": f"No {handler_name} handler available"}

        log_info(f"Calling {handler_name} handler for {ide_name}")
        result = handler(arguments, project_root, **kwargs)

        if not result.get("content") or result.get("isError"):
            return {
                "error": f"Handler returned error: {result.get('error', 'Unknown error')}"
            }

        # Extract and parse JSON response
        content_text = result["content"][0]["text"]
        ide_data = json.loads(content_text)

        # Handle different response formats
        conversations = []
        if "conversations" in ide_data:  # Cursor format
            conversations = ide_data["conversations"]
        elif "results" in ide_data:  # Claude Code format
            conversations = ide_data["results"]

        # Standardize conversations
        standardized_conversations = []
        for conv in conversations:
            standardized_conv = _standardize_conversation_format(
                conv, ide_name, context_keywords
            )

            # Add search-specific fields, if this is a search operation
            if handler_name == "search":
                standardized_conv["match_count"] = conv.get("match_count", 1)
                standardized_conv["matches"] = conv.get("matches", [])

            standardized_conversations.append(standardized_conv)

        return {
            "conversations": standardized_conversations,
            "count": len(standardized_conversations),
            "total_analyzed": ide_data.get(
                "total_analyzed", len(standardized_conversations)
            ),
            "total_results": ide_data.get(
                "total_results", len(standardized_conversations)
            ),
            "processing_time": ide_data.get("processing_time", 0.0),
        }

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        log_error(e, f"parsing {ide_name} conversation data")
        return {"error": f"Data parsing error: {str(e)}"}
    except Exception as e:
        log_error(e, f"processing conversations from {ide_name}")
        return {"error": str(e)}


def _create_no_ides_response(
    operation_type: str,
    context_keywords: List[str],
    processing_time: float,
    **extra_fields,
) -> Dict[str, Any]:
    """Create standardized response when no IDEs are detected."""
    base_response = {
        "available_ides": [],
        "context_keywords": context_keywords,
        "processing_time": processing_time,
        "message": "No compatible IDEs detected",
    }

    if operation_type == "recall":
        base_response.update(
            {
                "conversations": [],
                "total_conversations": 0,
            }
        )
    elif operation_type == "search":
        base_response.update(
            {
                "results": [],
                "total_results": 0,
                "query": extra_fields.get("query", ""),
            }
        )

    base_response.update(extra_fields)
    return base_response


def handle_recall_conversations(
    arguments: Dict[str, Any], project_root: Path, **kwargs
) -> Dict[str, Any]:
    """
    Cross-platform conversation recall that aggregates results from all available IDEs.

    This function detects available IDEs and combines their conversation data
    into a standardized format.
    """
    try:
        # Get parameters
        fast_mode = arguments.get("fast_mode", True)
        days_lookback = arguments.get(
            "days_lookback", CONVERSATION_DEFAULT_RECENT_DAYS
        )
        limit = min(
            arguments.get("limit", CONVERSATION_DEFAULT_LIMIT),
            CONVERSATION_MAX_LIMIT,
        )
        arguments.get("conversation_types", [])
        min_score = arguments.get("min_score", CONVERSATION_DEFAULT_MIN_SCORE)

        # Validate parameters
        days_lookback = min(days_lookback, CONVERSATION_MAX_LOOKBACK_DAYS)

        timer = start_timer()

        # Generate shared context keywords
        context_keywords = generate_shared_context_keywords(project_root)
        log_info(
            f"Generated {len(context_keywords)} context keywords for conversation recall"
        )

        available_ides = _detect_available_ides()

        if not available_ides:
            response = _create_no_ides_response(
                "recall",
                context_keywords,
                get_duration(timer),
                fast_mode=fast_mode,
                days_lookback=days_lookback,
                min_score=min_score,
            )
            return AccessValidator.create_json_response(response)

        log_info(
            f"Found {len(available_ides)} available IDEs: {', '.join(available_ides)}"
        )

        # Collect conversations from all available IDEs
        all_conversations = []
        ide_results = {}

        for ide_name in available_ides:
            try:
                result = _process_ide_conversations(
                    ide_name,
                    "recall",
                    arguments,
                    project_root,
                    context_keywords,
                    **kwargs,
                )

                if result.get("error"):
                    log_error(
                        result["error"],
                        f"retrieving conversations from {ide_name}",
                    )
                    ide_results[ide_name] = result
                else:
                    all_conversations.extend(result["conversations"])
                    ide_results[ide_name] = result

            except Exception as e:
                log_error(e, f"retrieving conversations from {ide_name}")
                ide_results[ide_name] = {"error": str(e)}

        # Sort all conversations by relevance score descending
        all_conversations.sort(
            key=lambda x: x.get("relevance_score", 0), reverse=True
        )

        # Apply limit
        all_conversations = all_conversations[:limit]

        processing_time = get_duration(timer)

        result = {
            "conversations": all_conversations,
            "total_conversations": len(all_conversations),
            "available_ides": available_ides,
            "ide_results": ide_results,
            "context_keywords": context_keywords,
            "processing_time": processing_time,
            "fast_mode": fast_mode,
            "days_lookback": days_lookback,
            "min_score": min_score,
        }

        log_info(
            f"Conversation recall returned {len(all_conversations)} conversations "
            f"from {len(available_ides)} IDEs in {processing_time:.2f}s"
        )
        return AccessValidator.create_json_response(result)

    except Exception as e:
        log_error(e, "conversation recall")
        return AccessValidator.create_error_response(
            f"Error in conversation recall: {str(e)}"
        )


def handle_search_conversations(
    arguments: Dict[str, Any], project_root: Path, **kwargs
) -> Dict[str, Any]:
    """
    Cross-platform conversation search that aggregates results from all available IDEs.

    This function detects available IDEs and combines their search results
    into a standardized format.
    """
    try:
        # Get parameters
        query = arguments.get("query", "").strip()
        limit = arguments.get("limit", 20)
        arguments.get("include_content", False)
        days_lookback = arguments.get("days_lookback", 30)

        if not query:
            return AccessValidator.create_error_response(
                "query parameter is required"
            )

        timer = start_timer()

        # Generate shared context keywords
        context_keywords = generate_shared_context_keywords(project_root)
        log_info(
            f"Generated {len(context_keywords)} context keywords for conversation search"
        )

        available_ides = _detect_available_ides()

        if not available_ides:
            response = _create_no_ides_response(
                "search",
                context_keywords,
                get_duration(timer),
                query=query,
                days_lookback=days_lookback,
            )
            return AccessValidator.create_json_response(response)

        log_info(
            f"Searching across {len(available_ides)} available IDEs: {', '.join(available_ides)}"
        )

        # Collect search results from all available IDEs
        all_results = []
        ide_results = {}

        for ide_name in available_ides:
            try:
                result = _process_ide_conversations(
                    ide_name,
                    "search",
                    arguments,
                    project_root,
                    context_keywords,
                    **kwargs,
                )

                if result.get("error"):
                    log_error(
                        result["error"],
                        f"searching conversations in {ide_name}",
                    )
                    ide_results[ide_name] = result
                else:
                    all_results.extend(result["conversations"])
                    ide_results[ide_name] = result

            except Exception as e:
                log_error(e, f"searching conversations in {ide_name}")
                ide_results[ide_name] = {"error": str(e)}

        # Sort all results by relevance score descending
        all_results.sort(
            key=lambda x: x.get("relevance_score", 0), reverse=True
        )

        # Apply limit
        all_results = all_results[:limit]

        processing_time = get_duration(timer)

        result = {
            "query": query,
            "results": all_results,
            "total_results": len(all_results),
            "available_ides": available_ides,
            "ide_results": ide_results,
            "context_keywords": context_keywords,
            "processing_time": processing_time,
            "days_lookback": days_lookback,
            "search_timestamp": datetime.now().isoformat(),
        }

        log_info(
            f"Conversation search returned {len(all_results)} results "
            f"from {len(available_ides)} IDEs in {processing_time:.2f}s"
        )
        return AccessValidator.create_json_response(result)

    except Exception as e:
        log_error(e, "conversation search")
        return AccessValidator.create_error_response(
            f"Error in conversation search: {str(e)}"
        )


# Tool definitions
TOOL_RECALL_CONVERSATIONS = {
    "name": "recall_conversations",
    "description": (
        "Recall and analyze relevant conversations with intelligent aggregation. "
        f"Automatically detects and combines results from available IDEs "
        f"({', '.join(SUPPORTED_IDES)}, etc.) for comprehensive conversation context."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "fast_mode": {
                "type": "boolean",
                "default": True,
                "description": "Use fast extraction (seconds) vs full analysis (minutes). Recommended: true",
            },
            "days_lookback": {
                "type": "integer",
                "default": CONVERSATION_DEFAULT_RECENT_DAYS,
                "minimum": 1,
                "maximum": CONVERSATION_MAX_LOOKBACK_DAYS,
                "description": "Number of days to look back for conversations (default: 7 days for recent focus)",
            },
            "limit": {
                "type": "integer",
                "default": CONVERSATION_DEFAULT_LIMIT,
                "minimum": 1,
                "maximum": CONVERSATION_MAX_LIMIT,
                "description": "Maximum number of conversations to return",
            },
            "conversation_types": {
                "type": "array",
                "items": {"type": "string", "enum": CONVERSATION_TYPES},
                "description": "Filter by conversation types (only used when fast_mode=false)",
            },
            "min_score": {
                "type": "number",
                "default": CONVERSATION_DEFAULT_MIN_SCORE,
                "minimum": 0.0,
                "maximum": 5.0,
                "description": "Minimum relevance score threshold (only used when fast_mode=false)",
            },
        },
        "required": [],
    },
    "annotations": {
        "title": "Recall Conversations",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}

TOOL_SEARCH_CONVERSATIONS = {
    "name": "search_conversations",
    "description": (
        "Search conversation history for specific topics, keywords, or context. "
        f"Automatically detects and searches across available IDEs "
        f"({', '.join(SUPPORTED_IDES)}, etc.) for comprehensive results."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query to find in conversation content",
            },
            "limit": {
                "type": "integer",
                "default": 20,
                "minimum": 1,
                "maximum": 100,
                "description": "Maximum number of conversations to return",
            },
            "include_content": {
                "type": "boolean",
                "default": False,
                "description": "Include matched content snippets in results",
            },
            "days_lookback": {
                "type": "integer",
                "default": 30,
                "minimum": 0,
                "maximum": 365,
                "description": "Number of days to look back (0 for all time)",
            },
        },
        "required": ["query"],
    },
    "annotations": {
        "title": "Search Conversations",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}

# Tool handlers and definitions
CONVERSATION_AGGREGATOR_TOOL_HANDLERS = {
    "recall_conversations": handle_recall_conversations,
    "search_conversations": handle_search_conversations,
}

CONVERSATION_AGGREGATOR_TOOL_DEFINITIONS = [
    TOOL_RECALL_CONVERSATIONS,
    TOOL_SEARCH_CONVERSATIONS,
]
