"""
Recency scoring for conversation recall based on conversation timestamps.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.config.constants import RECENCY_DECAY_RATE

logger = logging.getLogger(__name__)


class RecencyScorer:
    """Calculates recency scores for conversations based on timestamps."""

    def __init__(self, decay_rate: float = RECENCY_DECAY_RATE) -> None:
        """Initialize the recency scorer.

        Args:
            decay_rate: Rate of exponential decay for recency scoring.
                       Higher values mean older conversations decay faster.
        """
        self.decay_rate = decay_rate

    def extract_timestamp(self, conversation: Dict[str, Any]) -> Optional[datetime]:
        """Extract timestamp from conversation data.

        Looks for timestamp in common locations:
        - timestamp
        - createdAt
        - date
        - time
        - created_at

        Args:
            conversation: Conversation data dictionary.

        Returns:
            Datetime object if found, None otherwise.
        """
        if not isinstance(conversation, dict):
            return None

        # Try common timestamp field names
        timestamp_fields = [
            "timestamp",
            "createdAt",
            "date",
            "time",
            "created_at",
            "created",
        ]

        for field in timestamp_fields:
            if field in conversation:
                value = conversation[field]
                if isinstance(value, (int, float)):
                    # Unix timestamp (seconds or milliseconds)
                    if value > 1e10:  # Milliseconds
                        value = value / 1000
                    return datetime.fromtimestamp(value, tz=timezone.utc)
                elif isinstance(value, str):
                    # Try parsing ISO format
                    try:
                        return datetime.fromisoformat(value.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        pass

        # Check nested structures
        if "metadata" in conversation and isinstance(conversation["metadata"], dict):
            return self.extract_timestamp(conversation["metadata"])

        return None

    def calculate_recency_score(self, conversation: Dict[str, Any]) -> float:
        """Calculate recency score based on conversation age.

        Uses exponential decay: score = 1.0 / (1.0 + decay_rate * days_old)

        Args:
            conversation: Conversation data dictionary.

        Returns:
            Recency score between 0.0 and 1.0.
            Returns 0.5 if timestamp cannot be determined (neutral score).
        """
        timestamp = self.extract_timestamp(conversation)

        if timestamp is None:
            # neutral score
            return 0.5

        try:
            now = datetime.now(timezone.utc)
            if timestamp.tzinfo is None:
                # Assume UTC when no timezone info
                timestamp = timestamp.replace(tzinfo=timezone.utc)

            age_delta = now - timestamp
            days_old = age_delta.total_seconds() / (24 * 3600)

            # Exponential decay: 1.0 for new conversations, 0.0ish for old
            recency_score = 1.0 / (1.0 + self.decay_rate * days_old)

            return max(0.0, min(1.0, recency_score))
        except Exception as e:
            logger.warning(
                f"Recency scoring failed: {e}, returning neutral score 0.5",
                exc_info=True,
            )
            return 0.5
