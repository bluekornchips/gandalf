"""
Output formatting for conversation recall operations.
"""

import os
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
            summary = summary[:half_length] + "..." + summary[-(half_length - 3):]

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

    def score_conversation_relevance(
        self, conversation: Dict[str, Any], keywords: str, recency_scorer: Optional[Any] = None
    ) -> Optional[float]:
        """Score conversation relevance using keyword matching or recency.

        Args:
            conversation: Conversation data
            keywords: Search keywords
            recency_scorer: Optional RecencyScorer instance

        Returns:
            Relevance score (0.0 to 1.0), or None if not applicable
        """
        if not conversation:
            return None

        # If keywords provided, use keyword matching
        if keywords:
            keyword_words = keywords.lower().split()
            conversation_text = str(conversation).lower()
            matches = sum(1 for word in keyword_words if word in conversation_text)
            return matches / len(keyword_words) if keyword_words else 0.0

        # No keywords: use recency scoring
        if recency_scorer:
            try:
                return recency_scorer.calculate_recency_score(conversation)
            except Exception:
                pass

        # No scoring method available
        return None

    def format_conversation_entry(
        self,
        conv_data: Dict[str, Any],
        include_prompts: bool,
        include_generations: bool,
        keywords: str = "",
        include_editor_history: bool = DEFAULT_INCLUDE_EDITOR_HISTORY,
        recency_scorer: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Format a conversation entry with concise output for reduced context window impact.

        Args:
            conv_data: Conversation data dictionary
            include_prompts: Whether to include prompts in output
            include_generations: Whether to include generations in output
            keywords: Search keywords for relevance scoring
            include_editor_history: Whether to include editor UI state entries
            recency_scorer: Optional RecencyScorer instance

        Returns:
            Formatted conversation entry dictionary
        """
        formatted: Dict[str, Any] = {
            "status": "success" if not conv_data.get("error") else "error",
        }

        if conv_data.get("error"):
            formatted["error"] = conv_data["error"]
        else:
            # Create concise summaries instead of full data
            conversations: List[Dict[str, Any]] = []

            # Process prompts
            if include_prompts and conv_data.get("prompts"):
                for prompt in conv_data["prompts"][:MAX_SUMMARY_ENTRIES]:
                    summary = self.create_conversation_summary(prompt)
                    relevance = self.score_conversation_relevance(prompt, keywords, recency_scorer)
                    entry: Dict[str, Any] = {
                        "summary": summary,
                        "type": "prompt",
                    }
                    if relevance is not None and relevance > 0.0:
                        entry["relevance"] = relevance
                    conversations.append(entry)

            # Process generations
            if include_generations and conv_data.get("generations"):
                for generation in conv_data["generations"][:MAX_SUMMARY_ENTRIES]:
                    summary = self.create_conversation_summary(generation)
                    relevance = self.score_conversation_relevance(generation, keywords, recency_scorer)
                    entry: Dict[str, Any] = {
                        "summary": summary,
                        "type": "generation",
                    }
                    if relevance is not None and relevance > 0.0:
                        entry["relevance"] = relevance
                    conversations.append(entry)

            # Process history entries
            if conv_data.get("history_entries"):
                for history in conv_data["history_entries"][:MAX_SUMMARY_ENTRIES]:
                    if not include_editor_history and self._is_editor_state(history):
                        continue
                    summary = self.create_conversation_summary(history)
                    relevance = self.score_conversation_relevance(history, keywords, recency_scorer)
                    entry: Dict[str, Any] = {
                        "summary": summary,
                        "type": "history",
                    }
                    if relevance is not None and relevance > 0.0:
                        entry["relevance"] = relevance
                    conversations.append(entry)

            # Sort by relevance if available
            if any(c.get("relevance") is not None for c in conversations):
                conversations.sort(key=lambda x: x.get("relevance", 0.0), reverse=True)

            formatted["conversations"] = conversations

        return formatted
