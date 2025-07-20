"""
Conversation aggregation tool for Gandalf MCP Server.

This module provides the primary conversation interface that automatically detects
and aggregates conversation data from all available tools (Cursor, Claude Code, etc.)
for comprehensive context analysis.
"""

import json
from pathlib import Path
from typing import Any

from src.config.constants.agentic import (
    AGENTIC_TOOL_CLAUDE_CODE,
    AGENTIC_TOOL_CURSOR,
    AGENTIC_TOOL_WINDSURF,
    SUPPORTED_AGENTIC_TOOLS,
)
from src.config.constants.context import (
    TOKEN_OPTIMIZATION_CONTENT_TRUNCATION_LIMIT,
    TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS,
    TOKEN_OPTIMIZATION_MAX_RESPONSE_SIZE,
    TOKEN_OPTIMIZATION_MAX_TOOL_RESULT_FIELDS,
    TOKEN_OPTIMIZATION_SUMMARY_MODE_THRESHOLD,
)
from src.config.constants.conversation import (
    CONVERSATION_DEFAULT_FAST_MODE,
    CONVERSATION_DEFAULT_LIMIT,
    CONVERSATION_DEFAULT_LOOKBACK_DAYS,
    CONVERSATION_DEFAULT_MIN_SCORE,
    CONVERSATION_ID_DISPLAY_LIMIT,
    CONVERSATION_MAX_LIMIT,
    CONVERSATION_MAX_LOOKBACK_DAYS,
    CONVERSATION_SNIPPET_DISPLAY_LIMIT,
    CONVERSATION_TITLE_DISPLAY_LIMIT,
)
from src.core.conversation_analysis import generate_shared_context_keywords
from src.core.conversation_filtering import apply_conversation_filtering
from src.core.database_scanner import get_available_agentic_tools
from src.core.registry import get_registered_agentic_tools
from src.tool_calls.claude_code.recall import (
    create_lightweight_conversation as claude_create_lightweight,
)
from src.tool_calls.claude_code.recall import (
    handle_recall_claude_conversations as claude_recall_handler,
)
from src.tool_calls.claude_code.recall import (
    standardize_conversation as claude_standardize_conversation,
)
from src.tool_calls.cursor.recall import (
    create_lightweight_conversation as cursor_create_lightweight,
)
from src.tool_calls.cursor.recall import (
    handle_recall_cursor_conversations as cursor_recall_handler,
)
from src.tool_calls.cursor.recall import (
    standardize_conversation as cursor_standardize_conversation,
)
from src.tool_calls.windsurf.recall import (
    create_lightweight_conversation as windsurf_create_lightweight,
)
from src.tool_calls.windsurf.recall import (
    handle_recall_windsurf_conversations as windsurf_recall_handler,
)
from src.tool_calls.windsurf.recall import (
    standardize_conversation as windsurf_standardize_conversation,
)
from src.utils.access_control import AccessValidator
from src.utils.common import log_debug, log_error, log_info


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
    conversation: dict[str, Any], source_tool: str
) -> dict[str, Any]:
    """Create lightweight conversation format for token optimization."""
    if source_tool == AGENTIC_TOOL_CURSOR:
        return cursor_create_lightweight(conversation)
    elif source_tool == AGENTIC_TOOL_CLAUDE_CODE:
        return claude_create_lightweight(conversation)
    elif source_tool == AGENTIC_TOOL_WINDSURF:
        return windsurf_create_lightweight(conversation)
    else:
        # Generic fallback
        return {
            "id": conversation.get("id", "")[:CONVERSATION_ID_DISPLAY_LIMIT],
            "title": _truncate_string_field(
                conversation.get("title", ""),
                CONVERSATION_TITLE_DISPLAY_LIMIT,
            ),
            "source_tool": source_tool,
            "message_count": conversation.get("message_count", 0),
            "relevance_score": round(conversation.get("relevance_score", 0.0), 2),
            "created_at": conversation.get("created_at", ""),
            "snippet": _truncate_string_field(
                conversation.get("snippet", ""),
                CONVERSATION_SNIPPET_DISPLAY_LIMIT,
            ),
        }


def _standardize_conversation_format(
    conversation: dict[str, Any],
    source_tool: str,
    context_keywords: list[str],
    lightweight: bool = False,
) -> dict[str, Any]:
    """Standardize conversation format across different tools."""
    if source_tool == AGENTIC_TOOL_CURSOR:
        return cursor_standardize_conversation(
            conversation, context_keywords, lightweight
        )
    elif source_tool == AGENTIC_TOOL_CLAUDE_CODE:
        return claude_standardize_conversation(
            conversation, context_keywords, lightweight
        )
    elif source_tool == AGENTIC_TOOL_WINDSURF:
        return windsurf_standardize_conversation(
            conversation, context_keywords, lightweight
        )
    else:
        # generic fallback
        try:
            if lightweight:
                return _create_lightweight_conversation(conversation, source_tool)

            standardized = {
                "id": conversation.get("id", "")[:CONVERSATION_ID_DISPLAY_LIMIT],
                "title": _truncate_string_field(
                    conversation.get("title", ""),
                    CONVERSATION_TITLE_DISPLAY_LIMIT,
                ),
                "source_tool": source_tool,
                "message_count": conversation.get("message_count", 0),
                "relevance_score": round(conversation.get("relevance_score", 0.0), 2),
                "created_at": conversation.get("created_at", ""),
                "snippet": _truncate_string_field(
                    conversation.get("snippet", ""),
                    CONVERSATION_SNIPPET_DISPLAY_LIMIT,
                ),
                "context_keywords": context_keywords[
                    :TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS
                ],
                "keyword_matches": conversation.get("keyword_matches", []),
            }
            return standardized
        except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
            log_error(e, f"standardizing conversation from {source_tool}")
            return {}


def _detect_available_agentic_tools() -> list[str]:
    """Detect available tools using the database scanner for comprehensive detection."""
    try:
        # Use database scanner for better tool detection
        available_tools = get_available_agentic_tools(silent=True)
        log_info(f"Found available tools via database scanner: {available_tools}")

        # Also check for tools with accessible databases even if no conversations
        from src.core.database_scanner import DatabaseScanner

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

    except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
        log_error(e, "detecting available tools")
        # Final fallback to registry
        try:
            registered_tools = get_registered_agentic_tools()
            log_info(f"Final fallback to registered tools: {registered_tools}")
            return registered_tools
        except (
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
            OSError,
        ) as registry_error:
            log_error(registry_error, "detecting tools from registry")
            return []


def _process_agentic_tool_conversations(
    tool_name: str,
    context_keywords: list[str],
    **kwargs,
) -> dict[str, Any]:
    """Process conversations from a single tool with standardized error handling."""
    try:
        handler = AGENTIC_TOOL_HANDLERS.get(tool_name, {}).get("recall")

        if not handler:
            log_debug(f"No recall handler found for {tool_name}")
            return {}

        log_info(f"Calling recall handler for {tool_name}")

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
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
        log_error(e, f"processing conversations from {tool_name}")
        return {"error": str(e)}


def _create_no_tools_response(
    context_keywords: list[str],
    processing_time: float = 0.0,
    **kwargs,
) -> dict[str, Any]:
    """Create standardized response when no tools are detected."""
    response = {
        "available_tools": [],
        "context_keywords": context_keywords,
        "message": "No compatible tools detected",
        "conversations": [],
        "total_conversations": 0,
        "processing_time": processing_time,
        "tool_results": {},
        "fast_mode": kwargs.get("fast_mode", CONVERSATION_DEFAULT_FAST_MODE),
        "days_lookback": kwargs.get(
            "days_lookback", CONVERSATION_DEFAULT_LOOKBACK_DAYS
        ),
        "min_score": kwargs.get("min_score", CONVERSATION_DEFAULT_MIN_SCORE),
        "limit": kwargs.get("limit", CONVERSATION_DEFAULT_LIMIT),
        "conversation_types": kwargs.get("conversation_types", []),
        "tools": kwargs.get("tools", []),
        "search_query": kwargs.get("search_query"),
        "tags": kwargs.get("tags"),
    }

    return response


def _check_response_size_and_optimize(
    response: dict[str, Any],
) -> dict[str, Any]:
    """Check response size and optimize if needed."""
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


def _create_summary_response(
    original_response: dict[str, Any],
) -> dict[str, Any]:
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
                isinstance(current_date, type(latest_date))
                and current_date > latest_date
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
    fast_mode: bool = CONVERSATION_DEFAULT_FAST_MODE,
    days_lookback: int = CONVERSATION_DEFAULT_LOOKBACK_DAYS,
    limit: int = CONVERSATION_DEFAULT_LIMIT,
    min_score: float = CONVERSATION_DEFAULT_MIN_SCORE,
    conversation_types: list[str] | None = None,
    tools: list[str] | None = None,
    project_root: Path | None = None,
    user_prompt: str | None = None,
    search_query: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Cross-platform conversation recall that aggregates results from all available tools."""
    import time

    start_time = time.time()

    try:
        # Use provided project root, fallback to cwd
        context_project_root = project_root or Path.cwd()

        has_search_query = bool(search_query or tags)

        # Generate context keywords for relevance analysis
        base_context_keywords = generate_shared_context_keywords(context_project_root)

        # Enhance keywords with search terms if provided
        if has_search_query:
            search_keywords = []
            if search_query:
                search_keywords.append(search_query)
            if tags:
                search_keywords.extend(tags)
            context_keywords = search_keywords + base_context_keywords
            log_info(f"Recall with query terms: {search_keywords}")
        else:
            context_keywords = base_context_keywords
            log_info("Returning contextually relevant recent conversations")

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
                    f"Invalid tools requested: {invalid_tools}. "
                    f"Supported tools: {SUPPORTED_AGENTIC_TOOLS}"
                )

            # Filter to only include requested tools that are available
            available_tools = [tool for tool in available_tools if tool in tools]
            log_info(f"Filtered to requested tools: {available_tools}")

        if not available_tools:
            response = _create_no_tools_response(
                context_keywords,
                time.time() - start_time,
                fast_mode=fast_mode,
                days_lookback=days_lookback,
                limit=limit,
                min_score=min_score,
                conversation_types=conversation_types,
                tools=tools,
                user_prompt=user_prompt,
                search_query=search_query,
                tags=tags,
            )
            log_info("No tools detected for conversation recall")
            return AccessValidator.create_success_response(
                json.dumps(_convert_paths_for_json(response), indent=2)
            )

        log_info(
            f"Found {len(available_tools)} available tools: "
            f"{', '.join(available_tools)}"
        )

        # Stream and filter conversations from all available tools (memory efficient)
        filtered_conversations = []
        tool_results = {}
        total_processed = 0

        for tool_name in available_tools:
            try:
                tool_kwargs = {
                    "project_root": context_project_root,
                    "fast_mode": fast_mode,
                    "days_lookback": days_lookback,
                    "limit": limit * 2,  # Get more initially for better filtering
                    "min_score": min_score,
                    "conversation_types": conversation_types,
                }

                if has_search_query and search_query:
                    # For query-based recall, pass the query
                    tool_kwargs["query"] = search_query
                    tool_kwargs["include_content"] = True

                result = _process_agentic_tool_conversations(
                    tool_name, context_keywords, **tool_kwargs
                )

                if result and "conversations" in result:
                    tool_conversations = result["conversations"]
                    total_processed += len(tool_conversations)

                    # Apply early filtering to prevent memory buildup
                    for conv in tool_conversations:
                        # Basic relevance filtering
                        if conv.get("relevance_score", 0) >= min_score:
                            filtered_conversations.append(conv)

                        # Break early if we have enough high-quality conversations
                        if len(filtered_conversations) >= limit * 3:
                            break

                    log_info(
                        f"Retrieved {len(tool_conversations)} conversations from {tool_name}, "
                        f"kept {len([c for c in tool_conversations if c.get('relevance_score', 0) >= min_score])}"
                    )

                tool_results[tool_name] = result

            except (
                ValueError,
                TypeError,
                KeyError,
                AttributeError,
                OSError,
            ) as e:
                log_error(e, f"retrieving conversations from {tool_name}")
                tool_results[tool_name] = {"error": str(e)}

        processing_time = time.time() - start_time

        # Apply intelligent filtering to pre-filtered conversations
        final_conversations, filtering_metadata = apply_conversation_filtering(
            filtered_conversations,
            context_project_root,
            limit,
            user_prompt,
        )

        # Determine response optimization
        total_size_estimate = len(json.dumps(final_conversations))
        use_summary_mode = total_size_estimate > TOKEN_OPTIMIZATION_MAX_RESPONSE_SIZE

        # Create comprehensive response
        response = {
            "available_tools": available_tools,
            "conversations": final_conversations,
            "total_conversations": len(final_conversations),
            "context_keywords": context_keywords[
                :TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS
            ],
            "search_query": search_query,
            "tags": tags,
            "parameters": {
                "fast_mode": fast_mode,
                "days_lookback": days_lookback,
                "limit": limit,
                "min_score": min_score,
                "conversation_types": conversation_types,
                "tools": tools,
                "user_prompt": user_prompt,
            },
            "processing_time": processing_time,
        }

        # Add tool results if not in summary mode
        if not use_summary_mode:
            response["tool_results"] = tool_results

        # Check and optimize response size
        response = _check_response_size_and_optimize(response)

        result_desc = "conversations"
        query_desc = f" for '{search_query}'" if search_query else ""
        log_info(
            f"Recalled {len(filtered_conversations)} total "
            f"{result_desc}{query_desc} from {len(available_tools)} tools "
            f"in {processing_time:.2f}s"
        )

        return AccessValidator.create_success_response(
            json.dumps(_convert_paths_for_json(response), indent=2)
        )

    except (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        OSError,
        json.JSONDecodeError,
    ) as e:
        processing_time = time.time() - start_time
        log_error(e, "handling recall conversations")
        response = _create_no_tools_response(
            [],
            processing_time,
            fast_mode=fast_mode,
            days_lookback=days_lookback,
            limit=limit,
            min_score=min_score,
            conversation_types=conversation_types,
            tools=tools,
            user_prompt=user_prompt,
            search_query=search_query,
            tags=tags,
        )
        return AccessValidator.create_success_response(
            json.dumps(_convert_paths_for_json(response), indent=2)
        )


def handle_recall_conversations_wrapper(
    arguments: dict[str, Any], project_root: Path, **kwargs
) -> dict[str, Any]:
    """Wrapper function to match the expected handler signature."""
    return handle_recall_conversations(project_root=project_root, **arguments)


# Tool definitions
TOOL_RECALL_CONVERSATIONS = {
    "name": "recall_conversations",
    "description": (
        "Cross-platform conversation recall that aggregates results from all "
        "available tools (Cursor, Claude Code, etc.) for comprehensive context "
        "analysis with enhanced conversation filtering."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "fast_mode": {
                "type": "boolean",
                "default": CONVERSATION_DEFAULT_FAST_MODE,
                "description": "Use fast extraction vs comprehensive analysis",
            },
            "days_lookback": {
                "type": "integer",
                "minimum": 1,
                "maximum": CONVERSATION_MAX_LOOKBACK_DAYS,
                "default": CONVERSATION_DEFAULT_LOOKBACK_DAYS,
                "description": "Number of days to look back for conversations",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": CONVERSATION_MAX_LIMIT,
                "default": CONVERSATION_DEFAULT_LIMIT,
                "description": (
                    "Maximum number of conversations to return (used as "
                    "context limit for intelligent filtering)"
                ),
            },
            "min_score": {
                "type": "number",
                "minimum": 0,
                "default": CONVERSATION_DEFAULT_MIN_SCORE,
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
            "user_prompt": {
                "type": "string",
                "description": (
                    "Optional user prompt or context for dynamic keyword "
                    "extraction and enhanced relevance scoring"
                ),
            },
            "search_query": {
                "type": "string",
                "description": (
                    "Optional query to filter conversations for specific content"
                ),
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Optional list of tags/keywords to filter conversations"
                ),
            },
        },
        "required": [],
    },
    "annotations": {
        "title": "Intelligent Conversation Recall from All Tools",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}


CONVERSATION_AGGREGATOR_TOOL_HANDLERS = {
    "recall_conversations": handle_recall_conversations_wrapper,
}

CONVERSATION_AGGREGATOR_TOOL_DEFINITIONS = [
    TOOL_RECALL_CONVERSATIONS,
]


# Handler registry for different tools
AGENTIC_TOOL_HANDLERS = {
    "cursor": {
        "recall": cursor_recall_handler,
    },
    "claude-code": {
        "recall": claude_recall_handler,
    },
    "windsurf": {
        "recall": windsurf_recall_handler,
    },
}
