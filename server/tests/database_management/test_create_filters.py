"""
Tests for create_filters module.
"""

from src.database_management.create_filters import SearchFilterBuilder
from src.config.constants import MAX_KEYWORDS


class TestSearchFilterBuilder:
    """Test suite for SearchFilterBuilder class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.filter_builder = SearchFilterBuilder()

    def test_build_search_conditions_empty_keywords(self) -> None:
        """Test build_search_conditions with empty keywords."""
        conditions, params = self.filter_builder.build_search_conditions("")

        assert conditions == []
        assert params == []

    def test_build_search_conditions_single_keyword(self) -> None:
        """Test build_search_conditions with single keyword."""
        conditions, params = self.filter_builder.build_search_conditions("python")

        assert len(conditions) == 1
        assert conditions[0] == "value LIKE ?"
        assert len(params) == 1
        assert params[0] == "%python%"

    def test_build_search_conditions_multiple_keywords(self) -> None:
        """Test build_search_conditions with multiple keywords."""
        conditions, params = self.filter_builder.build_search_conditions(
            "python programming"
        )

        assert len(conditions) == 2
        assert all(condition == "value LIKE ?" for condition in conditions)
        assert len(params) == 2
        assert "%python%" in params
        assert "%programming%" in params

    def test_build_search_conditions_ignored_keywords(self) -> None:
        """Test build_search_conditions filters out ignored keywords."""
        conditions, params = self.filter_builder.build_search_conditions(
            "the python and programming"
        )

        # Should filter out "the" and "and"
        assert len(conditions) == 2
        assert "%python%" in params
        assert "%programming%" in params
        assert "%the%" not in params
        assert "%and%" not in params

    def test_build_search_conditions_only_ignored_keywords(self) -> None:
        """Test build_search_conditions with only ignored keywords."""
        conditions, params = self.filter_builder.build_search_conditions("the and or")

        # Should use original keywords when no meaningful words remain
        assert len(conditions) == 3
        assert "%the%" in params
        assert "%and%" in params
        assert "%or%" in params

    def test_build_search_conditions_max_keywords_limit(self) -> None:
        """Test build_search_conditions respects MAX_KEYWORDS limit."""
        long_keywords = " ".join([f"word{i}" for i in range(MAX_KEYWORDS + 5)])
        conditions, params = self.filter_builder.build_search_conditions(long_keywords)

        # Should limit to MAX_KEYWORDS
        assert len(conditions) <= MAX_KEYWORDS
        assert len(params) <= MAX_KEYWORDS

    def test_sql_injection_protection(self) -> None:
        """Test that SQL queries are protected against injection attacks."""
        # Test with potentially malicious keywords
        malicious_keywords = "'; DROP TABLE ItemTable; --"
        conditions, params = self.filter_builder.build_search_conditions(
            malicious_keywords
        )

        # Should be safely parameterized
        assert all(condition == "value LIKE ?" for condition in conditions)
        assert all(
            isinstance(param, str) and param.startswith("%") and param.endswith("%")
            for param in params
        )

    def test_case_insensitive_search(self) -> None:
        """Test that search conditions handle case insensitivity."""
        conditions, params = self.filter_builder.build_search_conditions(
            "PYTHON Programming"
        )

        # Keywords should be converted to lowercase
        assert "%python%" in params
        assert "%programming%" in params
        assert "%PYTHON%" not in params
