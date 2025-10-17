"""
Output formatting for conversation recall operations.
"""

import os
from typing import Any, Dict, List, TypedDict

from src.config.constants import MAX_SUMMARY_LENGTH, MAX_SUMMARY_ENTRIES


class ConversationSummary(TypedDict):
    """Type definition for conversation summary entries."""

    id: str
    summary: str
    type: str
    relevance: float


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
            summary = summary[: MAX_SUMMARY_LENGTH - 3] + "..."

        return summary

    def score_conversation_relevance(
        self, conversation: Dict[str, Any], keywords: str
    ) -> float:
        """Score conversation relevance based on keyword matches.

        Args:
            conversation: Conversation data
            keywords: Search keywords

        Returns:
            Relevance score (0.0 to 1.0)
        """
        if not keywords or not conversation:
            return 0.0

        keyword_words = keywords.lower().split()
        conversation_text = str(conversation).lower()

        matches = sum(1 for word in keyword_words if word in conversation_text)
        return matches / len(keyword_words) if keyword_words else 0.0

    def format_conversation_entry(
        self,
        conv_data: Dict[str, Any],
        include_prompts: bool,
        include_generations: bool,
        keywords: str = "",
    ) -> Dict[str, Any]:
        """Format a conversation entry with concise output for reduced context window impact.

        Args:
            conv_data: Conversation data dictionary
            include_prompts: Whether to include prompts in output
            include_generations: Whether to include generations in output
            keywords: Search keywords for relevance scoring

        Returns:
            Formatted conversation entry dictionary
        """
        # Extract database filename only for cleaner output
        db_path = conv_data.get("database_path", "")
        db_filename = os.path.basename(db_path) if db_path else "unknown"

        formatted = {
            "source": db_filename,
            "status": "success" if not conv_data.get("error") else "error",
            "total_conversations": (
                len(conv_data.get("prompts", [])) if include_prompts else 0
            )
            + (len(conv_data.get("generations", [])) if include_generations else 0)
            + len(conv_data.get("history_entries", [])),
        }

        if conv_data.get("error"):
            formatted["error"] = conv_data["error"]
        else:
            # Create concise summaries instead of full data
            conversations: List[ConversationSummary] = []

            # Process prompts
            if include_prompts and conv_data.get("prompts"):
                for i, prompt in enumerate(conv_data["prompts"][:MAX_SUMMARY_ENTRIES]):
                    summary = self.create_conversation_summary(prompt)
                    relevance = self.score_conversation_relevance(prompt, keywords)
                    conversations.append(
                        {
                            "id": f"prompt_{i}",
                            "summary": summary,
                            "type": "prompt",
                            "relevance": relevance,
                        }
                    )

            # Process generations
            if include_generations and conv_data.get("generations"):
                for i, generation in enumerate(
                    conv_data["generations"][:MAX_SUMMARY_ENTRIES]
                ):
                    summary = self.create_conversation_summary(generation)
                    relevance = self.score_conversation_relevance(generation, keywords)
                    conversations.append(
                        {
                            "id": f"generation_{i}",
                            "summary": summary,
                            "type": "generation",
                            "relevance": relevance,
                        }
                    )

            # Process history entries
            if conv_data.get("history_entries"):
                for i, history in enumerate(
                    conv_data["history_entries"][:MAX_SUMMARY_ENTRIES]
                ):
                    summary = self.create_conversation_summary(history)
                    relevance = self.score_conversation_relevance(history, keywords)
                    conversations.append(
                        {
                            "id": f"history_{i}",
                            "summary": summary,
                            "type": "history",
                            "relevance": relevance,
                        }
                    )

            # Sort by relevance if keywords provided
            if keywords:
                conversations.sort(key=lambda x: x["relevance"], reverse=True)

            formatted["conversations"] = conversations

        return formatted
