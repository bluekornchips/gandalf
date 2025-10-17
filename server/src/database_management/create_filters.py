"""
Search filter creation for conversation recall operations.
"""

from typing import List

from src.config.constants import IGNORED_KEYWORDS, MAX_KEYWORDS


class SearchFilterBuilder:
    """Builds SQL search conditions and parameters for keywords."""

    def build_search_conditions(self, keywords: str) -> tuple[List[str], List[str]]:
        """Build SQL search conditions and parameters for keywords.

        Args:
            keywords: Keywords to search for

        Returns:
            Tuple of (search_conditions, search_params)
        """
        if not keywords:
            return [], []

        keyword_words = keywords.lower().split()
        meaningful_words = [
            word for word in keyword_words if word not in IGNORED_KEYWORDS
        ]

        if len(meaningful_words) > MAX_KEYWORDS:
            meaningful_words = meaningful_words[:MAX_KEYWORDS]

        # If no meaningful words remain, use original keywords, but also limited
        if not meaningful_words:
            search_terms = keyword_words[:MAX_KEYWORDS]
        else:
            search_terms = meaningful_words

        conditions = []
        params = []

        for term in search_terms:
            # Search in JSON content using LIKE with wildcards, yay sqlite
            condition = "value LIKE ?"
            conditions.append(condition)
            params.append(f"%{term}%")

        return conditions, params
