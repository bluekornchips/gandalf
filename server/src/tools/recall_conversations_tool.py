"""
Recall conversations tool implementation.
"""

import json
import traceback
from typing import Any, Dict, List

from src.tools.base_tool import BaseTool
from src.protocol.models import ToolResult
from src.config.constants import (
    DEFAULT_INCLUDE_EDITOR_HISTORY,
    DEFAULT_RESULTS_LIMIT,
    GANDALF_REGISTRY_FILE,
    INCLUDE_GENERATIONS_DEFAULT,
    INCLUDE_PROMPTS_DEFAULT,
    MAX_PHRASES,
    MAX_RESULTS_LIMIT,
)
from src.database_management.recall_conversations import ConversationDatabaseManager
from src.utils.logger import log_info, log_error


class RecallConversationsTool(BaseTool):
    """Tool for recalling conversations."""

    def __init__(self) -> None:
        """Initialize the tool with database manager."""
        super().__init__()
        self.db_manager = ConversationDatabaseManager()

    @property
    def name(self) -> str:
        """Tool name."""
        return "recall_conversations"

    @property
    def description(self) -> str:
        """Tool description."""
        return "Extract and analyze conversation history from database files in the Gandalf registry"

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Tool input schema."""
        return {
            "type": "object",
            "properties": {
                "phrases": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": f"Exact phrases to search for in conversations (optional, max {MAX_PHRASES} phrases)",
                },
                "limit": {
                    "type": "integer",
                    "description": f"Maximum number of results to return (default: {DEFAULT_RESULTS_LIMIT}, max: {MAX_RESULTS_LIMIT})",
                    "default": DEFAULT_RESULTS_LIMIT,
                },
                "include_prompts": {
                    "type": "boolean",
                    "description": f"Include user prompts in results (default: {INCLUDE_PROMPTS_DEFAULT})",
                    "default": INCLUDE_PROMPTS_DEFAULT,
                },
                "include_generations": {
                    "type": "boolean",
                    "description": f"Include AI generations in results (default: {INCLUDE_GENERATIONS_DEFAULT})",
                    "default": INCLUDE_GENERATIONS_DEFAULT,
                },
                "include_editor_history": {
                    "type": "boolean",
                    "description": f"Include editor UI state entries in results (default: {DEFAULT_INCLUDE_EDITOR_HISTORY})",
                    "default": DEFAULT_INCLUDE_EDITOR_HISTORY,
                },
            },
        }

    async def execute(self, arguments: Dict[str, Any] | None) -> List[ToolResult]:
        """Execute the recall conversations tool."""
        log_info("Recall conversations tool called")

        # Parse arguments
        args = arguments or {}
        phrases_input = args.get("phrases", [])
        # Limit to MAX_PHRASES and filter empty strings
        phrases: List[str] = [p for p in phrases_input if p][:MAX_PHRASES]
        results_limit = min(args.get("limit", DEFAULT_RESULTS_LIMIT), MAX_RESULTS_LIMIT)
        include_prompts = args.get("include_prompts", INCLUDE_PROMPTS_DEFAULT)
        # Always use the environment variable setting for include_generations
        include_generations = INCLUDE_GENERATIONS_DEFAULT
        include_editor_history = args.get(
            "include_editor_history", DEFAULT_INCLUDE_EDITOR_HISTORY
        )

        try:
            # Load registry data
            with open(GANDALF_REGISTRY_FILE, "r", encoding="utf-8") as f:
                registry_data = json.load(f)
        except FileNotFoundError:
            return [ToolResult(text="Registry file not found")]
        except (json.JSONDecodeError, IOError) as e:
            error_msg = f"Error reading registry file: {str(e)}"
            log_error(error_msg, {"traceback": traceback.format_exc()})
            return [ToolResult(text=error_msg)]

        # Find and process database files using database manager
        all_conversations, _, total_db_files, _ = (
            self.db_manager.process_database_files(
                registry_data, results_limit, phrases
            )
        )

        all_entries: List[Dict[str, Any]] = []
        for conv in all_conversations:
            formatted = self.db_manager.format_conversation_entry(
                conv,
                include_prompts,
                include_generations,
                phrases,
                include_editor_history,
            )
            if formatted.get("status") == "success":
                all_entries.extend(formatted.get("conversations", []))

        if phrases:
            # Filter to only exact phrase matches (relevance > 0)
            all_entries = [e for e in all_entries if e.get("relevance", 0) > 0]
            all_entries.sort(key=lambda x: x.get("relevance", 0), reverse=True)

        if len(all_entries) > results_limit:
            all_entries = all_entries[:results_limit]

        result = {
            "status": "success",
            "conversations": all_entries,
            "search_info": {
                "phrases": phrases if phrases else None,
                "databases_searched": total_db_files,
                "total_found": len(all_entries),
            },
        }

        formatted_output = json.dumps(result, indent=2, ensure_ascii=False)

        return [ToolResult(text=formatted_output)]
