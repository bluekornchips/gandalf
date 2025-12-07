"""
Conversation data extraction from database files.
"""

import os
from typing import Any, Dict, List

from src.config.constants import SUPPORTED_DB_FILES
from src.database_management.execute_query import QueryExecutor


class ConversationDataExtractor:
    """Extracts conversation data from database files."""

    def __init__(self) -> None:
        self.query_executor = QueryExecutor()

    def extract_conversation_data(
        self, db_path: str, limit: int = 50, phrases: List[str] | None = None
    ) -> Dict[str, Any]:
        """Extract conversation data from a database file with optional phrase filtering.

        Args:
            db_path: Path to the database file
            limit: Maximum number of entries to return
            phrases: List of phrases to filter by (applied at SQL level)

        Returns:
            Dictionary containing extracted conversation data
        """
        return self.query_executor.execute_conversation_query(db_path, limit, phrases)

    def process_database_files(
        self,
        registry_data: Dict[str, Any],
        limit: int,
        phrases: List[str] | None = None,
    ) -> tuple[List[Dict[str, Any]], List[str], int, Dict[str, int]]:
        """Process database files from registry and extract conversation data.

        Args:
            registry_data: The loaded registry data
            limit: Maximum number of conversations to return per database
            phrases: List of phrases to filter by

        Returns:
            Tuple of (all_conversations, found_paths, total_db_files, db_file_counts)
        """
        total_db_files = 0
        db_file_counts: Dict[str, int] = {}
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
                                    conversation_data = self.extract_conversation_data(
                                        db_path, limit, phrases
                                    )
                                    all_conversations.append(conversation_data)

        return all_conversations, found_paths, total_db_files, db_file_counts
