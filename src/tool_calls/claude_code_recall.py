"""
Claude Code conversation recall and analysis.

This module provides intelligent conversation recall capabilities for Claude Code,
using the shared conversation analysis functionality for consistency with Cursor IDE.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from src.config.constants.conversations import (
    CONVERSATION_DEFAULT_RECENT_DAYS,
    CONVERSATION_MAX_LOOKBACK_DAYS,
    CONVERSATION_TEXT_EXTRACTION_LIMIT,
    CONVERSATION_TYPES,
)
from src.config.constants.system import (
    CONVERSATION_DEFAULT_LIMIT,
    CONVERSATION_DEFAULT_MIN_SCORE,
    CONVERSATION_MAX_LIMIT,
    CONVERSATION_SNIPPET_MAX_LENGTH,
)
from src.core.conversation_analysis import (
    analyze_session_relevance,
    extract_conversation_content,
    filter_conversations_by_date,
    generate_shared_context_keywords,
    sort_conversations_by_relevance,
)
from src.tool_calls.claude_code_query import ClaudeCodeQuery
from src.utils.access_control import AccessValidator
from src.utils.common import log_error, log_info
from src.utils.performance import get_duration, start_timer


def handle_recall_claude_conversations(
    arguments: Dict[str, Any], project_root: Path, **kwargs
) -> Dict[str, Any]:
    """Recall and analyze Claude Code conversations for context."""
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
        conversation_types = arguments.get("conversation_types", [])
        min_score = arguments.get("min_score", CONVERSATION_DEFAULT_MIN_SCORE)

        # Validate parameters
        days_lookback = min(days_lookback, CONVERSATION_MAX_LOOKBACK_DAYS)

        timer = start_timer()

        # Generate context keywords using shared functionality
        context_keywords = generate_shared_context_keywords(project_root)
        log_info(f"Generated {len(context_keywords)} context keywords")

        # Initialize query tool
        query_tool = ClaudeCodeQuery(silent=True)

        # Get conversations - for Claude Code, we want to search by user home, not specific project
        log_info("Querying Claude Code conversations...")
        # Use the user home directory to find conversation files
        conversation_project_root = Path.home()
        data = query_tool.query_conversations(
            conversation_project_root, limit=limit * 2
        )  # Get more for filtering

        if not data.get("conversations"):
            return AccessValidator.create_success_response(
                json.dumps(
                    {
                        "conversations": [],
                        "total_analyzed": 0,
                        "context_keywords": context_keywords,
                        "processing_time": get_duration(timer),
                        "fast_mode": fast_mode,
                    },
                    indent=2,
                )
            )

        # Filter by date using shared functionality
        filtered_conversations = filter_conversations_by_date(
            data["conversations"], days_lookback
        )

        # Analyze and score conversations
        analyzed_conversations = []
        for conv in filtered_conversations:
            # Extract content using shared functionality
            content = extract_conversation_content(conv)

            # Analyze relevance using shared functionality
            score, analysis = analyze_session_relevance(
                content,
                context_keywords,
                conv.get("session_metadata", {}),
                include_detailed_analysis=not fast_mode,
            )

            if score >= min_score:
                # Filter by conversation type if specified
                if (
                    not conversation_types
                    or analysis["conversation_type"] in conversation_types
                ):
                    analyzed_conversations.append(
                        {
                            "session_data": conv,
                            "relevance_score": score,
                            "analysis": analysis,
                        }
                    )

        # Sort by relevance score using shared functionality
        analyzed_conversations = sort_conversations_by_relevance(
            analyzed_conversations, "relevance_score"
        )
        analyzed_conversations = analyzed_conversations[:limit]

        # Format response
        response_conversations = []
        for item in analyzed_conversations:
            conv = item["session_data"]
            analysis = item["analysis"]
            session_meta = conv.get("session_metadata", {})

            # Create conversation summary
            messages = conv.get("messages", [])
            first_message = messages[0] if messages else {}
            first_content = first_message.get("content", "")

            if isinstance(first_content, list):
                first_text = ""
                for content_item in first_content:
                    if (
                        isinstance(content_item, dict)
                        and content_item.get("type") == "text"
                    ):
                        first_text = content_item.get("text", "")
                        break
                first_content = first_text

            summary = (
                str(first_content)[:200] + "..."
                if len(str(first_content)) > 200
                else str(first_content)
            )

            response_conversations.append(
                {
                    "session_id": session_meta.get("session_id", "Unknown"),
                    "start_time": session_meta.get("start_time", "Unknown"),
                    "working_directory": session_meta.get("cwd", "Unknown"),
                    "message_count": len(messages),
                    "relevance_score": round(item["relevance_score"], 2),
                    "conversation_type": analysis["conversation_type"],
                    "summary": summary,
                    "keyword_matches": analysis["keyword_matches"],
                    "file_references": analysis["file_references"],
                    "last_modified": conv.get("last_modified", "Unknown"),
                }
            )

        processing_time = get_duration(timer)

        result = {
            "conversations": response_conversations,
            "total_analyzed": len(filtered_conversations),
            "total_returned": len(response_conversations),
            "context_keywords": context_keywords,
            "processing_time": processing_time,
            "fast_mode": fast_mode,
            "days_lookback": days_lookback,
            "min_score": min_score,
            "claude_home": data.get("claude_home"),
        }

        log_info(
            f"Recalled {len(response_conversations)} relevant conversations in {processing_time:.2f}s"
        )
        return AccessValidator.create_success_response(
            json.dumps(result, indent=2)
        )

    except Exception as e:
        log_error(e, "recall_claude_conversations")
        return AccessValidator.create_error_response(
            f"Error recalling Claude Code conversations: {str(e)}"
        )


def handle_search_claude_conversations_enhanced(
    arguments: Dict[str, Any], project_root: Path, **kwargs
) -> Dict[str, Any]:
    """Enhanced search for Claude Code conversations with context analysis."""
    try:
        # Get parameters
        query = arguments.get("query", "").strip()
        limit = arguments.get("limit", 20)
        include_content = arguments.get("include_content", False)
        days_lookback = arguments.get("days_lookback", 30)

        if not query:
            return AccessValidator.create_error_response(
                "query parameter is required"
            )

        timer = start_timer()

        # Initialize query tool
        query_tool = ClaudeCodeQuery(silent=True)

        # Search conversations - for Claude Code, use user home directory to find conversation files
        log_info(f"Searching Claude Code conversations for: '{query}'")
        # Use the user home directory to find conversation files
        conversation_project_root = Path.home()
        results = query_tool.search_conversations(
            query, conversation_project_root, limit=limit * 2
        )

        # Filter by date if specified using shared functionality
        if days_lookback > 0:
            filtered_results = []
            for result in results:
                session = result["session"]
                # Convert to format expected by shared filter function
                conversations_to_filter = [session]
                filtered = filter_conversations_by_date(
                    conversations_to_filter, days_lookback
                )
                if filtered:
                    filtered_results.append(result)
            results = filtered_results[:limit]

        # Format results with enhanced analysis using shared functionality
        context_keywords = generate_shared_context_keywords(project_root)
        formatted_results = []

        for result in results:
            session = result["session"]
            session_meta = session.get("session_metadata", {})

            # Extract content and analyze relevance using shared functionality
            content = extract_conversation_content(session)
            relevance_score, analysis = analyze_session_relevance(
                content, context_keywords, session_meta
            )

            formatted_result = {
                "session_id": session_meta.get("session_id", "Unknown"),
                "start_time": session_meta.get("start_time", "Unknown"),
                "working_directory": session_meta.get("cwd", "Unknown"),
                "match_count": result["match_count"],
                "relevance_score": round(relevance_score, 2),
                "conversation_type": analysis["conversation_type"],
                "keyword_matches": analysis["keyword_matches"],
                "matches": [],
            }

            for match in result["matches"]:
                match_data = {
                    "snippet": match["snippet"][
                        :CONVERSATION_SNIPPET_MAX_LENGTH
                    ],
                    "timestamp": match["message"].get("timestamp", "Unknown"),
                    "role": match["message"].get("role", "unknown"),
                }

                if include_content:
                    content = match["message"].get("content", "")
                    if isinstance(content, list):
                        # Handle structured content
                        text_content = ""
                        for item in content:
                            if (
                                isinstance(item, dict)
                                and item.get("type") == "text"
                            ):
                                text_content += item.get("text", "") + " "
                        content = text_content.strip()

                    match_data["full_content"] = str(content)[
                        :CONVERSATION_TEXT_EXTRACTION_LIMIT
                    ]

                formatted_result["matches"].append(match_data)

            formatted_results.append(formatted_result)

        # Sort by relevance score using shared functionality
        formatted_results = sort_conversations_by_relevance(
            formatted_results, "relevance_score"
        )

        processing_time = get_duration(timer)

        response_data = {
            "query": query,
            "total_results": len(formatted_results),
            "results": formatted_results,
            "context_keywords": context_keywords,
            "processing_time": processing_time,
            "days_lookback": days_lookback,
            "search_timestamp": datetime.now().isoformat(),
        }

        log_info(
            f"Found {len(formatted_results)} conversations matching '{query}' in {processing_time:.2f}s"
        )
        return AccessValidator.create_success_response(
            json.dumps(response_data, indent=2)
        )

    except Exception as e:
        log_error(e, "search_claude_conversations_enhanced")
        return AccessValidator.create_error_response(
            f"Error searching Claude Code conversations: {str(e)}"
        )


# Tool definitions
TOOL_RECALL_CLAUDE_CONVERSATIONS = {
    "name": "recall_claude_conversations",
    "description": "Recall and analyze Claude Code conversations for relevant context",
    "inputSchema": {
        "type": "object",
        "properties": {
            "fast_mode": {
                "type": "boolean",
                "default": True,
                "description": "Use fast mode for quicker context gathering",
            },
            "days_lookback": {
                "type": "integer",
                "default": CONVERSATION_DEFAULT_RECENT_DAYS,
                "minimum": 1,
                "maximum": CONVERSATION_MAX_LOOKBACK_DAYS,
                "description": "Number of days to look back for conversations",
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
                "description": "Filter by conversation types",
            },
            "min_score": {
                "type": "number",
                "default": CONVERSATION_DEFAULT_MIN_SCORE,
                "minimum": 0.0,
                "maximum": 5.0,
                "description": "Minimum relevance score threshold",
            },
        },
        "required": [],
    },
    "annotations": {
        "title": "Recall Claude Code Conversations",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}

TOOL_SEARCH_CLAUDE_CONVERSATIONS_ENHANCED = {
    "name": "search_claude_conversations_enhanced",
    "description": "Enhanced search of Claude Code conversations with context analysis",
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
                "description": "Maximum number of matching conversations to return",
            },
            "include_content": {
                "type": "boolean",
                "default": False,
                "description": "Include full message content in results",
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
        "title": "Enhanced Search Claude Code Conversations",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}

# Tool handlers and definitions
CLAUDE_CODE_RECALL_TOOL_HANDLERS = {
    "recall_claude_conversations": handle_recall_claude_conversations,
    "search_claude_conversations_enhanced": handle_search_claude_conversations_enhanced,
}

CLAUDE_CODE_RECALL_TOOL_DEFINITIONS = [
    TOOL_RECALL_CLAUDE_CONVERSATIONS,
    TOOL_SEARCH_CLAUDE_CONVERSATIONS_ENHANCED,
]
