"""
Conversation aggregation tool for Gandalf MCP Server.

This module provides the primary conversation interface that automatically detects
and aggregates conversation data from all available tools (Cursor, Claude Code, etc.)
for comprehensive context analysis.
"""

import json
from pathlib import Path
from typing import Any

from src.config.constants.conversation import (
    CONVERSATION_DEFAULT_FAST_MODE,
    CONVERSATION_DEFAULT_LIMIT,
    CONVERSATION_DEFAULT_LOOKBACK_DAYS,
    CONVERSATION_DEFAULT_MIN_SCORE,
    CONVERSATION_MAX_LIMIT,
    CONVERSATION_MAX_LOOKBACK_DAYS,
)
from src.core.conversation_filtering import apply_conversation_filtering
from src.tool_calls.aggregation_utils import (
    create_error_response_for_aggregation,
    generate_context_keywords_for_project,
    log_aggregation_performance,
    validate_aggregation_arguments,
)
from src.tool_calls.context_optimization import (
    create_processing_strategy,
    optimize_context_keywords,
)
from src.tool_calls.response_formatting import (
    format_aggregated_response,
)
from src.tool_calls.tool_aggregation import (
    _create_no_tools_response,
    _detect_available_agentic_tools,
    _process_agentic_tool_conversations,
    aggregate_tool_results,
)
from src.utils.access_control import AccessValidator, create_mcp_tool_result
from src.utils.common import log_debug, log_error, log_info
from src.utils.performance import get_duration, start_timer


def handle_recall_conversations(
    project_root: Path | str | None = None,
    **arguments: Any,
) -> dict[str, Any]:
    """
    Cross-platform conversation recall with intelligent aggregation.

    Automatically detects and aggregates conversations from all available
    agentic tools (Cursor, Claude Code, Windsurf) with smart filtering.
    """
    start_time = start_timer()

    try:
        # Validate project root
        if not project_root:
            project_root = Path.cwd()
        elif not isinstance(project_root, Path):
            project_root = Path(project_root)

        # Validate and normalize arguments
        validated_args = validate_aggregation_arguments(arguments)

        log_info(
            f"Starting conversation recall: limit={validated_args['limit']}, "
            f"days_lookback={validated_args['days_lookback']}, "
            f"fast_mode={validated_args['fast_mode']}"
        )

        # Detect available agentic tools
        available_tools = _detect_available_agentic_tools()
        if not available_tools:
            log_info("No agentic tools detected")
            # Include validated parameters in the no-tools response
            no_tools_response = _create_no_tools_response()
            # Merge parameters into the response structure
            if "content" in no_tools_response:
                content_text = no_tools_response["content"][0]["text"]
                try:
                    parsed_content = json.loads(content_text)
                    # Add parameters to the response
                    enhanced_response = {**parsed_content, **validated_args}
                    no_tools_response["content"][0]["text"] = json.dumps(
                        enhanced_response, indent=2
                    )
                except json.JSONDecodeError:
                    # Fallback: create new structured response with parameters
                    enhanced_content = {
                        "message": content_text,
                        "status": "no_tools_available",
                        **validated_args,
                    }
                    no_tools_response["content"][0]["text"] = json.dumps(
                        enhanced_content, indent=2
                    )
            return no_tools_response

        log_info(f"Processing {len(available_tools)} tools: {available_tools}")

        # Generate context keywords
        context_keywords = generate_context_keywords_for_project(
            project_root,
            validated_args.get("user_prompt", ""),
            validated_args.get("search_query", ""),
        )

        # Optimize keywords for performance
        optimized_keywords = optimize_context_keywords(context_keywords)

        # Create processing strategy
        strategy = create_processing_strategy(
            available_tools,
            estimated_conversations=validated_args["limit"] * len(available_tools),
            parameters=validated_args,
        )

        log_debug(f"Processing strategy: {strategy}")

        # Process conversations from each tool
        tool_results = []
        for tool_name in available_tools:
            tool_start = start_timer()

            try:
                # Adjust arguments for tool-specific processing
                tool_args = validated_args.copy()
                if strategy.get("use_fast_mode"):
                    tool_args["fast_mode"] = True

                result = _process_agentic_tool_conversations(
                    tool_name, tool_args, project_root
                )

                tool_results.append((tool_name, result))

                tool_duration = get_duration(tool_start)
                log_debug(f"Processed {tool_name} in {tool_duration:.2f}s")

            except Exception as e:
                log_error(e, f"Failed to process {tool_name}")
                error_result = AccessValidator.create_error_response(
                    f"Failed to process {tool_name}: {str(e)}"
                )
                tool_results.append((tool_name, error_result))

        # Aggregate results from all tools
        aggregated_conversations, processing_stats = aggregate_tool_results(
            tool_results, validated_args["limit"]
        )

        if not aggregated_conversations:
            log_info("No conversations found across all tools")
            return _create_empty_response(
                available_tools, processing_stats, optimized_keywords, validated_args
            )

        # Apply final filtering if not in fast mode
        if not validated_args["fast_mode"]:
            filtered_conversations, filtering_metadata = apply_conversation_filtering(
                aggregated_conversations,
                project_root,
                requested_limit=validated_args["limit"],
            )
        else:
            filtered_conversations = aggregated_conversations[: validated_args["limit"]]

        # Format final response
        response_data = format_aggregated_response(
            filtered_conversations,
            processing_stats,
            optimized_keywords,
            validated_args,
        )

        # Log performance
        total_duration = get_duration(start_time)
        log_aggregation_performance(
            "Conversation aggregation",
            start_time,
            len(available_tools),
            len(filtered_conversations),
        )

        # Create structured response
        structured_data = {
            "summary": response_data["summary"],
            "conversations": filtered_conversations,
            "tools": available_tools,
            "keywords": optimized_keywords[:10],
            "strategy": strategy,
            "status": "aggregation_complete",
        }

        content_text = json.dumps(response_data, indent=2)
        return create_mcp_tool_result(content_text, structured_data)

    except Exception as e:
        total_duration = get_duration(start_time)
        log_error(e, "Conversation aggregation failed")

        return create_error_response_for_aggregation(
            f"Aggregation failed: {str(e)}",
            available_tools if "available_tools" in locals() else [],
            total_duration,
        )


def _create_empty_response(
    available_tools: list[str],
    processing_stats: dict[str, Any],
    context_keywords: list[str],
    parameters: dict[str, Any],
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

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(structured_data, indent=2),
            }
        ]
    }


def handle_recall_conversations_wrapper(
    arguments: dict[str, Any], project_root: Path, **kwargs: Any
) -> dict[str, Any]:
    """Wrapper function to match the expected handler signature."""
    return handle_recall_conversations(project_root=project_root, **arguments)


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
