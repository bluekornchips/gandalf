"""
Output formatting for conversation recall operations.
"""

from typing import Any, Dict, List, Optional, TypedDict

from src.config.constants import (
    MAX_SUMMARY_ENTRIES,
    MAX_SUMMARY_LENGTH,
    DEFAULT_INCLUDE_EDITOR_HISTORY,
)


class ConversationSummary(TypedDict, total=False):
    """Type definition for conversation summary entries."""

    id: str
    summary: str
    type: str
    relevance: float
    prompt: Optional[Dict[str, Any]]
    generation: Optional[Dict[str, Any]]


class OutputFormatter:
    """Formats conversation data for output."""

    def create_conversation_summary(self, conversation: Dict[str, Any]) -> str:
        """Create a concise summary of a conversation entry.

        Args:
            conversation: Conversation data dictionary

        Returns:
            Concise summary string limited to MAX_SUMMARY_LENGTH
        """
        if not conversation:
            return ""

        # Extract text content based on conversation type
        text_content = ""
        if isinstance(conversation, dict):
            # Try different possible text fields
            text_content = (
                conversation.get("text", "")
                or conversation.get("textDescription", "")
                or conversation.get("content", "")
                or conversation.get("message", "")
                or str(conversation)
            )
        else:
            text_content = str(conversation)

        summary = text_content.strip()
        if len(summary) > MAX_SUMMARY_LENGTH:
            half_length = MAX_SUMMARY_LENGTH // 2
            summary = summary[:half_length] + "..." + summary[-(half_length - 3) :]

        return summary

    def _is_editor_state(self, history_entry: Dict[str, Any]) -> bool:
        """Return True if entry looks like editor UI state (not conversational)."""
        entry_str = str(history_entry).lower()
        # Check for editor state patterns
        if "editor" in entry_str and (
            "resource" in entry_str or "forcefile" in entry_str
        ):
            return True
        return False

    def _extract_text_content(self, conversation: Dict[str, Any]) -> str:
        """Extract text content from conversation for relevance scoring.

        Uses the same logic as create_conversation_summary for consistency.
        """
        if not conversation:
            return ""

        if isinstance(conversation, dict):
            return (
                conversation.get("text", "")
                or conversation.get("textDescription", "")
                or conversation.get("content", "")
                or conversation.get("message", "")
                or str(conversation)
            )
        return str(conversation)

    def score_conversation_relevance(
        self,
        conversation: Dict[str, Any],
        phrases: List[str],
        recency_scorer: Optional[Any] = None,
    ) -> float:
        """Score conversation relevance using exact phrase matching or recency.

        Scoring strategy:
        1. If phrases provided: 1.0 if ANY exact phrase found, 0.0 otherwise
        2. If no phrases: use recency scoring

        Args:
            conversation: Conversation data
            phrases: List of exact phrases to search for (case-insensitive)
            recency_scorer: Optional RecencyScorer instance

        Returns:
            Relevance score (0.0 or 1.0 for phrase match, 0.0-1.0 for recency)
        """
        if not conversation:
            return 0.0

        # If phrases provided, use exact phrase matching
        if phrases:
            conversation_text = self._extract_text_content(conversation).lower()

            for phrase in phrases:
                if phrase and phrase.lower() in conversation_text:
                    return 1.0
            return 0.0

        # No phrases: use recency scoring
        if recency_scorer:
            try:
                score: float = recency_scorer.calculate_recency_score(conversation)
                return score
            except Exception:
                pass

        # No scoring method available, return 0.0
        return 0.0

    def _truncate_relevance(self, relevance: float) -> float:
        """Truncate relevance score to 4 decimal places.

        Args:
            relevance: Raw relevance score

        Returns:
            Relevance truncated to 4 decimal places
        """
        return round(relevance, 4)

    def format_conversation_entry(
        self,
        conv_data: Dict[str, Any],
        include_prompts: bool,
        include_generations: bool,
        phrases: List[str] | None = None,
        include_editor_history: bool = DEFAULT_INCLUDE_EDITOR_HISTORY,
        recency_scorer: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Format a conversation entry with concise output for reduced context window impact.

        Args:
            conv_data: Conversation data dictionary
            include_prompts: Whether to include prompts in output
            include_generations: Whether to include generations in output
            phrases: List of search phrases for relevance scoring
            include_editor_history: Whether to include editor UI state entries
            recency_scorer: Optional RecencyScorer instance

        Returns:
            Formatted conversation entry dictionary with flattened structure
        """
        phrases = phrases or []

        if conv_data.get("error"):
            return {"status": "error", "error": conv_data["error"], "conversations": []}

        # Create concise summaries instead of full data
        conversations: List[Dict[str, Any]] = []

        if include_prompts and conv_data.get("prompts"):
            prompt_entries = self._process_entries(
                conv_data["prompts"],
                "prompt",
                phrases,
                recency_scorer,
            )
            conversations.extend(prompt_entries)

        if include_generations and conv_data.get("generations"):
            generation_entries = self._process_entries(
                conv_data["generations"],
                "generation",
                phrases,
                recency_scorer,
            )
            conversations.extend(generation_entries)

        if conv_data.get("history_entries"):
            history_list = conv_data["history_entries"]
            if not include_editor_history:
                history_list = [h for h in history_list if not self._is_editor_state(h)]
            history_entries = self._process_entries(
                history_list,
                "history",
                phrases,
                recency_scorer,
            )
            conversations.extend(history_entries)

        if phrases:
            conversations.sort(key=lambda x: x.get("relevance", 0), reverse=True)

        return {"status": "success", "conversations": conversations}

    def _process_entries(
        self,
        entries: List[Dict[str, Any]],
        entry_type: str,
        phrases: List[str],
        recency_scorer: Optional[Any],
    ) -> List[Dict[str, Any]]:
        """Process entries with phrase-aware limiting.

        When phrases are provided, returns ALL matches (no per-database limit).
        Global limit is applied later in the tool. Without phrases, limits first.

        Args:
            entries: List of conversation entries to process
            entry_type: Type label for the entries (prompt, generation, history)
            phrases: List of search phrases for relevance scoring
            recency_scorer: Optional RecencyScorer instance

        Returns:
            List of processed entry dictionaries
        """
        result: List[Dict[str, Any]] = []

        if phrases:
            # With phrases: score all, filter matches, NO per-database limit
            # Global limit is applied in recall_conversations_tool.py
            for entry_data in entries:
                relevance = self._truncate_relevance(
                    self.score_conversation_relevance(
                        entry_data, phrases, recency_scorer
                    )
                )
                if relevance > 0:
                    summary = self.create_conversation_summary(entry_data)
                    result.append(
                        {
                            "summary": summary,
                            "type": entry_type,
                            "relevance": relevance,
                        }
                    )
        else:
            # Without phrases: limit first, then score for recency
            for entry_data in entries[:MAX_SUMMARY_ENTRIES]:
                summary = self.create_conversation_summary(entry_data)
                relevance = self._truncate_relevance(
                    self.score_conversation_relevance(
                        entry_data, phrases, recency_scorer
                    )
                )
                entry: Dict[str, Any] = {
                    "summary": summary,
                    "type": entry_type,
                }
                if relevance > 0:
                    entry["relevance"] = relevance
                result.append(entry)

        return result
