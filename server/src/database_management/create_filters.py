"""
Search filter creation for conversation recall operations.
"""

from typing import List


class SearchFilterBuilder:
    """Builds SQL search conditions and parameters for phrase matching."""

    def build_search_conditions(
        self, phrases: List[str]
    ) -> tuple[List[str], List[str]]:
        """Build SQL search conditions for exact phrase matching.

        Multiple phrases are combined with OR logic - matches if ANY phrase is found.

        Args:
            phrases: List of exact phrases to search for (case-insensitive)

        Returns:
            Tuple of (search_conditions, search_params)
        """
        if not phrases:
            return [], []

        # Build OR conditions for multiple phrases
        conditions = []
        params = []

        for phrase in phrases:
            if phrase:
                conditions.append("value LIKE ?")
                params.append(f"%{phrase}%")

        return conditions, params
