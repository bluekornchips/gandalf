"""
Simple conversation filtering for Gandalf MCP Server.

This module implements basic keyword-based filtering to find relevant conversations
based on user prompts and project context.
"""

import re
from pathlib import Path
from typing import Any

from src.config.constants.conversation import (
    CONVERSATION_DOMAIN_WORD_EXCLUSIONS,
    CONVERSATION_DOMAIN_WORD_LIMIT,
    CONVERSATION_DOMAIN_WORD_MIN_LENGTH,
    CONVERSATION_FILE_PATTERNS,
    CONVERSATION_FILTERING_ENABLED,
    CONVERSATION_KEYWORD_EXTRACTION_LIMIT,
    CONVERSATION_KEYWORD_MATCH_ENABLED,
    CONVERSATION_TECH_PATTERNS,
)
from src.core.conversation_analysis import generate_shared_context_keywords
from src.utils.common import log_debug, log_error, log_info


class ConversationFilter:
    """Simple conversation filtering based on keyword matching."""

    def __init__(self, project_root: Path, user_prompt: str | None = None):
        """Initialize the conversation filter.

        Args:
            project_root: Project root directory for context generation
            user_prompt: Optional user prompt for keyword extraction
        """
        self.project_root = project_root
        self.user_prompt = user_prompt
        self.base_keywords = generate_shared_context_keywords(project_root)
        self.prompt_keywords = self._extract_prompt_keywords() if user_prompt else []
        self.all_keywords = self._merge_keywords()

        log_debug(
            f"Conversation filter initialized with {len(self.all_keywords)} keywords"
        )

    def _extract_prompt_keywords(self) -> list[str]:
        """Extract keywords from user prompt."""
        if not self.user_prompt or not CONVERSATION_KEYWORD_MATCH_ENABLED:
            return []

        try:
            prompt_lower = self.user_prompt.lower()
            keywords = []

            # Extract technical terms using patterns from constants
            for pattern in CONVERSATION_TECH_PATTERNS:
                matches = re.findall(pattern, prompt_lower, re.IGNORECASE)
                keywords.extend(matches)

            # Extract file references using patterns from constants
            for pattern in CONVERSATION_FILE_PATTERNS:
                matches = re.findall(pattern, prompt_lower)
                keywords.extend([m for m in matches if "." in m or "/" in m])

            # Extract domain-specific terms
            domain_words = [
                word
                for word in prompt_lower.split()
                if len(word) > CONVERSATION_DOMAIN_WORD_MIN_LENGTH
                and word.isalpha()
                and word not in CONVERSATION_DOMAIN_WORD_EXCLUSIONS
            ]

            keywords.extend(domain_words[:CONVERSATION_DOMAIN_WORD_LIMIT])

            # Remove duplicates and limit
            unique_keywords = list(set(keywords))
            limited_keywords = unique_keywords[:CONVERSATION_KEYWORD_EXTRACTION_LIMIT]

            log_debug(f"Extracted {len(limited_keywords)} keywords from prompt")
            return limited_keywords

        except (ValueError, TypeError, AttributeError) as e:
            log_error(e, "extracting keywords from prompt")
            return []

    def _merge_keywords(self) -> list[str]:
        """Merge base project keywords with prompt keywords."""
        if not self.prompt_keywords:
            return self.base_keywords

        # Combine keywords, prioritizing prompt keywords
        combined = self.prompt_keywords + self.base_keywords

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for keyword in combined:
            if keyword.lower() not in seen:
                seen.add(keyword.lower())
                unique_keywords.append(keyword)

        return unique_keywords

    def _conversation_matches_keywords(self, conversation: dict[str, Any]) -> bool:
        """Check if conversation matches any of our keywords."""
        if not self.all_keywords:
            return True  # If no keywords, include all conversations

        # Get conversation text from various possible fields
        text_fields = [
            "content",
            "snippet",
            "title",
            "user_query",
            "ai_response",
        ]  # move to constants
        conversation_text = ""

        for field in text_fields:
            if field in conversation and conversation[field]:
                conversation_text += " " + str(conversation[field])

        if not conversation_text.strip():
            return False

        conversation_text_lower = conversation_text.lower()

        # Check if any keyword matches
        for keyword in self.all_keywords:
            if keyword.lower() in conversation_text_lower:
                return True

        return False

    def apply_conversation_filtering(
        self, conversations: list[dict[str, Any]], requested_limit: int
    ) -> list[dict[str, Any]]:
        """Apply simple keyword-based filtering."""

        if not CONVERSATION_FILTERING_ENABLED:
            return conversations[:requested_limit]

        if not CONVERSATION_KEYWORD_MATCH_ENABLED:
            return conversations[:requested_limit]

        # Filter conversations that match keywords
        matching_conversations = []
        for conv in conversations:
            if self._conversation_matches_keywords(conv):
                matching_conversations.append(conv)

        # Return up to the requested limit
        filtered_conversations = matching_conversations[:requested_limit]

        log_info(
            f"Conversation filtering: {len(conversations)} -> "
            f"{len(filtered_conversations)} conversations "
            f"(keyword matched: {len(matching_conversations)})"
        )

        return filtered_conversations

    def get_filtering_summary(self) -> dict[str, Any]:
        """Get a summary of the filtering configuration."""
        return {
            "conversation_filtering_enabled": CONVERSATION_FILTERING_ENABLED,
            "keyword_match_enabled": CONVERSATION_KEYWORD_MATCH_ENABLED,
            "base_keywords_count": len(self.base_keywords),
            "prompt_keywords_count": len(self.prompt_keywords),
            "total_keywords_count": len(self.all_keywords),
            "sample_keywords": self.all_keywords[:10],
        }


def create_conversation_filter(
    project_root: Path, user_prompt: str | None = None
) -> ConversationFilter:
    """Factory function to create a conversation filter."""
    return ConversationFilter(project_root, user_prompt)


def apply_conversation_filtering(
    conversations: list[dict[str, Any]],
    project_root: Path,
    requested_limit: int = 20,
    user_prompt: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply conversation filtering and return filtered conversations with metadata.

    Args:
        conversations: List of conversations to filter
        project_root: Project root directory
        requested_limit: Maximum number of conversations to return
        user_prompt: Optional user prompt for keyword extraction

    Returns:
        Tuple of (filtered_conversations, filtering_metadata)
    """

    if not CONVERSATION_FILTERING_ENABLED:
        limited_conversations = conversations[:requested_limit]
        return limited_conversations, {
            "mode": "simple_limit",
            "original_count": len(conversations),
            "filtered_count": len(limited_conversations),
            "conversation_filtering_enabled": False,
            "keyword_match_enabled": False,
        }

    # Create conversation filter
    conversation_filter = create_conversation_filter(project_root, user_prompt)

    # Apply filtering
    filtered_conversations = conversation_filter.apply_conversation_filtering(
        conversations, requested_limit
    )

    # Get filtering metadata
    filtering_metadata = conversation_filter.get_filtering_summary()
    filtering_metadata["mode"] = "keyword_filtering"
    filtering_metadata["original_count"] = len(conversations)
    filtering_metadata["filtered_count"] = len(filtered_conversations)

    return filtered_conversations, filtering_metadata
