"""
Access control utilities for Gandalf MCP server.
Provides path validation, project name sanitization, and security checks.
"""

import json
import re
from pathlib import Path
from typing import Any

from src.config.config_data import BLOCKED_EXTENSIONS
from src.config.constants.limits import (
    MAX_ARRAY_LENGTH,
    MAX_FILE_TYPES,
    MAX_PATH_DEPTH,
    MAX_QUERY_LENGTH,
    MAX_STRING_LENGTH,
    PROJECT_NAME_MAX_LENGTH,
)
from src.config.constants.security import (
    COMMON_BLOCKED_PATHS,
    CONVERSATION_DANGEROUS_PATTERNS,
    DANGEROUS_PATTERNS,
    FILE_EXTENSION_MAX_LENGTH,
    FILENAME_INVALID_CHARS_PATTERN,
    LINUX_SPECIFIC_BLOCKED_PATHS,
    MACOS_SPECIFIC_BLOCKED_PATHS,
    PROJECT_NAME_SANITIZE_PATTERN,
    QUERY_SANITIZE_PATTERN,
    WSL_SPECIFIC_BLOCKED_PATHS,
)
from src.utils.common import log_debug, log_info


class AccessValidator:
    """Centralized access control and validation for MCP tools."""

    @classmethod
    def validate_string(
        cls,
        value: Any,
        field_name: str,
        min_length: int = 1,
        max_length: int | None = None,
        required: bool = True,
    ) -> tuple[bool, str]:
        """Validate string input with length and content constraints."""
        if required and not value:
            return False, f"{field_name} is required"

        if value is None and not required:
            return True, ""

        if not isinstance(value, str):
            return False, f"{field_name} must be a string"

        if len(value.strip()) < min_length:
            return (
                False,
                f"{field_name} must be at least {min_length} characters",
            )

        max_len = max_length or MAX_STRING_LENGTH
        if len(value) > max_len:
            return False, f"{field_name} cannot exceed {max_len} characters"

        if cls._check_for_tricks(value):
            return False, f"{field_name} contains potentially unsafe content"

        return True, ""

    @classmethod
    def validate_array(
        cls,
        value: Any,
        field_name: str,
        max_items: int | None = None,
        item_type: type | None = None,
        required: bool = True,
    ) -> tuple[bool, str]:
        """Validate array input with type and size constraints."""
        if required and not value:
            return False, f"{field_name} is required"

        if value is None and not required:
            return True, ""

        if not isinstance(value, list):
            return False, f"{field_name} must be an array"

        max_len = max_items or MAX_ARRAY_LENGTH
        if len(value) > max_len:
            return False, f"{field_name} cannot exceed {max_len} items"

        if item_type:
            for i, item in enumerate(value):
                if not isinstance(item, item_type):
                    return (
                        False,
                        f"{field_name}[{i}] must be of type {item_type.__name__}",
                    )

        return True, ""

    @classmethod
    def validate_integer(
        cls,
        value: Any,
        field_name: str,
        min_value: int | None = None,
        max_value: int | None = None,
        required: bool = True,
    ) -> tuple[bool, str]:
        """Validate integer input with range constraints."""
        if required and value is None:
            return False, f"{field_name} is required"

        if value is None and not required:
            return True, ""

        if not isinstance(value, int):
            return False, f"{field_name} must be an integer"

        if min_value is not None and value < min_value:
            return False, f"{field_name} must be at least {min_value}"

        if max_value is not None and value > max_value:
            return False, f"{field_name} cannot exceed {max_value}"

        return True, ""

    @classmethod
    def validate_enum(
        cls,
        value: Any,
        field_name: str,
        valid_values: list[str],
        required: bool = True,
    ) -> tuple[bool, str]:
        """Validate enum input against allowed values."""
        if required and not value:
            return False, f"{field_name} is required"

        if value is None and not required:
            return True, ""

        if not isinstance(value, str):
            return False, f"{field_name} must be a string"

        if value not in valid_values:
            return (
                False,
                f"{field_name} must be one of: {', '.join(valid_values)}",
            )

        return True, ""

    @classmethod
    def validate_path(
        cls, path: str | Path, field_name: str = "path"
    ) -> tuple[bool, str]:
        """Validate file path for security."""
        path_str = str(path)

        if cls._check_for_tricks(path_str):
            return False, f"{field_name} contains potentially unsafe content"

        try:
            resolved_path = Path(path_str).resolve()
            path_parts = resolved_path.parts

            if len(path_parts) > MAX_PATH_DEPTH:
                return False, f"{field_name} exceeds maximum depth"

            for blocked_path in COMMON_BLOCKED_PATHS:
                try:
                    # Resolve blocked path to handle symlinks, sort of?
                    resolved_blocked_path = Path(blocked_path).resolve()
                    if str(resolved_path).startswith(str(resolved_blocked_path)):
                        return False, f"{field_name} accesses blocked system path"
                except (OSError, ValueError):
                    if str(resolved_path).startswith(blocked_path):
                        return False, f"{field_name} accesses blocked system path"

        except (OSError, ValueError):
            return False, f"{field_name} is not a valid path"

        return True, ""

    @classmethod
    def validate_file_extension(cls, extension: str) -> tuple[bool, str]:
        """Validate file extension for security using blocklist approach."""
        if not extension.startswith("."):
            extension = f".{extension}"

        extension = extension.lower()

        # Check if extension is in the blocked list
        if extension in BLOCKED_EXTENSIONS:
            return False, f"File extension {extension} is not allowed"

        if len(extension) > FILE_EXTENSION_MAX_LENGTH:
            return False, "File extension too long"

        if re.search(FILENAME_INVALID_CHARS_PATTERN, extension):
            return False, "File extension contains invalid characters"

        return True, ""

    @classmethod
    def sanitize_query(cls, query: str) -> str:
        """Sanitize search query input."""
        if not query:
            return ""

        sanitized = re.sub(QUERY_SANITIZE_PATTERN, "", query)
        return sanitized[:MAX_QUERY_LENGTH].strip()

    @classmethod
    def _check_for_tricks(cls, text: str) -> bool:
        """Check for potentially dangerous patterns in user input.

        Tricksy hobbits!
        """
        text_lower = text.lower()

        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, text_lower):
                log_debug(
                    f"Security validation blocked dangerous pattern "
                    f"'{pattern}' in input"
                )
                return True

        log_debug(f"Security validation passed for input ({len(text)} chars)")
        return False

    @classmethod
    def create_error_response(cls, message: str) -> dict[str, Any]:
        """Create a standardized MCP error response."""
        return {
            "isError": True,
            "error": message,
            "content": [{"type": "text", "text": f"Error: {message}"}],
        }

    @classmethod
    def create_success_response(cls, content: str) -> dict[str, Any]:
        """Create a standardized MCP success response."""
        return create_mcp_tool_result(content)

    @classmethod
    def validate_conversation_content(
        cls,
        value: Any,
        field_name: str,
        min_length: int = 1,
        max_length: int | None = None,
        required: bool = True,
    ) -> tuple[bool, str]:
        """Validate conversation content with enhanced security checks."""
        is_valid, error_msg = cls.validate_string(
            value, field_name, min_length, max_length, required
        )

        if not is_valid:
            return False, error_msg

        if value and cls._check_for_conversation_tricks(value):
            return False, f"{field_name} contains potentially unsafe content"

        return True, ""

    @classmethod
    def _check_for_conversation_tricks(cls, text: str) -> bool:
        """Check for conversation-specific dangerous patterns.

        Validates conversation content for potentially malicious patterns,
        while being less restrictive than general input validation.
        """
        for pattern in CONVERSATION_DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                return True

        return False

    @classmethod
    def sanitize_project_name(cls, project_name: str) -> str:
        """Sanitize project name for filesystem safety with transparency."""
        if not project_name:
            log_debug("Empty project name provided, using default")
            return "unnamed_project"

        original_name = project_name

        sanitized = re.sub(PROJECT_NAME_SANITIZE_PATTERN, "_", project_name)

        # Ensure it doesn't start with a dot to avoid hidden files
        if sanitized.startswith("."):
            sanitized = "project" + sanitized

        # Ensure it's not empty after sanitization
        if not sanitized or sanitized.isspace():
            sanitized = "sanitized_project"

        # Limit length
        if len(sanitized) > PROJECT_NAME_MAX_LENGTH:
            sanitized = sanitized[:PROJECT_NAME_MAX_LENGTH]

        # Remove trailing dots or dashes for safety
        sanitized = sanitized.rstrip(".-")

        if sanitized != original_name:
            log_info(f"Project name sanitized: '{original_name}' -> '{sanitized}'")
        else:
            log_debug(f"Project name validation passed: '{original_name}'")

        return sanitized

    @staticmethod
    def create_json_response(data: dict[str, Any]) -> dict[str, Any]:
        """Create a standardized JSON success response."""
        return AccessValidator.create_success_response(json.dumps(data, indent=2))


def validate_conversation_id(conv_id: Any) -> tuple[bool, str]:
    """Validate conversation ID with specific rules."""
    return AccessValidator.validate_string(
        conv_id, "conversation_id", min_length=1, max_length=100
    )


def validate_search_query(query: Any) -> tuple[bool, str]:
    """Validate search query with specific rules."""
    return AccessValidator.validate_string(
        query,
        "query",
        min_length=1,
        max_length=MAX_QUERY_LENGTH,
    )


def validate_file_types(file_types: Any) -> tuple[bool, str]:
    """Validate file types array with extension validation."""
    is_valid, error = AccessValidator.validate_array(
        file_types,
        "file_types",
        max_items=MAX_FILE_TYPES,
        item_type=str,
        required=False,
    )
    if not is_valid:
        return False, error

    if file_types:
        for ext in file_types:
            ext_valid, ext_error = AccessValidator.validate_file_extension(ext)
            if not ext_valid:
                return False, ext_error

    return True, ""


def get_platform_blocked_paths(platform: str | None = None) -> set[str]:
    """Get platform-specific blocked paths."""
    if platform == "linux":
        return COMMON_BLOCKED_PATHS | LINUX_SPECIFIC_BLOCKED_PATHS
    elif platform == "macos":
        return COMMON_BLOCKED_PATHS | MACOS_SPECIFIC_BLOCKED_PATHS
    elif platform == "wsl":
        return COMMON_BLOCKED_PATHS | WSL_SPECIFIC_BLOCKED_PATHS
    else:
        return COMMON_BLOCKED_PATHS


def create_mcp_tool_result(
    content_text: str,
    structured_content: dict[str, Any] | None = None,
    is_error: bool = False,
) -> dict[str, Any]:
    """
    Create MCP-compliant tool result with optional structured content.

    According to MCP 2025-06-18 specification:
    - Tools can return both text content and structured content
    - Structured content should be validated against output schema
    - Error handling should distinguish protocol vs tool execution errors
    """
    result = {
        "content": [
            {
                "type": "text",
                "text": content_text,
                "annotations": {"audience": ["assistant"], "priority": 0.8},
            }
        ],
        "isError": is_error,
    }

    # Add structured content if provided
    if structured_content and not is_error:
        result["structuredContent"] = structured_content

    return result


def create_tool_execution_error(
    error_message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Create tool execution error (not protocol error) according to MCP 2025-06-18."""
    content_text = error_message
    if details:
        content_text += f"\nDetails: {json.dumps(details, indent=2)}"

    return create_mcp_tool_result(content_text, is_error=True)
