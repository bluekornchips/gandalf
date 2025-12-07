"""
Direct database query handler for Gandalf.
"""

import json
import re
import sys
from typing import Any, Dict, List

from src.database_management.recall_conversations import ConversationDatabaseManager
from src.config.constants import GANDALF_REGISTRY_FILE
from src.utils.logger import log_error


class QueryHandler:
    """Handles direct database queries from query files."""

    def __init__(self) -> None:
        self.db_manager = ConversationDatabaseManager()

    def find_matches(self, text: str, search: str, regex: bool = False) -> List[str]:
        """Find all matches in text.

        Args:
            text: Text to search in
            search: Search string or regex pattern
            regex: If True, treat search as regex pattern

        Returns:
            List of matched strings
        """
        if not search or not text:
            return []

        if regex:
            try:
                return [m.group() for m in re.finditer(search, text, re.IGNORECASE)]
            except re.error:
                return []

        # Simple case-insensitive substring matching
        matches = []
        text_lower = text.lower()
        search_lower = search.lower()
        pos = 0
        while True:
            pos = text_lower.find(search_lower, pos)
            if pos == -1:
                break
            matches.append(text[pos : pos + len(search)])
            pos += 1
        return matches

    def load_query_file(self, query_file_path: str) -> Dict[str, Any]:
        """Load and parse a query file."""
        try:
            with open(query_file_path, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
                return data
        except FileNotFoundError:
            raise FileNotFoundError(f"Query file not found: {query_file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in query file: {e}")

    def validate_query(self, query_data: Dict[str, Any]) -> None:
        """Validate and normalize query data."""
        if "search" not in query_data:
            raise ValueError("Missing required field: search")

        if "limit" not in query_data:
            raise ValueError("Missing required field: limit")

        if not isinstance(query_data["search"], str):
            raise ValueError("Search must be a string")

        if not isinstance(query_data["limit"], int) or query_data["limit"] <= 0:
            raise ValueError("Limit must be a positive integer")

        # Defaults
        query_data.setdefault("include_prompts", True)
        query_data.setdefault("include_generations", False)
        query_data.setdefault("count_matches", False)
        query_data.setdefault("regex", False)

    def execute_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a database query."""
        try:
            with open(GANDALF_REGISTRY_FILE, "r", encoding="utf-8") as f:
                registry_data = json.load(f)
        except FileNotFoundError:
            return {
                "status": "error",
                "error": "Registry file not found",
                "message": f"Registry file not found at: {GANDALF_REGISTRY_FILE}",
            }
        except (json.JSONDecodeError, IOError) as e:
            return {
                "status": "error",
                "error": "Registry file error",
                "message": str(e),
            }

        from src.config.constants import DEFAULT_INCLUDE_EDITOR_HISTORY

        search = query_data.get("search", "")
        limit = query_data.get("limit", 8)
        include_prompts = query_data.get("include_prompts", True)
        include_generations = query_data.get("include_generations", False)
        include_editor_history = query_data.get(
            "include_editor_history", DEFAULT_INCLUDE_EDITOR_HISTORY
        )
        count_matches = query_data.get("count_matches", False)
        regex = query_data.get("regex", False)

        try:
            all_conversations, found_paths, total_db_files, db_file_counts = (
                self.db_manager.process_database_files(registry_data, limit, search)
            )

            # Flatten conversation entries from all databases
            all_entries: List[Dict[str, Any]] = []
            for conv in all_conversations:
                formatted = self.db_manager.format_conversation_entry(
                    conv,
                    include_prompts,
                    include_generations,
                    search,
                    include_editor_history,
                )
                if formatted.get("status") == "success":
                    all_entries.extend(formatted.get("conversations", []))

            total_match_count = 0
            if count_matches and search:
                for entry in all_entries:
                    summary = entry.get("summary", "")
                    matches = self.find_matches(summary, search, regex)
                    entry["match_count"] = len(matches)
                    total_match_count += len(matches)
                    if matches and regex:
                        entry["matched_texts"] = matches[:5]

            # Filter to only matching if search provided
            if search:
                all_entries = [
                    entry
                    for entry in all_entries
                    if self.find_matches(entry.get("summary", ""), search, regex)
                    or entry.get("match_count", 0) > 0
                ]

            # Sort by relevance if search provided
            if search:
                all_entries.sort(key=lambda x: x.get("relevance", 0), reverse=True)

            # Limit results to 32
            if len(all_entries) > 32:
                all_entries = all_entries[:32]

            result: Dict[str, Any] = {
                "status": "success",
                "query": {
                    "search": search,
                    "limit": limit,
                    "regex": regex,
                },
                "results": {
                    "conversations": all_entries,
                    "total_conversations": len(all_entries),
                    "databases_searched": total_db_files,
                    "total_found": len(all_entries),
                },
            }

            if count_matches:
                result["results"]["total_match_count"] = total_match_count

            return result

        except Exception as e:
            log_error(f"Error executing query: {str(e)}")
            return {
                "status": "error",
                "error": "Query execution error",
                "message": str(e),
            }

    def process_query_file(self, query_file_path: str) -> Dict[str, Any]:
        """Process a query file and return results."""
        try:
            query_data = self.load_query_file(query_file_path)
            self.validate_query(query_data)
            return self.execute_query(query_data)
        except Exception as e:
            return {
                "status": "error",
                "error": "Query processing error",
                "message": str(e),
            }


def main() -> None:
    """Main entry point for query handler."""
    if len(sys.argv) != 2:
        print("Usage: python query_handler.py <query_file_path>", file=sys.stderr)
        sys.exit(1)

    handler = QueryHandler()
    result = handler.process_query_file(sys.argv[1])
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
