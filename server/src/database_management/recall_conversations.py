"""
Database management for conversation recall operations.
"""

from typing import Any, Dict, List

from src.database_management.conversation_threading import ConversationThreader
from src.database_management.create_filters import SearchFilterBuilder
from src.database_management.execute_query import QueryExecutor
from src.database_management.extract_conversation_data import ConversationDataExtractor
from src.database_management.format_output import OutputFormatter
from src.database_management.recency_scorer import RecencyScorer


class ConversationDatabaseManager:
    """Manages database operations for conversation recall."""

    def __init__(self) -> None:
        self.filter_builder = SearchFilterBuilder()
        self.query_executor = QueryExecutor()
        self.data_extractor = ConversationDataExtractor()
        self.output_formatter = OutputFormatter()

        self._recency_scorer: RecencyScorer | None = None
        self._conversation_threader: ConversationThreader | None = None

    def _get_recency_scorer(self) -> RecencyScorer:
        """Get or create recency scorer instance.

        Returns:
            RecencyScorer instance.
        """
        if self._recency_scorer is None:
            self._recency_scorer = RecencyScorer()
        return self._recency_scorer

    def _get_conversation_threader(self) -> ConversationThreader:
        """Get or create conversation threader instance.

        Returns:
            ConversationThreader instance.
        """
        if self._conversation_threader is None:
            self._conversation_threader = ConversationThreader()
        return self._conversation_threader

    def build_search_conditions(self, keywords: str) -> tuple[List[str], List[str]]:
        """Build SQL search conditions and parameters for keywords.

        Args:
            keywords: Keywords to search for

        Returns:
            Tuple of (search_conditions, search_params)
        """
        return self.filter_builder.build_search_conditions(keywords)

    def create_conversation_summary(self, conversation: Dict[str, Any]) -> str:
        """Create a concise summary of a conversation entry.

        Args:
            conversation: Conversation data dictionary

        Returns:
            Concise summary string limited to MAX_SUMMARY_LENGTH
        """
        return self.output_formatter.create_conversation_summary(conversation)

    def score_conversation_relevance(
        self, conversation: Dict[str, Any], keywords: str
    ) -> float:
        """Score conversation relevance using keyword matching.

        Args:
            conversation: Conversation data
            keywords: Search keywords

        Returns:
            Relevance score (0.0 to 1.0)
        """
        return self.output_formatter.score_conversation_relevance(
            conversation, keywords
        )

    def extract_conversation_data(
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
        return self.data_extractor.extract_conversation_data(db_path, limit, keywords)

    def process_database_files(
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
        return self.data_extractor.process_database_files(
            registry_data, limit, keywords
        )

    def format_conversation_entry(
        self,
        conv_data: Dict[str, Any],
        include_prompts: bool,
        include_generations: bool,
        keywords: str = "",
        include_editor_history: bool = False,
    ) -> Dict[str, Any]:
        """Format a conversation entry with concise output.

        Args:
            conv_data: Conversation data dictionary
            include_prompts: Whether to include prompts in output
            include_generations: Whether to include generations in output
            keywords: Search keywords for relevance scoring
            include_editor_history: Whether to include editor UI history entries

        Returns:
            Formatted conversation entry dictionary
        """
        recency_scorer = self._get_recency_scorer()
        return self.output_formatter.format_conversation_entry(
            conv_data,
            include_prompts,
            include_generations,
            keywords,
            include_editor_history,
            recency_scorer,
        )
