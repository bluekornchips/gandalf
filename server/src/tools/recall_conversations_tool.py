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
    GANDALF_REGISTRY_FILE,
    INCLUDE_GENERATIONS_DEFAULT,
    INCLUDE_PROMPTS_DEFAULT,
    MAX_CONVERSATIONS,
    MAX_KEYWORDS,
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
                "keywords": {
                    "type": "string",
                    "description": f"Keywords to search for in conversations (optional, max {MAX_KEYWORDS} words)",
                },
                "limit": {
                    "type": "integer",
                    "description": f"Maximum number of conversations to return (default: {MAX_CONVERSATIONS})",
                    "default": MAX_CONVERSATIONS,
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
        keywords = args.get("keywords", "")
        limit = min(args.get("limit", MAX_CONVERSATIONS), MAX_RESULTS_LIMIT)
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
            self.db_manager.process_database_files(registry_data, limit, keywords)
        )

        # Format results with better structure for agent chat
        formatted_conversations = [
            self.db_manager.format_conversation_entry(
                conv,
                include_prompts,
                include_generations,
                keywords,
                include_editor_history,
            )
            for conv in all_conversations
        ]

        # Apply smart filtering to reduce total conversations if needed
        if len(formatted_conversations) > 32:  # Limit to 32 total conversations
            # Sort by relevance and take top conversations
            scored_conversations = []
            for conv in formatted_conversations:
                if conv.get("conversations"):
                    relevances = [
                        c.get("relevance", 0.0)
                        for c in conv["conversations"]
                        if c.get("relevance") is not None
                    ]
                    max_relevance = max(relevances) if relevances else 0.0
                    scored_conversations.append((conv, max_relevance))
                else:
                    scored_conversations.append((conv, 0.0))

            # Sort by relevance and take top conversations
            scored_conversations.sort(key=lambda x: x[1], reverse=True)
            formatted_conversations = [conv for conv, _ in scored_conversations[:32]]

        # Simplified result structure
        result = {
            "status": "success",
            "conversations": formatted_conversations,
            "search_info": {
                "keywords": keywords if keywords else None,
                "databases_searched": total_db_files,
                "total_found": len(formatted_conversations),
            },
        }

        # Create a more readable JSON output with better formatting
        formatted_output = json.dumps(result, indent=2, ensure_ascii=False)

        return [ToolResult(text=formatted_output)]
