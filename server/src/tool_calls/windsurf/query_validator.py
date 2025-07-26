"""
Conversation validation utilities for Windsurf IDE conversations.

This module provides validation functionality for Windsurf conversation data
and database integrity checks.
"""

import sqlite3
from pathlib import Path
from typing import Any

from src.config.core_constants import MAX_QUERY_LENGTH, MAX_STRING_LENGTH
from src.config.tool_config import (
    DATABASE_OPERATION_TIMEOUT,
    SQL_GET_TABLE_NAMES,
    WINDSURF_CONTENT_KEYS,
    WINDSURF_FALSE_POSITIVE_INDICATORS,
    WINDSURF_MESSAGE_INDICATORS,
    WINDSURF_STRONG_CONVERSATION_INDICATORS,
)
from src.utils.access_control import AccessValidator
from src.utils.common import format_json_response, log_debug, log_error


class ConversationValidator:
    """Validates Windsurf conversation data and database integrity."""

    def __init__(self) -> None:
        """Initialize the conversation validator."""
        pass

    @staticmethod
    def is_valid_conversation(conversation: Any) -> bool:
        """
        Static method to validate conversation data.
        """
        validator = ConversationValidator()
        return validator.validate_conversation_data(conversation)

    def validate_conversation_data(self, conversation: Any) -> bool:
        """
        Validate conversation data structure and content.

        Args:
            conversation: The conversation data to validate

        Returns:
            bool: True if conversation is valid, False otherwise
        """
        if not isinstance(conversation, dict | list):
            log_debug("Invalid conversation: not a dictionary or list")
            return False

        # Check for strong conversation indicators
        strong_indicators_found = 0
        false_positive_indicators_found = 0

        def check_data(data: Any, path: str = "") -> None:
            nonlocal strong_indicators_found, false_positive_indicators_found

            if isinstance(data, dict):
                for key, value in data.items():
                    key_lower = str(key).lower()
                    if key_lower in WINDSURF_STRONG_CONVERSATION_INDICATORS:
                        strong_indicators_found += 1
                    if key_lower in WINDSURF_FALSE_POSITIVE_INDICATORS:
                        false_positive_indicators_found += 1
                    # Recursively check values
                    check_data(value, f"{path}.{key}" if path else key)
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    check_data(item, f"{path}[{i}]" if path else f"[{i}]")
            elif isinstance(data, str):
                data_lower = data.lower()
                for indicator in WINDSURF_STRONG_CONVERSATION_INDICATORS:
                    if indicator in data_lower:
                        strong_indicators_found += 1
                        break  # Only count once per string

        check_data(conversation)

        # Validation logic: must have sufficient strong indicators and not too many false positives
        if strong_indicators_found < 2:
            log_debug(
                f"Invalid conversation: insufficient strong indicators ({strong_indicators_found} < 2)"
            )
            return False

        if false_positive_indicators_found > strong_indicators_found:
            log_debug("Invalid conversation: too many false positive indicators")
            return False

        log_debug(
            f"Valid conversation: {strong_indicators_found} strong indicators, {false_positive_indicators_found} false positive indicators"
        )
        return True

    @staticmethod
    def _validate_dict_structure(data: dict[str, Any]) -> bool:
        """
        Validate dictionary structure for conversation content.
        """
        content_keys_found = []
        for key in data.keys():
            if key.lower() in WINDSURF_CONTENT_KEYS:
                content_keys_found.append(key)

        if not content_keys_found:
            return False

        for key in content_keys_found:
            value = data[key]

            if isinstance(value, str):
                if len(value.strip()) < 5:  # Too short
                    continue
                return True

            elif isinstance(value, list):
                # List content is considered valid
                if len(value) > 0:
                    return True

            elif isinstance(value, dict):
                # Nested dict content
                if len(value) > 0:
                    return True

        return False

    @staticmethod
    def _validate_list_structure(data: list[Any]) -> bool:
        """
        Validate list structure for conversation content.
        """
        if not data:  # Empty list
            return False

        for item in data:
            if isinstance(item, dict):
                for key in item.keys():
                    if key.lower() in WINDSURF_MESSAGE_INDICATORS:
                        return True

        return False

    @staticmethod
    def _validate_structure(data: Any) -> bool:
        """
        Dispatcher method to validate structure based on data type.
        """
        if isinstance(data, dict):
            return ConversationValidator._validate_dict_structure(data)
        elif isinstance(data, list):
            return ConversationValidator._validate_list_structure(data)
        else:
            return False

    def _validate_message(self, message: Any, index: int) -> bool:
        """
        Validate individual message data.

        Args:
            message: The message data to validate
            index: Message index for error reporting

        Returns:
            bool: True if message is valid, False otherwise
        """
        if not isinstance(message, dict):
            log_debug(f"Invalid message at index {index}: not a dictionary")
            return False

        # Check for content
        content_fields = ["content", "text", "body"]
        has_content = any(field in message for field in content_fields)
        if not has_content:
            log_debug(f"Invalid message at index {index}: no content field found")
            return False

        # Validate content length
        for field in content_fields:
            if field in message:
                content = message[field]
                if isinstance(content, str) and len(content) > MAX_STRING_LENGTH:
                    log_debug(f"Invalid message at index {index}: '{field}' too long")
                    return False

        return True

    def validate_database_file(self, db_path: Path) -> bool:
        """
        Validate database file accessibility and basic structure.

        Args:
            db_path: Path to the database file

        Returns:
            bool: True if database is accessible, False otherwise
        """
        try:
            if not db_path.exists():
                log_debug(f"Database file does not exist: {db_path}")
                return False

            if not db_path.is_file():
                log_debug(f"Database path is not a file: {db_path}")
                return False

            # Try to open and query the database
            with sqlite3.connect(
                str(db_path), timeout=DATABASE_OPERATION_TIMEOUT
            ) as conn:
                cursor = conn.cursor()

                # Check if it's a valid SQLite database
                cursor.execute(SQL_GET_TABLE_NAMES)
                tables = cursor.fetchall()

                if not tables:
                    log_debug(f"Database has no tables: {db_path}")
                    return False

                log_debug(
                    f"Database validation successful: {db_path} ({len(tables)} tables)"
                )
                return True

        except (sqlite3.Error, OSError) as e:
            log_error(e, f"Database validation failed: {db_path}")
            return False

    def validate_query_parameters(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Validate and sanitize query parameters.

        Args:
            arguments: Raw query arguments

        Returns:
            dict: Validated and sanitized arguments
        """
        validated: dict[str, Any] = {}

        # Validate limit
        limit_raw = arguments.get("limit", 50)
        if isinstance(limit_raw, int) and 1 <= limit_raw <= 1000:
            validated["limit"] = limit_raw
        elif isinstance(limit_raw, str) and limit_raw.isdigit():
            validated["limit"] = min(max(int(limit_raw), 1), 1000)
        else:
            validated["limit"] = 50

        # Validate days_lookback
        days_lookback_raw = arguments.get("days_lookback", 30)
        if isinstance(days_lookback_raw, int) and 1 <= days_lookback_raw <= 365:
            validated["days_lookback"] = days_lookback_raw
        elif isinstance(days_lookback_raw, str) and days_lookback_raw.isdigit():
            validated["days_lookback"] = min(max(int(days_lookback_raw), 1), 365)
        else:
            validated["days_lookback"] = 30

        # Validate search_query
        search_query = arguments.get("search_query", "")
        if isinstance(search_query, str) and len(search_query) <= MAX_QUERY_LENGTH:
            validated["search_query"] = search_query.strip()
        else:
            validated["search_query"] = ""

        # Validate boolean flags
        for flag in ["include_messages", "fast_mode"]:
            value = arguments.get(flag, False)
            validated[flag] = bool(value)

        # Validate format
        format_type = arguments.get("format", "json")
        if format_type in ["json", "text", "summary"]:
            validated["format"] = format_type
        else:
            validated["format"] = "json"

        log_debug(f"Validated query parameters: {validated}")
        return validated

    def create_validation_error_response(self, error_message: str) -> dict[str, Any]:
        """
        Create standardized validation error response.

        Args:
            error_message: Description of the validation error

        Returns:
            dict: Formatted error response
        """
        error_data = {
            "error": f"Validation error: {error_message}",
            "success": False,
            "conversations": [],
            "metadata": {
                "total_found": 0,
                "validation_failed": True,
            },
        }

        return AccessValidator.create_error_response(format_json_response(error_data))
