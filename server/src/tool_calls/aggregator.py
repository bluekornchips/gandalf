"""
Conversation aggregation tool for Gandalf MCP Server.

This module provides the primary conversation interface that automatically detects
and aggregates conversation data from all available tools (Cursor, Claude Code, etc.)
for comprehensive context analysis.
"""

import json
from pathlib import Path
from typing import Any

from src.config.conversation_config import (
    CONVERSATION_DEFAULT_FAST_MODE,
    CONVERSATION_DEFAULT_LIMIT,
    CONVERSATION_DEFAULT_LOOKBACK_DAYS,
    CONVERSATION_DEFAULT_MIN_SCORE,
    CONVERSATION_MAX_LIMIT,
    CONVERSATION_MAX_LOOKBACK_DAYS,
)
from src.core.conversation_filtering import apply_conversation_filtering
from src.utils.access_control import create_mcp_tool_result
from src.utils.common import format_json_response, log_debug, log_error, log_info


def handle_recall_conversations(
    project_root: Path | str | None = None,
    client_info: dict[str, Any] | None = None,
    **arguments: Any,
) -> dict[str, Any]:
    """
    Cross-platform conversation recall that aggregates results from all available tools.

    This function detects available tools and combines their conversation data
    into a unified format for comprehensive context analysis with intelligent filtering.
    """
    import time

    from src.config.conversation_config import (
        SUPPORTED_AGENTIC_TOOLS,
        TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS,
        TOKEN_OPTIMIZATION_MAX_RESPONSE_SIZE,
    )
    from src.core.conversation_analysis import generate_shared_context_keywords
    from src.tool_calls.response_formatting import (
        _check_response_size_and_optimize,
        _convert_paths_for_json,
    )
    from src.tool_calls.tool_aggregation import (
        _create_no_tools_response,
        _process_agentic_tool_conversations,
    )

    start_time = time.time()

    try:
        # Use provided project root, fallback to cwd
        if not project_root:
            project_root = Path.cwd()
        elif not isinstance(project_root, Path):
            project_root = Path(project_root)
        context_project_root = project_root

        # Extract arguments with defaults
        fast_mode = arguments.get("fast_mode", CONVERSATION_DEFAULT_FAST_MODE)
        days_lookback = arguments.get(
            "days_lookback", CONVERSATION_DEFAULT_LOOKBACK_DAYS
        )
        limit = arguments.get("limit", CONVERSATION_DEFAULT_LIMIT)
        min_score = arguments.get("min_relevance_score", CONVERSATION_DEFAULT_MIN_SCORE)
        conversation_types = arguments.get("conversation_types")
        tools = arguments.get("tools")
        user_prompt = arguments.get("user_prompt")
        search_query = arguments.get("search_query")
        tags = arguments.get("tags")

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
        from src.tool_calls.tool_aggregation import _detect_available_agentic_tools

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
            filtered_tools = [tool for tool in available_tools if tool in tools]
            available_tools = filtered_tools
            log_info(f"Filtered to requested tools: {available_tools}")

        if not available_tools:
            response = _create_no_tools_response()
            log_info("No tools detected for conversation recall")

            # Create MCP 2025-06-18 compliant response with structured content
            # Add parameters to response for no-tools case
            response["days_lookback"] = days_lookback
            response["limit"] = limit
            response["min_relevance_score"] = min_score
            response["search_query"] = search_query
            response["tags"] = tags

            response_data = _convert_paths_for_json(response)
            response_text = format_json_response(response_data)

            # Structure the data for better AI consumption
            # Ensure response_data is a dict for safe .get() operations
            if not isinstance(response_data, dict):
                response_data = {}

            structured_data = {
                "summary": {
                    "total_conversations": 0,
                    "total_conversations_found": 0,
                    "available_tools": [],
                    "processing_time": response_data.get("processing_time", 0.0),
                    "tools_processed": 0,
                },
                "conversations": [],
                "context": {
                    "keywords": response_data.get("context_keywords", []),
                    "filters_applied": {
                        "fast_mode": response_data.get("fast_mode"),
                        "days_lookback": response_data.get("days_lookback"),
                        "min_score": response_data.get("min_score"),
                        "limit": response_data.get("limit"),
                    },
                },
                "tool_results": {},
                "status": "no_tools_detected",
            }

            # Return MCP 2025-06-18 format with both text and structured content
            mcp_result = create_mcp_tool_result(
                response_text, structured_data, client_info=client_info
            )
            return mcp_result

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
                # Prepare arguments dict for the tool
                tool_arguments = {
                    "fast_mode": fast_mode,
                    "days_lookback": days_lookback,
                    "limit": limit * 2,  # Get more initially for better filtering
                    "min_score": min_score,
                    "conversation_types": conversation_types,
                }

                if has_search_query and search_query:
                    tool_arguments["query"] = search_query
                    tool_arguments["include_content"] = True

                result = _process_agentic_tool_conversations(
                    tool_name, tool_arguments, context_project_root
                )

                # Parse MCP response to extract conversation data
                tool_conversations = []
                if (
                    result
                    and "content" in result
                    and isinstance(result["content"], list)
                ):
                    try:
                        for content_item in result["content"]:
                            if content_item.get("type") == "text":
                                tool_data = json.loads(content_item["text"])
                                tool_conversations = tool_data.get("conversations", [])
                                break
                    except (json.JSONDecodeError, KeyError, TypeError):
                        log_debug(f"Failed to parse {tool_name} response")

                if tool_conversations:
                    total_processed += len(tool_conversations)

                    # Apply early filtering to prevent memory buildup
                    for conv in tool_conversations:
                        # Basic relevance filtering
                        if (
                            conv.get("relevance_score", 0) >= min_score
                            or conv.get("relevance_score", 0) == 0
                        ):
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

        # Sort conversations by relevance score to ensure proper mixing of results from all tools
        filtered_conversations.sort(
            key=lambda x: x.get("relevance_score", 0), reverse=True
        )

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
        conversations_data = response.get("conversations", [])
        summary_data = {
            "total_conversations": response.get("total_conversations", 0),
            "available_tools": response.get("available_tools", []),
            "processing_time": response.get("processing_time", 0.0),
        }
        optimized_conversations, optimized_summary, was_optimized = (
            _check_response_size_and_optimize(conversations_data, summary_data)
        )

        # Update response with optimized data
        response["conversations"] = optimized_conversations
        response["total_conversations"] = optimized_summary.get(
            "total_conversations", 0
        )
        response["was_optimized"] = was_optimized

        result_desc = "conversations"
        query_desc = f" for '{search_query}'" if search_query else ""
        log_info(
            f"Recalled {len(filtered_conversations)} total "
            f"{result_desc}{query_desc} from {len(available_tools)} tools "
            f"in {processing_time:.2f}s"
        )

        response_data = _convert_paths_for_json(response)
        response_text = format_json_response(response_data)

        # Ensure response_data is a dict for safe .get() operations
        if not isinstance(response_data, dict):
            response_data = {}

        structured_data = {
            "summary": {
                "total_conversations": response_data.get("total_conversations", 0),
                "total_conversations_found": total_processed,  # Use the actual total found from all tools
                "available_tools": response_data.get("available_tools", []),
                "processing_time": response_data.get("processing_time", 0.0),
                "tools_processed": len(response_data.get("available_tools", [])),
            },
            "conversations": response_data.get("conversations", []),
            "tools": response_data.get(
                "available_tools", []
            ),  # Add alias for compatibility
            "context": {
                "keywords": response_data.get("context_keywords", []),
                "filters_applied": {
                    "fast_mode": response_data.get("fast_mode"),
                    "days_lookback": response_data.get("days_lookback"),
                    "min_score": response_data.get("min_score"),
                    "limit": response_data.get("limit"),
                },
            },
            "tool_results": response_data.get("tool_results", {}),
            "status": "recall_complete",
        }

        # Return MCP 2025-06-18 format with both text and structured content
        mcp_result = create_mcp_tool_result(
            response_text, structured_data, client_info=client_info
        )
        return mcp_result

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
        response = _create_no_tools_response()

        # Create MCP 2025-06-18 compliant error response
        response_data = _convert_paths_for_json(response)
        response_text = format_json_response(response_data)

        # Ensure response_data is a dict for safe .get() operations
        if not isinstance(response_data, dict):
            response_data = {}

        # Structure the error data
        structured_data = {
            "summary": {
                "total_conversations": 0,
                "total_conversations_found": 0,
                "available_tools": [],
                "processing_time": processing_time,
                "tools_processed": 0,
            },
            "conversations": [],
            "tools": [],  # Add alias for compatibility
            "context": {
                "keywords": [],
                "filters_applied": {
                    "fast_mode": response_data.get("fast_mode"),
                    "days_lookback": response_data.get("days_lookback"),
                    "min_score": response_data.get("min_score"),
                    "limit": response_data.get("limit"),
                },
            },
            "tool_results": {},
            "status": "error_occurred",
        }

        # Return MCP 2025-06-18 format
        mcp_result = create_mcp_tool_result(
            response_text, structured_data, client_info=client_info
        )
        return mcp_result


def _create_empty_response(
    available_tools: list[str],
    processing_stats: dict[str, Any],
    context_keywords: list[str],
    parameters: dict[str, Any],
    client_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create response when no conversations are found."""
    response_data = {
        "summary": {
            "total_conversations_found": 0,
            "conversations_returned": 0,
            "success_rate_percent": 0.0,
            "processing_time_seconds": processing_stats.get("total_processing_time", 0),
            "tools_processed": len(available_tools),
            "tools_with_data": [],
            "context_keywords": context_keywords[:10],
        },
        "conversations": [],
        "message": "No conversations found matching the criteria",
        "suggestion": "Try adjusting the days_lookback parameter or min_relevance_score",
        "status": "no_conversations_found",
    }

    structured_data = {
        "summary": response_data["summary"],
        "conversations": [],  # Add missing conversations field for consistency
        "tools": available_tools,
        "status": "no_conversations_found",
    }

    content_text = format_json_response(structured_data)
    return create_mcp_tool_result(content_text, None, client_info=client_info)


# Re-export functions from aggregator_backup for test compatibility


def handle_recall_conversations_wrapper(
    arguments: dict[str, Any], project_root: Path, **kwargs: Any
) -> dict[str, Any]:
    """Wrapper function to match the expected handler signature."""
    client_info = kwargs.get("client_info")
    return handle_recall_conversations(
        project_root=project_root, client_info=client_info, **arguments
    )


# Tool definitions
TOOL_RECALL_CONVERSATIONS = {
    "name": "recall_conversations",
    "title": "Cross-Platform Conversation Recall",
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
            "min_relevance_score": {
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
            "include_analysis": {
                "type": "boolean",
                "default": False,
                "description": "Include detailed relevance analysis",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of tags/keywords to filter conversations",
            },
            "search_query": {
                "type": "string",
                "description": "Optional query to filter conversations for specific content",
            },
            "user_prompt": {
                "type": "string",
                "description": "Optional user prompt or context for dynamic keyword extraction",
            },
            "tools": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["cursor", "claude-code", "windsurf"],
                },
                "description": "Filter by specific agentic tools",
            },
        },
        "required": [],
    },
    "annotations": {
        "title": "Intelligent Multi-Tool Conversation Aggregation",
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
