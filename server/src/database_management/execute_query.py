"""
Database query execution for conversation recall operations.
"""

import json
import sqlite3
import traceback
from typing import Any, Dict, List

from src.config.constants import RECALL_CONVERSATIONS_QUERIES
from src.database_management.create_filters import SearchFilterBuilder
from src.utils.logger import log_error


class QueryExecutor:
    """Executes database queries for conversation data extraction."""

    def __init__(self) -> None:
        self.filter_builder = SearchFilterBuilder()

    def execute_conversation_query(
        self, db_path: str, limit: int, keywords: str = ""
    ) -> Dict[str, Any]:
        """Execute queries to extract conversation data from a database file.

        Args:
            db_path: Path to the database file
            limit: Maximum number of entries to return
            keywords: Keywords to filter by (applied at SQL level)

        Returns:
            Dictionary containing extracted conversation data
        """
        conversation_data: Dict[str, Any] = {
            "prompts": [],
            "generations": [],
            "history_entries": [],
            "database_path": db_path,
            "error": None,
        }

        search_conditions, search_params = self.filter_builder.build_search_conditions(
            keywords
        )

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

                # Execute prompts query
                conversation_data["prompts"] = self._execute_single_query(
                    cursor,
                    filtered_query,
                    base_query,
                    search_conditions,
                    search_params,
                    RECALL_CONVERSATIONS_QUERIES["PROMPTS_KEY"],
                    limit,
                )

                # Execute generations query
                conversation_data["generations"] = self._execute_single_query(
                    cursor,
                    filtered_query,
                    base_query,
                    search_conditions,
                    search_params,
                    RECALL_CONVERSATIONS_QUERIES["GENERATIONS_KEY"],
                    limit,
                )

                # Execute history query
                conversation_data["history_entries"] = self._execute_single_query(
                    cursor,
                    filtered_query,
                    base_query,
                    search_conditions,
                    search_params,
                    RECALL_CONVERSATIONS_QUERIES["HISTORY_KEY"],
                    limit,
                )

        except sqlite3.Error as e:
            error_msg = f"Database error: {str(e)}"
            log_error(error_msg, {"traceback": traceback.format_exc()})
            conversation_data["error"] = error_msg
        except (OSError, IOError, ValueError) as e:
            error_msg = f"File operation error: {str(e)}"
            log_error(error_msg, {"traceback": traceback.format_exc()})
            conversation_data["error"] = error_msg
        except (RuntimeError, MemoryError, SystemError) as e:
            # Handle system-level errors that shouldn't be ignored
            error_msg = f"System error: {str(e)}"
            log_error(error_msg, {"traceback": traceback.format_exc()})
            conversation_data["error"] = error_msg

        return conversation_data

    def _execute_single_query(
        self,
        cursor: sqlite3.Cursor,
        filtered_query: str,
        base_query: str,
        search_conditions: List[str],
        search_params: List[str],
        query_key: str,
        limit: int,
    ) -> List[Any]:
        """Execute a single query for prompts, generations, or history.

        Args:
            cursor: Database cursor
            filtered_query: Query with search conditions
            base_query: Base query without conditions
            search_conditions: Search conditions list
            search_params: Search parameters list
            query_key: Key for the specific query type
            limit: Maximum number of entries to return

        Returns:
            List of conversation entries
        """
        try:
            if search_conditions:
                cursor.execute(
                    filtered_query,
                    (query_key,) + tuple(search_params),
                )
            else:
                cursor.execute(base_query, (query_key,))

            result = cursor.fetchone()
            if result:
                value = result[0]
                if isinstance(value, bytes):
                    data = json.loads(value.decode("utf-8"))
                else:
                    data = json.loads(value)

                # Apply optimization: limit and prioritize recent conversations
                if isinstance(data, list):
                    # Take most recent conversations
                    return data[-limit:]
                else:
                    return []
            return []
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            error_msg = f"Error parsing {query_key}: {str(e)}"
            log_error(error_msg, {"traceback": traceback.format_exc()})
            raise ValueError(error_msg) from e
