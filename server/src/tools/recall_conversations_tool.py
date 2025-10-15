"""
Recall conversations tool implementation.
"""

import json
import os
import sqlite3
import traceback
from datetime import datetime
from datetime import timezone
from typing import Any, Dict, List

from src.tools.base_tool import BaseTool
from src.protocol.types import ToolResult
from src.config.constants import (
    GANDALF_REGISTRY_FILE,
    SUPPORTED_DB_FILES,
    RECALL_CONVERSATIONS_QUERIES,
    IGNORED_KEYWORDS,
    MAX_CONVERSATIONS,
    MAX_KEYWORDS,
    INCLUDE_PROMPTS_DEFAULT,
    INCLUDE_GENERATIONS_DEFAULT,
)
from src.utils.logger import log_info, log_error


class RecallConversationsTool(BaseTool):
    """Tool for recalling conversations."""

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
            },
        }

    def _build_search_conditions(self, keywords: str) -> tuple[List[str], List[str]]:
        """Build SQL search conditions and parameters for keywords.

        Args:
            keywords: Keywords to search for

        Returns:
            Tuple of (search_conditions, search_params)
        """
        if not keywords:
            return [], []

        # Filter out ignored keywords and limit to MAX_KEYWORDS
        keyword_words = keywords.lower().split()
        meaningful_words = [
            word for word in keyword_words if word not in IGNORED_KEYWORDS
        ]

        # Limit to MAX_KEYWORDS
        if len(meaningful_words) > MAX_KEYWORDS:
            meaningful_words = meaningful_words[:MAX_KEYWORDS]

        # If no meaningful words remain, use original keywords, also limited
        if not meaningful_words:
            search_terms = keyword_words[:MAX_KEYWORDS]
        else:
            search_terms = meaningful_words

        conditions = []
        params = []

        for term in search_terms:
            # Search in JSON content using LIKE with wildcards, yay sqlite
            condition = "value LIKE ?"
            conditions.append(condition)
            params.append(f"%{term}%")

        return conditions, params

    def _extract_conversation_data(
        self, db_path: str, limit: int = 50, keywords: str = ""
    ) -> Dict[str, Any]:
        """Extract conversation data from a database file with optional keyword filtering.

        Args:
            db_path: Path to the database file
            limit: Maximum number of entries to return
            keywords: Keywords to filter by (applied at SQL level)

        Returns:
            Dictionary containing extracted conversation data
        """
        conversation_data = {
            "prompts": [],
            "generations": [],
            "history_entries": [],
            "database_path": db_path,
            "error": None,
        }

        search_conditions, search_params = self._build_search_conditions(keywords)

        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()

                # Build dynamic queries
                base_query = "SELECT value FROM ItemTable WHERE key = ?"

                if search_conditions:
                    # Add search conditions with OR logic to find any matching term
                    where_clause = " AND (" + " OR ".join(search_conditions) + ")"
                    filtered_query = base_query + where_clause
                else:
                    filtered_query = base_query

                # prompts query
                if search_conditions:
                    cursor.execute(
                        filtered_query,
                        (RECALL_CONVERSATIONS_QUERIES["PROMPTS_KEY"],)
                        + tuple(search_params),
                    )
                else:
                    cursor.execute(
                        base_query, (RECALL_CONVERSATIONS_QUERIES["PROMPTS_KEY"],)
                    )

                prompts_result = cursor.fetchone()
                if prompts_result:
                    try:
                        value = prompts_result[0]
                        if isinstance(value, bytes):
                            prompts_data = json.loads(value.decode("utf-8"))
                        else:
                            prompts_data = json.loads(value)
                        conversation_data["prompts"] = (
                            prompts_data[-limit:]
                            if isinstance(prompts_data, list)
                            else []
                        )
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        error_msg = f"Error parsing prompts: {str(e)}"
                        log_error(error_msg, {"traceback": traceback.format_exc()})
                        conversation_data["error"] = error_msg

                # generations query
                if search_conditions:
                    cursor.execute(
                        filtered_query,
                        (RECALL_CONVERSATIONS_QUERIES["GENERATIONS_KEY"],)
                        + tuple(search_params),
                    )
                else:
                    cursor.execute(
                        base_query, (RECALL_CONVERSATIONS_QUERIES["GENERATIONS_KEY"],)
                    )
                generations_result = cursor.fetchone()
                if generations_result:
                    try:
                        value = generations_result[0]
                        if isinstance(value, bytes):
                            generations_data = json.loads(value.decode("utf-8"))
                        else:
                            generations_data = json.loads(value)
                        conversation_data["generations"] = (
                            generations_data[-limit:]
                            if isinstance(generations_data, list)
                            else []
                        )
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        if not conversation_data["error"]:
                            error_msg = f"Error parsing generations: {str(e)}"
                            log_error(error_msg, {"traceback": traceback.format_exc()})
                            conversation_data["error"] = error_msg

                # history query
                if search_conditions:
                    cursor.execute(
                        filtered_query,
                        (RECALL_CONVERSATIONS_QUERIES["HISTORY_KEY"],)
                        + tuple(search_params),
                    )
                else:
                    cursor.execute(
                        base_query, (RECALL_CONVERSATIONS_QUERIES["HISTORY_KEY"],)
                    )
                history_result = cursor.fetchone()
                if history_result:
                    try:
                        value = history_result[0]
                        if isinstance(value, bytes):
                            history_data = json.loads(value.decode("utf-8"))
                        else:
                            history_data = json.loads(value)
                        conversation_data["history_entries"] = (
                            history_data[-limit:]
                            if isinstance(history_data, list)
                            else []
                        )
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        if not conversation_data["error"]:
                            error_msg = f"Error parsing history: {str(e)}"
                            log_error(error_msg, {"traceback": traceback.format_exc()})
                            conversation_data["error"] = error_msg

        except sqlite3.Error as e:
            error_msg = f"Database error: {str(e)}"
            log_error(error_msg, {"traceback": traceback.format_exc()})
            conversation_data["error"] = error_msg
        except (OSError, IOError, ValueError) as e:
            error_msg = f"File operation error: {str(e)}"
            log_error(error_msg, {"traceback": traceback.format_exc()})
            conversation_data["error"] = error_msg
        except Exception as e:
            # Keep broad exception for truly unexpected errors at database boundary
            error_msg = f"Unexpected error: {str(e)}"
            log_error(error_msg, {"traceback": traceback.format_exc()})
            conversation_data["error"] = error_msg

        return conversation_data

    def _format_conversation_entry(
        self,
        conv_data: Dict[str, Any],
        include_prompts: bool,
        include_generations: bool,
    ) -> Dict[str, Any]:
        """
        Format a conversation entry for better readability.
        Or at least its supposed to, because I don't actually visually see the changes
        in agent chat, but I do in logs.
        """
        formatted = {
            "database_path": conv_data.get("database_path", ""),
            "status": "success" if not conv_data.get("error") else "error",
            "counts": {
                "prompts": len(conv_data.get("prompts", [])) if include_prompts else 0,
                "generations": len(conv_data.get("generations", []))
                if include_generations
                else 0,
                "history_entries": len(conv_data.get("history_entries", [])),
            },
        }

        if conv_data.get("error"):
            formatted["error"] = conv_data["error"]
        else:
            # Include sample data for better context
            if include_prompts and conv_data.get("prompts"):
                formatted["sample_prompts"] = [
                    {"text": p.get("text", ""), "commandType": p.get("commandType", 0)}
                    for p in conv_data["prompts"][:2]
                ]

            if include_generations and conv_data.get("generations"):
                formatted["sample_generations"] = [
                    {
                        "textDescription": g.get("textDescription", ""),
                        "type": g.get("type", ""),
                    }
                    for g in conv_data["generations"][:2]
                ]

        return formatted

    def _process_database_files(
        self, registry_data: Dict[str, Any], limit: int, keywords: str = ""
    ) -> tuple[List[Dict[str, Any]], List[str], int, Dict[str, int]]:
        """Process database files from registry and extract conversation data.

        Args:
            registry_data: The loaded registry data
            limit: Maximum number of conversations to return per database
            keywords: Keywords to filter by

        Returns:
            Tuple of (all_conversations, found_paths, total_db_files, db_file_counts)
        """
        total_db_files = 0
        db_file_counts = {}
        found_paths = []
        all_conversations = []

        for tool_name, paths in registry_data.items():
            if isinstance(paths, list):
                for path in paths:
                    if os.path.exists(path):
                        for db_file in SUPPORTED_DB_FILES:
                            for root, dirs, files in os.walk(path):
                                if db_file in files:
                                    db_path = os.path.join(root, db_file)
                                    total_db_files += 1
                                    db_file_counts[db_file] = (
                                        db_file_counts.get(db_file, 0) + 1
                                    )
                                    found_paths.append(db_path)

                                    # Extract conversation data from this database
                                    conversation_data = self._extract_conversation_data(
                                        db_path, limit, keywords
                                    )
                                    all_conversations.append(conversation_data)

        return all_conversations, found_paths, total_db_files, db_file_counts

    async def execute(self, arguments: Dict[str, Any] | None) -> List[ToolResult]:
        """Execute the recall conversations tool."""
        log_info("Recall conversations tool called")

        # Parse arguments
        args = arguments or {}
        keywords = args.get("keywords", "")
        limit = args.get("limit", MAX_CONVERSATIONS)
        include_prompts = args.get("include_prompts", INCLUDE_PROMPTS_DEFAULT)
        include_generations = args.get(
            "include_generations", INCLUDE_GENERATIONS_DEFAULT
        )

        if not os.path.exists(GANDALF_REGISTRY_FILE):
            return [ToolResult(text="Error: Registry file not found")]

        try:
            with open(GANDALF_REGISTRY_FILE, "r", encoding="utf-8") as f:
                registry_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            error_msg = f"Error reading registry file: {str(e)}"
            log_error(error_msg, {"traceback": traceback.format_exc()})
            return [ToolResult(text=error_msg)]

        # Find and process database files
        all_conversations, found_paths, total_db_files, db_file_counts = (
            self._process_database_files(registry_data, limit, keywords)
        )

        # Format results with better structure for agent chat
        formatted_conversations = [
            self._format_conversation_entry(conv, include_prompts, include_generations)
            for conv in all_conversations
        ]

        result = {
            "status": "success",
            "metadata": {
                "total_db_files_found": total_db_files,
                "supported_db_files": SUPPORTED_DB_FILES,
                "db_file_counts": db_file_counts,
                "registry_file": GANDALF_REGISTRY_FILE,
                "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
                "search_keywords": keywords if keywords else None,
                "filtered_by_keywords": bool(keywords),
            },
            "summary": {
                "total_prompts": sum(
                    len(conv.get("prompts", [])) for conv in all_conversations
                ),
                "total_generations": sum(
                    len(conv.get("generations", [])) for conv in all_conversations
                ),
                "total_history_entries": sum(
                    len(conv.get("history_entries", [])) for conv in all_conversations
                ),
                "databases_with_errors": len(
                    [conv for conv in all_conversations if conv.get("error")]
                ),
                "databases_processed": len(all_conversations),
            },
            "conversations": formatted_conversations,
            "found_paths": found_paths,
        }

        # Create a more readable JSON output with better formatting
        formatted_output = json.dumps(result, indent=2, ensure_ascii=False)

        return [ToolResult(text=formatted_output)]
