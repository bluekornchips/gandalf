"""Tests for parameter validation functionality."""

from dataclasses import dataclass
from typing import Any

import pytest

# Mock the configuration constants for testing
CONVERSATION_DEFAULT_LIMIT = 50
CONVERSATION_MAX_LIMIT = 200
CONVERSATION_DEFAULT_LOOKBACK_DAYS = 30
CONVERSATION_MAX_LOOKBACK_DAYS = 90
CONVERSATION_DEFAULT_MIN_SCORE = 0.0
CONVERSATION_DEFAULT_FAST_MODE = True


# Mock the proposed ConversationParameters and ParameterValidator classes
@dataclass(frozen=True)
class ConversationParameters:
    """Validated conversation query parameters."""

    limit: int
    min_relevance_score: float
    days_lookback: int
    fast_mode: bool
    conversation_types: list[str] | None
    tools: list[str] | None
    user_prompt: str | None
    search_query: str | None
    tags: list[str] | None


class ParameterValidator:
    """Centralized parameter validation for all conversation tools."""

    @staticmethod
    def validate_conversation_params(
        arguments: dict[str, Any],
    ) -> ConversationParameters:
        """Validate and normalize conversation parameters."""
        return ConversationParameters(
            limit=max(
                1,
                min(
                    int(arguments.get("limit", CONVERSATION_DEFAULT_LIMIT)),
                    CONVERSATION_MAX_LIMIT,
                ),
            ),
            min_relevance_score=max(
                0.0,
                float(
                    arguments.get("min_relevance_score", CONVERSATION_DEFAULT_MIN_SCORE)
                ),
            ),
            days_lookback=max(
                1,
                min(
                    int(
                        arguments.get(
                            "days_lookback", CONVERSATION_DEFAULT_LOOKBACK_DAYS
                        )
                    ),
                    CONVERSATION_MAX_LOOKBACK_DAYS,
                ),
            ),
            fast_mode=bool(arguments.get("fast_mode", CONVERSATION_DEFAULT_FAST_MODE)),
            conversation_types=arguments.get("conversation_types"),
            tools=arguments.get("tools"),
            user_prompt=arguments.get("user_prompt"),
            search_query=arguments.get("search_query"),
            tags=arguments.get("tags"),
        )


class TestParameterValidator:
    """Test parameter validation functionality."""

    def test_default_parameter_validation(self):
        """Test validation with empty arguments uses defaults."""
        result = ParameterValidator.validate_conversation_params({})

        assert result.limit == CONVERSATION_DEFAULT_LIMIT
        assert result.min_relevance_score == CONVERSATION_DEFAULT_MIN_SCORE
        assert result.days_lookback == CONVERSATION_DEFAULT_LOOKBACK_DAYS
        assert result.fast_mode == CONVERSATION_DEFAULT_FAST_MODE
        assert result.conversation_types is None
        assert result.tools is None
        assert result.user_prompt is None
        assert result.search_query is None
        assert result.tags is None

    def test_limit_parameter_validation(self):
        """Test limit parameter validation and clamping."""
        # Test normal valid limit
        result = ParameterValidator.validate_conversation_params({"limit": 100})
        assert result.limit == 100

        # Test minimum clamping
        result = ParameterValidator.validate_conversation_params({"limit": 0})
        assert result.limit == 1

        result = ParameterValidator.validate_conversation_params({"limit": -10})
        assert result.limit == 1

        # Test maximum clamping
        result = ParameterValidator.validate_conversation_params({"limit": 500})
        assert result.limit == CONVERSATION_MAX_LIMIT

        # Test string conversion
        result = ParameterValidator.validate_conversation_params({"limit": "75"})
        assert result.limit == 75

        # Test float conversion
        result = ParameterValidator.validate_conversation_params({"limit": 50.7})
        assert result.limit == 50

    def test_min_relevance_score_validation(self):
        """Test min_relevance_score parameter validation."""
        # Test normal valid score
        result = ParameterValidator.validate_conversation_params(
            {"min_relevance_score": 0.5}
        )
        assert result.min_relevance_score == 0.5

        # Test minimum clamping (no negative scores)
        result = ParameterValidator.validate_conversation_params(
            {"min_relevance_score": -0.1}
        )
        assert result.min_relevance_score == 0.0

        # Test values above 1.0 are allowed (for flexibility)
        result = ParameterValidator.validate_conversation_params(
            {"min_relevance_score": 1.5}
        )
        assert result.min_relevance_score == 1.5

        # Test string conversion
        result = ParameterValidator.validate_conversation_params(
            {"min_relevance_score": "0.8"}
        )
        assert result.min_relevance_score == 0.8

    def test_days_lookback_validation(self):
        """Test days_lookback parameter validation and clamping."""
        # Test normal valid days
        result = ParameterValidator.validate_conversation_params({"days_lookback": 45})
        assert result.days_lookback == 45

        # Test minimum clamping
        result = ParameterValidator.validate_conversation_params({"days_lookback": 0})
        assert result.days_lookback == 1

        result = ParameterValidator.validate_conversation_params({"days_lookback": -5})
        assert result.days_lookback == 1

        # Test maximum clamping
        result = ParameterValidator.validate_conversation_params({"days_lookback": 120})
        assert result.days_lookback == CONVERSATION_MAX_LOOKBACK_DAYS

        # Test string conversion
        result = ParameterValidator.validate_conversation_params(
            {"days_lookback": "60"}
        )
        assert result.days_lookback == 60

    def test_fast_mode_validation(self):
        """Test fast_mode parameter validation."""
        # Test boolean true
        result = ParameterValidator.validate_conversation_params({"fast_mode": True})
        assert result.fast_mode is True

        # Test boolean false
        result = ParameterValidator.validate_conversation_params({"fast_mode": False})
        assert result.fast_mode is False

        # Test truthy values
        result = ParameterValidator.validate_conversation_params({"fast_mode": 1})
        assert result.fast_mode is True

        result = ParameterValidator.validate_conversation_params({"fast_mode": "true"})
        assert result.fast_mode is True

        # Test falsy values
        result = ParameterValidator.validate_conversation_params({"fast_mode": 0})
        assert result.fast_mode is False

        result = ParameterValidator.validate_conversation_params({"fast_mode": ""})
        assert result.fast_mode is False

    def test_optional_list_parameters(self):
        """Test optional list parameters are handled correctly."""
        # Test with list values
        arguments = {
            "conversation_types": ["technical", "debugging"],
            "tools": ["cursor", "claude-code"],
            "tags": ["authentication", "bug"],
        }

        result = ParameterValidator.validate_conversation_params(arguments)

        assert result.conversation_types == ["technical", "debugging"]
        assert result.tools == ["cursor", "claude-code"]
        assert result.tags == ["authentication", "bug"]

        # Test with empty lists
        arguments = {"conversation_types": [], "tools": [], "tags": []}

        result = ParameterValidator.validate_conversation_params(arguments)

        assert result.conversation_types == []
        assert result.tools == []
        assert result.tags == []

    def test_optional_string_parameters(self):
        """Test optional string parameters are handled correctly."""
        arguments = {
            "user_prompt": "Help me debug this authentication issue",
            "search_query": "login error",
        }

        result = ParameterValidator.validate_conversation_params(arguments)

        assert result.user_prompt == "Help me debug this authentication issue"
        assert result.search_query == "login error"

        # Test with empty strings
        arguments = {"user_prompt": "", "search_query": ""}

        result = ParameterValidator.validate_conversation_params(arguments)

        assert result.user_prompt == ""
        assert result.search_query == ""

    def test_complete_parameter_set(self):
        """Test validation with all parameters provided."""
        arguments = {
            "limit": 75,
            "min_relevance_score": 0.6,
            "days_lookback": 14,
            "fast_mode": False,
            "conversation_types": ["architecture", "code_discussion"],
            "tools": ["cursor"],
            "user_prompt": "How does authentication work in this system?",
            "search_query": "auth flow",
            "tags": ["security", "login"],
        }

        result = ParameterValidator.validate_conversation_params(arguments)

        assert result.limit == 75
        assert result.min_relevance_score == 0.6
        assert result.days_lookback == 14
        assert result.fast_mode is False
        assert result.conversation_types == ["architecture", "code_discussion"]
        assert result.tools == ["cursor"]
        assert result.user_prompt == "How does authentication work in this system?"
        assert result.search_query == "auth flow"
        assert result.tags == ["security", "login"]

    def test_parameter_immutability(self):
        """Test that ConversationParameters is immutable."""
        result = ParameterValidator.validate_conversation_params({"limit": 50})

        # Verify it's frozen (dataclass)
        with pytest.raises(AttributeError):
            result.limit = 100

    def test_type_conversion_errors(self):
        """Test handling of invalid type conversions."""
        # Test invalid limit conversion
        with pytest.raises(ValueError):
            ParameterValidator.validate_conversation_params({"limit": "invalid"})

        # Test invalid float conversion
        with pytest.raises(ValueError):
            ParameterValidator.validate_conversation_params(
                {"min_relevance_score": "not_a_number"}
            )

        # Test invalid days_lookback conversion
        with pytest.raises(ValueError):
            ParameterValidator.validate_conversation_params(
                {"days_lookback": "invalid_days"}
            )

    @pytest.mark.parametrize(
        "limit_value,expected_limit",
        [
            (1, 1),
            (50, 50),
            (200, 200),
            (0, 1),  # minimum clamp
            (-10, 1),  # minimum clamp
            (300, 200),  # maximum clamp
            (150.9, 150),  # float conversion
            ("75", 75),  # string conversion
        ],
    )
    def test_limit_boundary_conditions(self, limit_value, expected_limit):
        """Test limit parameter boundary conditions."""
        result = ParameterValidator.validate_conversation_params({"limit": limit_value})
        assert result.limit == expected_limit

    @pytest.mark.parametrize(
        "score_value,expected_score",
        [
            (0.0, 0.0),
            (0.5, 0.5),
            (1.0, 1.0),
            (1.5, 1.5),  # Allow values > 1.0
            (-0.1, 0.0),  # minimum clamp
            ("0.7", 0.7),  # string conversion
        ],
    )
    def test_relevance_score_boundary_conditions(self, score_value, expected_score):
        """Test relevance score parameter boundary conditions."""
        result = ParameterValidator.validate_conversation_params(
            {"min_relevance_score": score_value}
        )
        assert result.min_relevance_score == expected_score

    @pytest.mark.parametrize(
        "days_value,expected_days",
        [
            (1, 1),
            (30, 30),
            (90, 90),
            (0, 1),  # minimum clamp
            (-5, 1),  # minimum clamp
            (120, 90),  # maximum clamp
            (45.7, 45),  # float conversion
            ("60", 60),  # string conversion
        ],
    )
    def test_days_lookback_boundary_conditions(self, days_value, expected_days):
        """Test days_lookback parameter boundary conditions."""
        result = ParameterValidator.validate_conversation_params(
            {"days_lookback": days_value}
        )
        assert result.days_lookback == expected_days

    def test_none_values_handling(self):
        """Test handling of None values for optional parameters."""
        arguments = {
            "conversation_types": None,
            "tools": None,
            "user_prompt": None,
            "search_query": None,
            "tags": None,
        }

        result = ParameterValidator.validate_conversation_params(arguments)

        assert result.conversation_types is None
        assert result.tools is None
        assert result.user_prompt is None
        assert result.search_query is None
        assert result.tags is None

    def test_parameter_types(self):
        """Test that parameters have correct types after validation."""
        arguments = {
            "limit": "100",  # string -> int
            "min_relevance_score": "0.5",  # string -> float
            "days_lookback": "30",  # string -> int
            "fast_mode": "true",  # string -> bool
        }

        result = ParameterValidator.validate_conversation_params(arguments)

        assert isinstance(result.limit, int)
        assert isinstance(result.min_relevance_score, float)
        assert isinstance(result.days_lookback, int)
        assert isinstance(result.fast_mode, bool)

    def test_real_world_usage_scenarios(self):
        """Test realistic parameter combinations."""
        # Scenario 1: Quick search with high relevance
        args1 = {
            "limit": 25,
            "min_relevance_score": 0.8,
            "fast_mode": True,
            "search_query": "authentication bug",
        }
        result1 = ParameterValidator.validate_conversation_params(args1)
        assert result1.limit == 25
        assert result1.min_relevance_score == 0.8
        assert result1.fast_mode is True
        assert result1.search_query == "authentication bug"

        # Scenario 2: Deep analysis with specific tools
        args2 = {
            "limit": 150,
            "days_lookback": 60,
            "fast_mode": False,
            "tools": ["cursor", "claude-code"],
            "conversation_types": ["technical", "debugging"],
        }
        result2 = ParameterValidator.validate_conversation_params(args2)
        assert result2.limit == 150
        assert result2.days_lookback == 60
        assert result2.fast_mode is False
        assert result2.tools == ["cursor", "claude-code"]
        assert result2.conversation_types == ["technical", "debugging"]
