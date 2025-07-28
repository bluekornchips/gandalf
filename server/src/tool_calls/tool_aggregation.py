"""
Tool aggregation logic for Gandalf MCP Server.

This module handles the detection and processing of conversations from
multiple agentic tools (Cursor, Claude Code, Windsurf).
"""

from pathlib import Path
from typing import Any

from src.config.conversation_config import (
    AGENTIC_TOOL_CLAUDE_CODE,
    AGENTIC_TOOL_CURSOR,
    AGENTIC_TOOL_WINDSURF,
    SUPPORTED_AGENTIC_TOOLS,
)
from src.core.database_scanner import get_available_agentic_tools
from src.core.tool_registry import get_registered_agentic_tools
from src.tool_calls.claude_code.recall import (
    handle_recall_claude_conversations as claude_recall_handler,
)
from src.tool_calls.cursor.recall import CONVERSATION_RECALL_TOOL_HANDLERS
from src.tool_calls.windsurf.recall import (
    handle_recall_windsurf_conversations as windsurf_recall_handler,
)
from src.utils.access_control import AccessValidator
from src.utils.common import log_debug, log_info


def _detect_available_agentic_tools() -> list[str]:
    """Detect which agentic tools are available in the current environment."""
    available_tools = []

    # Check registry first (faster)
    registered_tools = get_registered_agentic_tools()
    log_debug(f"Registered tools detected: {registered_tools}")

    # Use registry results if available
    if registered_tools:
        available_tools.extend(registered_tools)
    else:
        # Fallback to database scanner (slower but more comprehensive)
        log_debug("No registered tools found, falling back to database scanner")
        scanned_tools = get_available_agentic_tools()
        available_tools.extend(scanned_tools)

    # Filter to only supported tools and remove duplicates
    filtered_tools = []
    for tool in available_tools:
        if tool in SUPPORTED_AGENTIC_TOOLS and tool not in filtered_tools:
            filtered_tools.append(tool)

    log_info(f"Available agentic tools: {filtered_tools}")
    return filtered_tools


def _process_agentic_tool_conversations(
    tool_name: str,
    arguments: dict[str, Any],
    project_root: Path,
    **kwargs: Any,
) -> dict[str, Any]:
    """Process conversations for a specific agentic tool."""
    log_debug(f"Processing conversations for tool: {tool_name}")

    try:
        if tool_name == AGENTIC_TOOL_CURSOR:
            handler = CONVERSATION_RECALL_TOOL_HANDLERS.get(
                "recall_cursor_conversations"
            )
            if handler:
                return handler(arguments, project_root, **kwargs)
            else:
                return AccessValidator.create_error_response(
                    f"Handler not found for {tool_name}"
                )

        elif tool_name == AGENTIC_TOOL_CLAUDE_CODE:
            return claude_recall_handler(arguments, project_root, **kwargs)

        elif tool_name == AGENTIC_TOOL_WINDSURF:
            return windsurf_recall_handler(arguments, project_root, **kwargs)

        else:
            return AccessValidator.create_error_response(
                f"Unsupported tool: {tool_name}"
            )

    except Exception as e:
        log_debug(f"Error processing {tool_name} conversations: {e}")
        return AccessValidator.create_error_response(
            f"Failed to process {tool_name} conversations: {str(e)}"
        )


def _create_no_tools_response() -> dict[str, Any]:
    """Create response when no agentic tools are available."""

    return AccessValidator.create_success_response(
        f"No agentic tools available. Checked: {SUPPORTED_AGENTIC_TOOLS}"
    )


def aggregate_tool_results(
    tool_results: list[tuple[str, dict[str, Any]]],
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Aggregate results from multiple tools."""
    all_conversations: list[dict[str, Any]] = []
    processing_stats: dict[str, Any] = {
        "tools_processed": 0,
        "total_processing_time": 0.0,
        "tools_with_data": [],
        "tools_with_errors": [],
    }

    for tool_name, result in tool_results:
        processing_stats["tools_processed"] += 1

        if "content" in result and isinstance(result["content"], list):
            # Handle MCP-style response
            try:
                for content_item in result["content"]:
                    if content_item.get("type") == "text":
                        import json

                        tool_data = json.loads(content_item["text"])
                        conversations = tool_data.get("conversations", [])
                        all_conversations.extend(conversations)

                        # Track processing time
                        proc_time = tool_data.get("processing_time", 0)
                        if isinstance(proc_time, int | float):
                            processing_stats["total_processing_time"] += proc_time

                        if conversations:
                            processing_stats["tools_with_data"].append(tool_name)
                        break
            except (json.JSONDecodeError, KeyError, TypeError):
                processing_stats["tools_with_errors"].append(tool_name)
                log_debug(f"Failed to parse {tool_name} response")
        else:
            # Handle error responses
            processing_stats["tools_with_errors"].append(tool_name)

    # Sort by relevance score and limit results
    all_conversations.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    limited_conversations = all_conversations[:limit]

    return limited_conversations, processing_stats


def get_tool_handlers() -> dict[str, Any]:
    """Get available tool handlers for conversation processing."""
    handlers = {}

    # Add cursor handler if available
    cursor_handler = CONVERSATION_RECALL_TOOL_HANDLERS.get(
        "recall_cursor_conversations"
    )
    if cursor_handler:
        handlers[AGENTIC_TOOL_CURSOR] = cursor_handler

    # Add claude code handler
    handlers[AGENTIC_TOOL_CLAUDE_CODE] = claude_recall_handler

    # Add windsurf handler
    handlers[AGENTIC_TOOL_WINDSURF] = windsurf_recall_handler

    return handlers
