"""
Direct database query handler for Gandalf.
"""

import json
import sys
from typing import Any, Dict

from src.database_management.recall_conversations import ConversationDatabaseManager
from src.config.constants import GANDALF_REGISTRY_FILE
from src.utils.logger import log_error


class QueryHandler:
    """Handles direct database queries from query files."""

    def __init__(self) -> None:
        self.db_manager = ConversationDatabaseManager()

    def load_query_file(self, query_file_path: str) -> Dict[str, Any]:
        """Load and parse a query file.

        Args:
            query_file_path: Path to the query file

        Returns:
            Parsed query data
        """
        try:
            with open(query_file_path, "r", encoding="utf-8") as f:
                query_data: Dict[str, Any] = json.load(f)
            return query_data
        except FileNotFoundError:
            raise FileNotFoundError(f"Query file not found: {query_file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in query file: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading query file: {e}")

    def validate_query(self, query_data: Dict[str, Any]) -> None:
        """Validate query data structure.

        Args:
            query_data: Query data to validate

        Raises:
            ValueError: If query data is invalid
        """
        required_fields = ["keywords", "limit"]
        for field in required_fields:
            if field not in query_data:
                raise ValueError(f"Missing required field: {field}")

        if not isinstance(query_data["keywords"], str):
            raise ValueError("Keywords must be a string")

        if not isinstance(query_data["limit"], int) or query_data["limit"] <= 0:
            raise ValueError("Limit must be a positive integer")

        # Optional fields with defaults
        if "include_prompts" not in query_data:
            query_data["include_prompts"] = True
        if "include_generations" not in query_data:
            query_data["include_generations"] = False

    def execute_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a database query.

        Args:
            query_data: Query parameters

        Returns:
            Query results
        """
        try:
            # Load registry data
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
                "message": f"Error reading registry file: {str(e)}",
            }

        # Extract query parameters
        keywords = query_data.get("keywords", "")
        limit = query_data.get("limit", 8)
        include_prompts = query_data.get("include_prompts", True)
        include_generations = query_data.get("include_generations", False)

        try:
            # Process database files
            all_conversations, found_paths, total_db_files, db_file_counts = (
                self.db_manager.process_database_files(registry_data, limit, keywords)
            )

            # Format results
            formatted_conversations = [
                self.db_manager.format_conversation_entry(
                    conv, include_prompts, include_generations, keywords
                )
                for conv in all_conversations
            ]

            # Apply smart filtering if needed
            if len(formatted_conversations) > 32:
                scored_conversations = []
                for conv in formatted_conversations:
                    if conv.get("conversations"):
                        max_relevance = max(
                            c.get("relevance", 0) for c in conv["conversations"]
                        )
                        scored_conversations.append((conv, max_relevance))
                    else:
                        scored_conversations.append((conv, 0))

                scored_conversations.sort(key=lambda x: x[1], reverse=True)
                formatted_conversations = [
                    conv for conv, _ in scored_conversations[:32]
                ]

            # Build result
            result = {
                "status": "success",
                "query": {
                    "keywords": keywords,
                    "limit": limit,
                    "include_prompts": include_prompts,
                    "include_generations": include_generations,
                },
                "results": {
                    "total_conversations": sum(
                        conv.get("total_conversations", 0)
                        for conv in formatted_conversations
                    ),
                    "conversations": formatted_conversations,
                    "search_info": {
                        "keywords": keywords if keywords else None,
                        "databases_searched": total_db_files,
                        "total_found": len(formatted_conversations),
                        "database_paths": found_paths,
                        "database_counts": db_file_counts,
                    },
                },
            }

            return result

        except Exception as e:
            log_error(f"Error executing query: {str(e)}")
            return {
                "status": "error",
                "error": "Query execution error",
                "message": str(e),
            }

    def process_query_file(self, query_file_path: str) -> Dict[str, Any]:
        """Process a query file and return results.

        Args:
            query_file_path: Path to the query file

        Returns:
            Query results
        """
        try:
            # Load and validate query
            query_data = self.load_query_file(query_file_path)
            self.validate_query(query_data)

            # Execute query
            result = self.execute_query(query_data)
            return result

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

    query_file_path = sys.argv[1]
    handler = QueryHandler()
    result = handler.process_query_file(query_file_path)

    # Output result as JSON
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
