"""
Tests for create_filters module.
"""

from src.database_management.create_filters import SearchFilterBuilder


class TestSearchFilterBuilder:
    """Test suite for SearchFilterBuilder class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.filter_builder = SearchFilterBuilder()

    def test_build_search_conditions_empty_phrases(self) -> None:
        """Test build_search_conditions with empty phrases list."""
        conditions, params = self.filter_builder.build_search_conditions([])

        assert conditions == []
        assert params == []

    def test_build_search_conditions_single_phrase(self) -> None:
        """Test build_search_conditions with single phrase."""
        conditions, params = self.filter_builder.build_search_conditions(["python"])

        assert len(conditions) == 1
        assert conditions[0] == "value LIKE ?"
        assert len(params) == 1
        assert params[0] == "%python%"

    def test_build_search_conditions_multi_word_phrase(self) -> None:
        """Test build_search_conditions with multi-word phrase."""
        conditions, params = self.filter_builder.build_search_conditions(
            ["python programming"]
        )

        assert len(conditions) == 1
        assert conditions[0] == "value LIKE ?"
        assert len(params) == 1
        assert params[0] == "%python programming%"

    def test_build_search_conditions_multiple_phrases(self) -> None:
        """Test build_search_conditions with multiple phrases (OR logic)."""
        conditions, params = self.filter_builder.build_search_conditions(
            ["fuck you", "follow the rules", "monkey"]
        )

        # Each phrase gets its own condition
        assert len(conditions) == 3
        assert all(c == "value LIKE ?" for c in conditions)
        assert len(params) == 3
        assert "%fuck you%" in params
        assert "%follow the rules%" in params
        assert "%monkey%" in params

    def test_sql_injection_protection(self) -> None:
        """Test that SQL queries are protected against injection attacks."""
        malicious_phrases = ["'; DROP TABLE ItemTable; --"]
        conditions, params = self.filter_builder.build_search_conditions(
            malicious_phrases
        )

        # Should be safely parameterized
        assert len(conditions) == 1
        assert conditions[0] == "value LIKE ?"
        assert len(params) == 1
        assert params[0] == "%'; DROP TABLE ItemTable; --%"

    def test_filters_empty_strings(self) -> None:
        """Test that empty strings in phrases list are filtered out."""
        conditions, params = self.filter_builder.build_search_conditions(
            ["python", "", "java"]
        )

        assert len(conditions) == 2
        assert "%python%" in params
        assert "%java%" in params
