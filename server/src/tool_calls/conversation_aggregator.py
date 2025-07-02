"""
Conversation aggregation tool for Gandalf MCP Server.

This module provides the primary conversation interface that automatically detects
and aggregates conversation data from all available tools (Cursor, Claude Code, etc.)
for comprehensive context analysis.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.constants import DEFAULT_FAST_MODE
from config.constants import (
    CONVERSATION_DEFAULT_LOOKBACK_DAYS,
    CONVERSATION_DEFAULT_LIMIT,
    CONVERSATION_DEFAULT_MIN_SCORE,
    SUPPORTED_AGENTIC_TOOLS,
    AGENTIC_TOOL_CURSOR,
    AGENTIC_TOOL_CLAUDE_CODE,
    AGENTIC_TOOL_WINDSURF,
    TOKEN_OPTIMIZATION_MAX_RESPONSE_SIZE,
    TOKEN_OPTIMIZATION_CONTENT_TRUNCATION_LIMIT,
    TOKEN_OPTIMIZATION_SUMMARY_MODE_THRESHOLD,
    TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS,
    TOKEN_OPTIMIZATION_MAX_TOOL_RESULT_FIELDS,
)
from tool_calls.conversation_recall import (
    handle_recall_cursor_conversations as cursor_recall_handler,
)
from tool_calls.claude_code_recall import (
    handle_recall_claude_conversations as claude_recall_handler,
)
from tool_calls.windsurf_recall import (
    handle_recall_windsurf_conversations as windsurf_recall_handler,
)
from tool_calls.cursor_query import handle_query_cursor_conversations
from tool_calls.claude_code_query import handle_query_claude_conversations
from tool_calls.windsurf_query import handle_query_windsurf_conversations
from core.conversation_analysis import generate_shared_context_keywords
from core.registry import get_registered_agentic_tools
from core.database_scanner import get_available_agentic_tools
from utils.access_control import AccessValidator
from utils.common import log_debug, log_error, log_info


def _convert_paths_for_json(obj):
    """Convert Path objects to strings for JSON serialization."""
    if isinstance(obj, Path):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: _convert_paths_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_paths_for_json(item) for item in obj]
    else:
        return obj


def _truncate_string_field(
    text: str, limit: int = TOKEN_OPTIMIZATION_CONTENT_TRUNCATION_LIMIT
) -> str:
    """Truncate string fields for token optimization."""
    if not text or len(text) <= limit:
        return text
    return text[:limit] + "..."


def _create_lightweight_conversation(
    conversation: Dict[str, Any], source_tool: str
) -> Dict[str, Any]:
    """Create lightweight conversation format for token optimization."""
    return {
        "id": conversation.get("id", "")[:50],  # Limit ID length
        "title": _truncate_string_field(conversation.get("title", ""), 100),
        "source_tool": source_tool,
        "message_count": conversation.get("message_count", 0),
        "relevance_score": round(conversation.get("relevance_score", 0.0), 2),
        "created_at": conversation.get("created_at", ""),
        "snippet": _truncate_string_field(conversation.get("snippet", ""), 150),
    }


def _standardize_conversation_format(
    conversation: Dict[str, Any],
    source_tool: str,
    context_keywords: List[str],
    lightweight: bool = False,
) -> Dict[str, Any]:
    """Standardize conversation format across different tools."""
    try:
        # Use lightweight format for token optimization
        if lightweight:
            return _create_lightweight_conversation(conversation, source_tool)

        standardized = {
            "id": conversation.get("id", ""),
            "title": _truncate_string_field(conversation.get("title", "")),
            "source_tool": source_tool,
            "created_at": conversation.get("created_at", ""),
            "updated_at": conversation.get("updated_at", ""),
            "message_count": conversation.get("message_count", 0),
            "relevance_score": round(conversation.get("relevance_score", 0.0), 2),
            "snippet": _truncate_string_field(conversation.get("snippet", "")),
        }

        # Map tool-specific fields to standardized format
        if source_tool == AGENTIC_TOOL_CURSOR:
            # Cursor-specific field mappings
            standardized.update(
                {
                    "workspace_id": conversation.get("workspace_id", ""),
                    "conversation_type": conversation.get("conversation_type", ""),
                    "ai_model": conversation.get("ai_model", ""),
                    "user_query": conversation.get("user_query", ""),
                    "ai_response": conversation.get("ai_response", ""),
                    "file_references": conversation.get("file_references", []),
                    "code_blocks": conversation.get("code_blocks", []),
                    "conversation_metadata": conversation.get("metadata", {}),
                }
            )
        elif source_tool == AGENTIC_TOOL_CLAUDE_CODE:
            # Claude Code-specific field mappings
            standardized.update(
                {
                    "session_id": conversation.get("session_id", ""),
                    "project_context": conversation.get("project_context", {}),
                    "conversation_context": conversation.get("context", {}),
                    "messages": conversation.get("messages", []),
                    "session_metadata": conversation.get("metadata", {}),
                    "analysis_results": conversation.get("analysis", {}),
                    "tool_usage": conversation.get("tool_usage", []),
                    "project_files": conversation.get("project_files", []),
                }
            )
        elif source_tool == AGENTIC_TOOL_WINDSURF:
            # Windsurf-specific field mappings
            standardized.update(
                {
                    "workspace_id": conversation.get("workspace_id", ""),
                    "database_path": conversation.get("database_path", ""),
                    "session_data": conversation.get("session_data", {}),
                    "windsurf_source": conversation.get(
                        "windsurf_source", conversation.get("source", "")
                    ),
                    "chat_session_id": conversation.get(
                        "chat_session_id", conversation.get("id", "")
                    ),
                    "windsurf_metadata": conversation.get(
                        "windsurf_metadata", conversation.get("metadata", {})
                    ),
                }
            )

        # Add context intelligence (limit keywords for token optimization)
        standardized["context_keywords"] = context_keywords[
            :TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS
        ]
        standardized["keyword_matches"] = []

        return standardized

    except Exception as e:
        log_error(e, f"standardizing conversation from {source_tool}")
        return {}


def _detect_available_agentic_tools() -> List[str]:
    """Detect available tools using the database scanner for comprehensive detection."""
    try:
        # Use database scanner for better tool detection
        available_tools = get_available_agentic_tools(silent=True)
        log_info(f"Found available tools via database scanner: {available_tools}")

        # Also check for tools with accessible databases even if no conversations
        from core.database_scanner import DatabaseScanner

        scanner = DatabaseScanner()
        databases = scanner.scan()

        accessible_tools = set()
        for db in databases:
            if db.is_accessible:
                accessible_tools.add(db.tool_type)

        # Combine tools with conversations and tools with accessible databases
        all_tools = set(available_tools) | accessible_tools

        if all_tools:
            result = list(all_tools)
            log_info(
                f"Combined available tools (with conversations + accessible): {result}"
            )
            return result

        # Fallback to registry if database scanner finds nothing
        registered_tools = get_registered_agentic_tools()
        log_info(f"Fallback to registered tools: {registered_tools}")
        return registered_tools

    except Exception as e:
        log_error(e, "detecting available tools")
        # Final fallback to registry
        try:
            registered_tools = get_registered_agentic_tools()
            log_info(f"Final fallback to registered tools: {registered_tools}")
            return registered_tools
        except Exception as registry_error:
            log_error(registry_error, "detecting tools from registry")
            return []


def _process_agentic_tool_conversations(
    tool_name: str,
    handler_name: str,
    context_keywords: List[str],
    **kwargs,
) -> Dict[str, Any]:
    """Process conversations from a single tool with standardized error handling."""
    try:
        handler = AGENTIC_TOOL_HANDLERS.get(tool_name, {}).get(handler_name)

        if not handler:
            log_debug(f"No {handler_name} handler found for {tool_name}")
            return {}

        log_info(f"Calling {handler_name} handler for {tool_name}")

        # Extract project_root from kwargs, default to current directory
        project_root = kwargs.pop("project_root", Path.cwd())

        # Call the tool-specific handler with proper arguments
        result = handler(kwargs, project_root)

        # Handle MCP response format
        if isinstance(result, dict) and "content" in result:
            # Extract the actual data from MCP response format
            content_items = result.get("content", [])
            if (
                content_items
                and isinstance(content_items, list)
                and len(content_items) > 0
            ):
                content_text = content_items[0].get("text", "{}")
            else:
                content_text = "{}"
        elif isinstance(result, dict):
            # Direct dictionary response
            serializable_result = _convert_paths_for_json(result)
            content_text = json.dumps(serializable_result)
        else:
            # String or other format
            content_text = str(result)

        # Parse the response and standardize format
        try:
            tool_data = json.loads(content_text)
        except json.JSONDecodeError:
            # If it's not valid JSON, try to work with raw data
            tool_data = {"conversations": [], "raw_response": content_text}

        if "conversations" in tool_data:  # Cursor format
            conversations = tool_data["conversations"]
        elif "results" in tool_data:  # Claude Code format
            conversations = tool_data["results"]
        else:
            conversations = []

        standardized_conversations = []
        # Determine if we should use lightweight format based on conversation count
        use_lightweight = len(conversations) > TOKEN_OPTIMIZATION_SUMMARY_MODE_THRESHOLD

        for conv in conversations:
            standardized_conv = _standardize_conversation_format(
                conv, tool_name, context_keywords, lightweight=use_lightweight
            )
            if standardized_conv:
                standardized_conversations.append(standardized_conv)

        # Return standardized metadata
        return {
            "conversations": standardized_conversations,
            "total_conversations": len(standardized_conversations),
            "source_tool": tool_name,
            "handler": handler_name,
            "total_analyzed": tool_data.get(
                "total_conversations", len(standardized_conversations)
            ),
            "total_results": tool_data.get(
                "total_results", len(standardized_conversations)
            ),
            "processing_time": tool_data.get("processing_time", 0.0),
        }

    except json.JSONDecodeError as e:
        log_error(e, f"parsing {tool_name} conversation data")
        return {"error": f"JSON parsing error: {str(e)}"}
    except Exception as e:
        log_error(e, f"processing conversations from {tool_name}")
        return {"error": str(e)}


def _create_no_tools_response(
    context_keywords: List[str],
    operation_type: str = "recall",
    processing_time: float = 0.0,
    **kwargs,
) -> Dict[str, Any]:
    """Create standardized response when no tools are detected."""
    response = {
        "available_tools": [],
        "context_keywords": context_keywords,
        "message": "No compatible tools detected",
        "conversations": [],
        "total_conversations": 0,
        "processing_time": processing_time,
        "tool_results": {},
    }

    # Add operation-specific fields
    if operation_type == "recall":
        response.update(
            {
                "fast_mode": kwargs.get("fast_mode", DEFAULT_FAST_MODE),
                "days_lookback": kwargs.get(
                    "days_lookback", CONVERSATION_DEFAULT_LOOKBACK_DAYS
                ),
                "min_score": kwargs.get("min_score", CONVERSATION_DEFAULT_MIN_SCORE),
                "limit": kwargs.get("limit", CONVERSATION_DEFAULT_LIMIT),
                "conversation_types": kwargs.get("conversation_types", []),
                "tools": kwargs.get("tools", []),
            }
        )
    elif operation_type == "search":
        response.update(
            {
                "query": kwargs.get("query", ""),
                "days_lookback": kwargs.get(
                    "days_lookback", CONVERSATION_DEFAULT_LOOKBACK_DAYS
                ),
                "include_content": kwargs.get("include_content", False),
                "limit": kwargs.get("limit", CONVERSATION_DEFAULT_LIMIT),
            }
        )

    return response


def _check_response_size_and_optimize(response: Dict[str, Any]) -> Dict[str, Any]:
    """Check response size and optimize if needed."""
    import json

    response_json = json.dumps(response)
    response_size = len(response_json.encode("utf-8"))

    if response_size <= TOKEN_OPTIMIZATION_MAX_RESPONSE_SIZE:
        return response

    log_info(f"Response size {response_size} bytes exceeds limit, optimizing...")

    # Remove verbose metadata from tool_results
    if "tool_results" in response:
        for tool_name, result in response["tool_results"].items():
            if isinstance(result, dict):
                # Keep only essential fields
                essential_fields = [
                    "total_conversations",
                    "source_tool",
                    "handler",
                    "processing_time",
                ]
                essential_fields = essential_fields[
                    :TOKEN_OPTIMIZATION_MAX_TOOL_RESULT_FIELDS
                ]
                response["tool_results"][tool_name] = {
                    k: v for k, v in result.items() if k in essential_fields
                }

    # Truncate context keywords
    if "context_keywords" in response:
        response["context_keywords"] = response["context_keywords"][
            :TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS
        ]

    # Create summary if still too large
    new_size = len(json.dumps(response).encode("utf-8"))
    if new_size > TOKEN_OPTIMIZATION_MAX_RESPONSE_SIZE:
        return _create_summary_response(response)

    return response


def _create_summary_response(original_response: Dict[str, Any]) -> Dict[str, Any]:
    """Create a summarized response when full response is too large."""
    conversations = original_response.get("conversations", [])

    # Group conversations by tool
    tool_summaries = {}
    for conv in conversations:
        tool = conv.get("source_tool", "unknown")
        if tool not in tool_summaries:
            tool_summaries[tool] = {
                "count": 0,
                "latest_date": None,  # Use None instead of empty string
                "avg_score": 0.0,
                "scores": [],
            }

        tool_summaries[tool]["count"] += 1
        tool_summaries[tool]["scores"].append(conv.get("relevance_score", 0.0))

        # Handle both string and integer timestamps
        current_date = conv.get("created_at")
        if current_date is not None:
            latest_date = tool_summaries[tool]["latest_date"]
            # Compare timestamps properly - both None, both strings, or both numbers
            if latest_date is None or (
                type(current_date) == type(latest_date) and current_date > latest_date
            ):
                tool_summaries[tool]["latest_date"] = current_date

    # Calculate averages and clean up
    for tool_data in tool_summaries.values():
        if tool_data["scores"]:
            tool_data["avg_score"] = round(
                sum(tool_data["scores"]) / len(tool_data["scores"]), 2
            )
        del tool_data["scores"]  # Remove raw scores

        # Convert None to empty string for JSON serialization
        if tool_data["latest_date"] is None:
            tool_data["latest_date"] = ""

    return {
        "summary_mode": True,
        "reason": "Response size exceeded limit, returning summary",
        "total_conversations": len(conversations),
        "tool_summaries": tool_summaries,
        "available_tools": original_response.get("available_tools", []),
        "processing_time": original_response.get("processing_time", 0.0),
        "optimization_applied": True,
    }


def handle_recall_conversations(
    fast_mode: bool = DEFAULT_FAST_MODE,
    days_lookback: int = CONVERSATION_DEFAULT_LOOKBACK_DAYS,
    limit: int = CONVERSATION_DEFAULT_LIMIT,
    min_score: float = CONVERSATION_DEFAULT_MIN_SCORE,
    conversation_types: Optional[List[str]] = None,
    tools: Optional[List[str]] = None,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Cross-platform conversation recall that aggregates results from all available tools.

    This function detects available tools and combines their conversation data
    into a unified format for comprehensive context analysis.

    Args:
        fast_mode: Use fast extraction vs comprehensive analysis
        days_lookback: Number of days to look back for conversations
        limit: Maximum number of conversations to return per tool
        min_score: Minimum relevance score threshold
        conversation_types: Filter by conversation types
        tools: Filter by specific agentic tools (e.g. ["windsurf", "cursor"])
        project_root: Project root directory for context generation

    Returns:
        Dict containing aggregated conversation data from all detected tools

    Note:
        This function automatically detects and processes conversations from multiple tools
        ({', '.join(SUPPORTED_AGENTIC_TOOLS)}, etc.) for comprehensive conversation context.
    """
    import time

    start_time = time.time()

    try:
        # Use provided project root, fallback to cwd
        context_project_root = project_root or Path.cwd()

        # Generate context keywords for relevance analysis
        context_keywords = generate_shared_context_keywords(context_project_root)
        log_debug(f"Generated context keywords: {context_keywords[:5]}...")

        # Detect available tools
        available_tools = _detect_available_agentic_tools()

        # Filter by requested tools if specified
        if tools:
            # Validate requested tools are supported
            invalid_tools = [
                tool for tool in tools if tool not in SUPPORTED_AGENTIC_TOOLS
            ]
            if invalid_tools:
                log_info(
                    f"Invalid tools requested: {invalid_tools}. Supported tools: {SUPPORTED_AGENTIC_TOOLS}"
                )

            # Filter to only include requested tools that are available
            available_tools = [tool for tool in available_tools if tool in tools]
            log_info(f"Filtered to requested tools: {available_tools}")

        if not available_tools:
            response = _create_no_tools_response(
                context_keywords,
                "recall",
                time.time() - start_time,
                fast_mode=fast_mode,
                days_lookback=days_lookback,
                limit=limit,
                min_score=min_score,
                conversation_types=conversation_types,
                tools=tools,
            )
            log_info("No tools detected for conversation recall")
            return AccessValidator.create_success_response(
                json.dumps(_convert_paths_for_json(response), indent=2)
            )

        log_info(
            f"Found {len(available_tools)} available tools: {', '.join(available_tools)}"
        )

        # Collect conversations from all available tools
        all_conversations = []
        tool_results = {}

        for tool_name in available_tools:
            try:
                result = _process_agentic_tool_conversations(
                    tool_name,
                    "recall",
                    context_keywords,
                    project_root=context_project_root,
                    fast_mode=fast_mode,
                    days_lookback=days_lookback,
                    limit=limit,
                    min_score=min_score,
                    conversation_types=conversation_types,
                )

                if result and "conversations" in result:
                    all_conversations.extend(result["conversations"])
                    log_info(
                        f"Retrieved {len(result['conversations'])} conversations "
                        f"from {tool_name}",
                    )

                tool_results[tool_name] = result

            except Exception as e:
                log_error(e, f"retrieving conversations from {tool_name}")
                tool_results[tool_name] = {"error": str(e)}

        processing_time = time.time() - start_time

        # Return unified response with size optimization
        response = {
            "available_tools": available_tools,
            "tool_results": tool_results,
            "conversations": all_conversations,
            "total_conversations": len(all_conversations),
            "context_keywords": context_keywords[
                :TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS
            ],
            "fast_mode": fast_mode,
            "days_lookback": days_lookback,
            "min_score": min_score,
            "limit": limit,
            "conversation_types": conversation_types or [],
            "tools": tools or [],
            "processing_time": processing_time,
        }

        # Check and optimize response size
        response = _check_response_size_and_optimize(response)

        log_info(
            f"Recalled {len(all_conversations)} total conversations "
            f"from {len(available_tools)} tools in {processing_time:.2f}s"
        )

        return AccessValidator.create_success_response(
            json.dumps(_convert_paths_for_json(response), indent=2)
        )

    except Exception as e:
        processing_time = time.time() - start_time
        log_error(e, "handling recall conversations")
        response = _create_no_tools_response(
            [],
            "recall",
            processing_time,
            fast_mode=fast_mode,
            days_lookback=days_lookback,
            limit=limit,
            min_score=min_score,
            conversation_types=conversation_types,
            tools=tools,
        )
        return AccessValidator.create_success_response(
            json.dumps(_convert_paths_for_json(response), indent=2)
        )


def handle_search_conversations(
    query: str,
    days_lookback: int = CONVERSATION_DEFAULT_LOOKBACK_DAYS,
    include_content: bool = False,
    limit: int = CONVERSATION_DEFAULT_LIMIT,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Cross-platform conversation search that queries all available tools.

    This function searches conversation history across multiple tools and
    returns unified results with consistent formatting.

    Args:
        query: Search query string
        days_lookback: Number of days to search back (0 for all time)
        include_content: Whether to include conversation content in results
        limit: Maximum number of results to return per tool
        project_root: Project root directory for context generation

    Returns:
        Dict containing search results from all detected tools

    Note:
        Automatically searches across multiple tools
        ({', '.join(SUPPORTED_AGENTIC_TOOLS)}, etc.) for comprehensive results.
    """
    import time

    start_time = time.time()

    try:
        # Use provided project root, fallback to cwd
        context_project_root = project_root or Path.cwd()

        # Generate context keywords for the search
        context_keywords = [query] + generate_shared_context_keywords(
            context_project_root
        )
        log_debug(f"Search context keywords: {context_keywords[:5]}...")

        # Detect available tools
        available_tools = _detect_available_agentic_tools()

        if not available_tools:
            response = _create_no_tools_response(
                context_keywords,
                "search",
                time.time() - start_time,
                query=query,
                days_lookback=days_lookback,
                include_content=include_content,
                limit=limit,
            )
            response["query"] = query
            log_info("No tools detected for conversation search")
            return AccessValidator.create_success_response(
                json.dumps(_convert_paths_for_json(response), indent=2)
            )

        log_info(
            f"Searching {len(available_tools)} tools: {', '.join(available_tools)}"
        )

        # Search conversations from all available tools
        all_results = []
        tool_results = {}

        for tool_name in available_tools:
            try:
                result = _process_agentic_tool_conversations(
                    tool_name,
                    "search",
                    context_keywords,
                    project_root=context_project_root,
                    query=query,
                    days_lookback=days_lookback,
                    include_content=include_content,
                    limit=limit,
                )

                if result and "conversations" in result:
                    all_results.extend(result["conversations"])
                    log_info(
                        f"Found {len(result['conversations'])} results from {tool_name}",
                    )

                tool_results[tool_name] = result

            except Exception as e:
                log_error(e, f"searching conversations in {tool_name}")
                tool_results[tool_name] = {"error": str(e)}

        processing_time = time.time() - start_time

        # Return unified search results with size optimization
        response = {
            "available_tools": available_tools,
            "tool_results": tool_results,
            "conversations": all_results,
            "total_conversations": len(all_results),
            "query": query,
            "context_keywords": context_keywords[
                :TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS
            ],
            "days_lookback": days_lookback,
            "include_content": include_content,
            "limit": limit,
            "processing_time": processing_time,
        }

        # Check and optimize response size
        response = _check_response_size_and_optimize(response)

        log_info(
            f"Found {len(all_results)} total search results "
            f"from {len(available_tools)} tools in {processing_time:.2f}s"
        )

        return AccessValidator.create_success_response(
            json.dumps(_convert_paths_for_json(response), indent=2)
        )

    except Exception as e:
        processing_time = time.time() - start_time
        log_error(e, "handling search conversations")
        response = _create_no_tools_response(
            [],
            "search",
            processing_time,
            query=query,
            days_lookback=days_lookback,
            include_content=include_content,
            limit=limit,
        )
        response["query"] = query
        return AccessValidator.create_success_response(
            json.dumps(_convert_paths_for_json(response), indent=2)
        )


# Handler registry for different tools
AGENTIC_TOOL_HANDLERS = {
    "cursor": {
        "recall": cursor_recall_handler,
        "search": handle_query_cursor_conversations,
    },
    "claude-code": {
        "recall": claude_recall_handler,
        "search": handle_query_claude_conversations,
    },
    "windsurf": {
        "recall": windsurf_recall_handler,
        "search": handle_query_windsurf_conversations,
    },
}


# Tool definitions
TOOL_RECALL_CONVERSATIONS = {
    "name": "recall_conversations",
    "description": "Cross-platform conversation recall that aggregates results from all available tools (Cursor, Claude Code, etc.) for comprehensive context analysis.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "fast_mode": {
                "type": "boolean",
                "default": True,
                "description": "Use fast extraction vs comprehensive analysis",
            },
            "days_lookback": {
                "type": "integer",
                "minimum": 1,
                "maximum": 60,
                "default": 7,
                "description": "Number of days to look back for conversations",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "default": 20,
                "description": "Maximum number of conversations to return per tool",
            },
            "min_score": {
                "type": "number",
                "minimum": 0,
                "default": 2.0,
                "description": "Minimum relevance score threshold",
            },
            "conversation_types": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "architecture",
                        "debugging",
                        "problem_solving",
                        "technical",
                        "code_discussion",
                        "general",
                    ],
                },
                "description": "Filter by conversation types",
            },
            "tools": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        AGENTIC_TOOL_CURSOR,
                        AGENTIC_TOOL_CLAUDE_CODE,
                        AGENTIC_TOOL_WINDSURF,
                    ],
                },
                "description": "Filter by specific agentic tools",
            },
        },
        "required": [],
    },
    "annotations": {
        "title": "Recall Conversations from All Tools",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}

TOOL_SEARCH_CONVERSATIONS = {
    "name": "search_conversations",
    "description": "Cross-platform conversation search that queries all available tools (Cursor, Claude Code, etc.) for comprehensive results.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query string",
            },
            "days_lookback": {
                "type": "integer",
                "minimum": 0,
                "maximum": 365,
                "default": 30,
                "description": "Number of days to search back (0 for all time)",
            },
            "include_content": {
                "type": "boolean",
                "default": False,
                "description": "Whether to include conversation content in results",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "default": 20,
                "description": "Maximum number of results to return per tool",
            },
        },
        "required": ["query"],
    },
    "annotations": {
        "title": "Search Conversations Across All Tools",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}


def handle_recall_conversations_wrapper(
    arguments: Dict[str, Any], project_root: Path, **kwargs
) -> Dict[str, Any]:
    """Wrapper function to match the expected handler signature."""
    return handle_recall_conversations(project_root=project_root, **arguments)


def handle_search_conversations_wrapper(
    arguments: Dict[str, Any], project_root: Path, **kwargs
) -> Dict[str, Any]:
    """Wrapper function to match the expected handler signature."""
    return handle_search_conversations(project_root=project_root, **arguments)


CONVERSATION_AGGREGATOR_TOOL_HANDLERS = {
    "recall_conversations": handle_recall_conversations_wrapper,
    "search_conversations": handle_search_conversations_wrapper,
}

CONVERSATION_AGGREGATOR_TOOL_DEFINITIONS = [
    TOOL_RECALL_CONVERSATIONS,
    TOOL_SEARCH_CONVERSATIONS,
]
