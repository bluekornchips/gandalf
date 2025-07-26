"""Parameter validation for all conversation tools."""

from dataclasses import dataclass
from typing import Any

from src.config.conversation_config import (
    CONVERSATION_DEFAULT_FAST_MODE,
    CONVERSATION_DEFAULT_LIMIT,
    CONVERSATION_DEFAULT_LOOKBACK_DAYS,
    CONVERSATION_DEFAULT_MIN_SCORE,
    CONVERSATION_MAX_LIMIT,
    CONVERSATION_MAX_LOOKBACK_DAYS,
)


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
    include_analysis: bool


class ParameterValidator:
    """Parameter validation for all conversation tools."""

    @staticmethod
    def validate_conversation_params(
        arguments: dict[str, Any],
    ) -> ConversationParameters:
        """Validate and normalize conversation parameters."""
        # Extract and validate limit
        limit_raw = arguments.get("limit", CONVERSATION_DEFAULT_LIMIT)
        limit = max(1, min(int(limit_raw), CONVERSATION_MAX_LIMIT))

        # Extract and validate min_relevance_score
        min_score_raw = arguments.get(
            "min_relevance_score",
            arguments.get("min_score", CONVERSATION_DEFAULT_MIN_SCORE),
        )
        min_relevance_score = max(0.0, float(min_score_raw))

        # Extract and validate days_lookback
        days_raw = arguments.get("days_lookback", CONVERSATION_DEFAULT_LOOKBACK_DAYS)
        days_lookback = max(1, min(int(days_raw), CONVERSATION_MAX_LOOKBACK_DAYS))

        # Extract boolean flags
        fast_mode = bool(arguments.get("fast_mode", CONVERSATION_DEFAULT_FAST_MODE))
        include_analysis = bool(arguments.get("include_analysis", False))

        # Extract optional lists with validation
        conversation_types = ParameterValidator._validate_string_list(
            arguments.get("conversation_types")
        )
        tools = ParameterValidator._validate_string_list(arguments.get("tools"))
        tags = ParameterValidator._validate_string_list(arguments.get("tags"))

        # Extract optional strings
        user_prompt = ParameterValidator._validate_optional_string(
            arguments.get("user_prompt")
        )
        search_query = ParameterValidator._validate_optional_string(
            arguments.get("search_query", arguments.get("query"))
        )

        return ConversationParameters(
            limit=limit,
            min_relevance_score=min_relevance_score,
            days_lookback=days_lookback,
            fast_mode=fast_mode,
            conversation_types=conversation_types,
            tools=tools,
            user_prompt=user_prompt,
            search_query=search_query,
            tags=tags,
            include_analysis=include_analysis,
        )

    @staticmethod
    def _validate_string_list(value: Any) -> list[str] | None:
        """Validate and normalize a list of strings parameter."""
        if value is None:
            return None

        if not isinstance(value, list):
            return None

        # Filter to only string values
        string_values = [str(item) for item in value if item is not None]
        return string_values if string_values else None

    @staticmethod
    def _validate_optional_string(value: Any) -> str | None:
        """Validate and normalize an optional string parameter."""
        if value is None:
            return None

        str_value = str(value).strip()
        return str_value if str_value else None

    @staticmethod
    def validate_file_tools_params(arguments: dict[str, Any]) -> dict[str, Any]:
        """Validate parameters for file tools with specific constraints."""
        from src.config.conversation_config import MAX_FILES_LIMIT

        # File-specific parameter validation
        max_files = arguments.get("max_files", 1000)
        max_files = max(1, min(int(max_files), MAX_FILES_LIMIT))

        file_types = ParameterValidator._validate_string_list(
            arguments.get("file_types")
        )

        scoring_enabled = bool(
            arguments.get(
                "scoring_enabled", arguments.get("use_relevance_scoring", True)
            )
        )

        return {
            "max_files": max_files,
            "file_types": file_types,
            "scoring_enabled": scoring_enabled,
        }

    @staticmethod
    def validate_export_params(arguments: dict[str, Any]) -> dict[str, Any]:
        """Validate parameters for conversation export operations."""
        from src.config.conversation_config import (
            CONVERSATION_EXPORT_FORMAT_DEFAULT,
            CONVERSATION_EXPORT_FORMATS,
        )

        # Validate export format
        export_format = arguments.get("format", CONVERSATION_EXPORT_FORMAT_DEFAULT)
        if export_format not in CONVERSATION_EXPORT_FORMATS:
            export_format = CONVERSATION_EXPORT_FORMAT_DEFAULT

        # Validate output directory
        output_dir = ParameterValidator._validate_optional_string(
            arguments.get("output_dir")
        )

        # Validate conversation filter
        conversation_filter = ParameterValidator._validate_optional_string(
            arguments.get("conversation_filter")
        )

        # Validate workspace filter
        workspace_filter = ParameterValidator._validate_optional_string(
            arguments.get("workspace_filter")
        )

        # Validate limit for export
        limit = max(1, min(int(arguments.get("limit", 20)), 100))

        return {
            "format": export_format,
            "output_dir": output_dir,
            "conversation_filter": conversation_filter,
            "workspace_filter": workspace_filter,
            "limit": limit,
        }
