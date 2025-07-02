"""
Access control and security validation for the Gandalf MCP server.
"""

import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from config.constants import (
    BLOCKED_EXTENSIONS,
    BLOCKED_PATHS,
    COMMON_BLOCKED_PATHS,
    LINUX_SPECIFIC_BLOCKED_PATHS,
    MACOS_SPECIFIC_BLOCKED_PATHS,
    MAX_ARRAY_LENGTH,
    MAX_FILE_TYPES,
    MAX_PATH_DEPTH,
    MAX_QUERY_LENGTH,
    MAX_STRING_LENGTH,
    WSL_SPECIFIC_BLOCKED_PATHS,
)
from utils.common import log_debug, log_info

# File extension validation constants
FILE_EXTENSION_MAX_LENGTH = 10
FILE_EXTENSION_PATTERN = r"^\.[a-z0-9]+$"

# Query sanitization patterns
QUERY_SANITIZE_PATTERN = r'[<>"\';\\]'

# Project name validation constants
PROJECT_NAME_SANITIZE_PATTERN = r"[^a-zA-Z0-9._-]"
PROJECT_NAME_MAX_LENGTH = 100

# Security threat detection patterns
DANGEROUS_PATTERNS = [
    r"\.\./",  # Directory traversal
    r"<script",  # Script injection
    r"javascript:",  # JavaScript injection
    r"data:",  # Data URLs
    r"file://",  # File URLs
    r"\x00",  # Null bytes
    r"[;&|`$()]",  # Shell metacharacters
]

# Conversation-specific threat patterns
CONVERSATION_DANGEROUS_PATTERNS = [
    r"<script[^>]*>.*</script>",  # Complete script tags
    r"javascript:[^\"'\s]+",  # JavaScript URLs
    r"data:text/html",  # HTML data URLs
    r"vbscript:",  # VBScript URLs
    r"\${.*}",  # Template injection patterns
]


class AccessValidator:
    """Centralized access control and validation for MCP tools."""

    @classmethod
    def validate_string(
        cls,
        value: Any,
        field_name: str,
        min_length: int = 1,
        max_length: Optional[int] = None,
        required: bool = True,
    ) -> Tuple[bool, str]:
        """Validate string input with length and content constraints.

        Args:
            value: Input value to validate
            field_name: Name of the field for error messages
            min_length: Minimum required length
            max_length: Maximum allowed length (defaults to MAX_STRING_LENGTH)
            required: Whether the field is required

        Returns:
            Tuple of (is_valid, error_message)
        """
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
        max_items: Optional[int] = None,
        item_type: Optional[type] = None,
        required: bool = True,
    ) -> Tuple[bool, str]:
        """Validate array input with type and size constraints.

        Args:
            value: Input value to validate
            field_name: Name of the field for error messages
            max_items: Maximum allowed items (defaults to MAX_ARRAY_LENGTH)
            item_type: Required type for array items
            required: Whether the field is required

        Returns:
            Tuple of (is_valid, error_message)
        """
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
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        required: bool = True,
    ) -> Tuple[bool, str]:
        """Validate integer input with range constraints.

        Args:
            value: Input value to validate
            field_name: Name of the field for error messages
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            required: Whether the field is required

        Returns:
            Tuple of (is_valid, error_message)
        """
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
        valid_values: List[str],
        required: bool = True,
    ) -> Tuple[bool, str]:
        """Validate enum input against allowed values.

        Args:
            value: Input value to validate
            field_name: Name of the field for error messages
            valid_values: List of allowed values
            required: Whether the field is required

        Returns:
            Tuple of (is_valid, error_message)
        """
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
        cls, path: Union[str, Path], field_name: str = "path"
    ) -> Tuple[bool, str]:
        """Validate file path for security.

        Args:
            path: Path to validate
            field_name: Name of the field for error messages

        Returns:
            Tuple of (is_valid, error_message)
        """
        path_str = str(path)

        if cls._check_for_tricks(path_str):
            return False, f"{field_name} contains potentially unsafe content"

        try:
            resolved_path = Path(path_str).resolve()
            path_parts = resolved_path.parts

            if len(path_parts) > MAX_PATH_DEPTH:
                return False, f"{field_name} exceeds maximum depth"

            for blocked_path in BLOCKED_PATHS:
                if str(resolved_path).startswith(blocked_path):
                    return False, f"{field_name} accesses blocked system path"

        except (OSError, ValueError):
            return False, f"{field_name} is not a valid path"

        return True, ""

    @classmethod
    def validate_file_extension(cls, extension: str) -> Tuple[bool, str]:
        """Validate file extension for security using blocklist approach.

        Args:
            extension: File extension to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not extension.startswith("."):
            extension = f".{extension}"

        extension = extension.lower()

        # Check if extension is in the blocked list
        if extension in BLOCKED_EXTENSIONS:
            return False, f"File extension {extension} is not allowed"

        if len(extension) > FILE_EXTENSION_MAX_LENGTH:
            return False, "File extension too long"

        if not re.match(FILE_EXTENSION_PATTERN, extension):
            return False, "File extension contains invalid characters"

        return True, ""

    @classmethod
    def sanitize_query(cls, query: str) -> str:
        """Sanitize search query input.

        Args:
            query: Query string to sanitize

        Returns:
            Sanitized query string
        """
        if not query:
            return ""

        sanitized = re.sub(QUERY_SANITIZE_PATTERN, "", query)
        return sanitized[: cls.MAX_QUERY_LENGTH].strip()

    @classmethod
    def _check_for_tricks(cls, text: str) -> bool:
        """Check for potentially dangerous patterns in user input.

        Tricksy hobbits!

        Detects common attack vectors including directory traversal,
        script injection, and shell metacharacters.

        Args:
            text: Input text to validate

        Returns:
            bool: True if dangerous patterns are found, False otherwise
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
    def create_error_response(cls, message: str) -> Dict[str, Any]:
        """Create a standardized MCP error response.

        Args:
            message: Error message

        Returns:
            MCP error response dictionary
        """
        return {
            "isError": True,
            "error": message,
            "content": [{"type": "text", "text": f"Error: {message}"}],
        }

    @classmethod
    def create_success_response(cls, text: str) -> Dict[str, Any]:
        """Create a standardized MCP success response.

        Args:
            text: Response text

        Returns:
            MCP success response dictionary
        """
        return {"content": [{"type": "text", "text": text}]}

    @classmethod
    def validate_conversation_content(
        cls,
        value: Any,
        field_name: str,
        min_length: int = 1,
        max_length: Optional[int] = None,
        required: bool = True,
    ) -> Tuple[bool, str]:
        """Validate conversation content with enhanced security checks.

        Args:
            value: Content to validate
            field_name: Name of the field for error messages
            min_length: Minimum required length
            max_length: Maximum allowed length
            required: Whether the field is required

        Returns:
            Tuple of (is_valid, error_message)
        """
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

        Args:
            text: Conversation text to validate

        Returns:
            bool: True if dangerous patterns are found, False otherwise
        """
        for pattern in CONVERSATION_DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                return True

        return False

    @classmethod
    def sanitize_project_name(cls, project_name: str) -> str:
        """Sanitize project name for filesystem safety with transparency.

        Args:
            project_name: Raw project name to sanitize

        Returns:
            str: Sanitized project name safe for filesystem use
        """
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
    def create_json_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a standardized JSON success response."""
        return AccessValidator.create_success_response(json.dumps(data, indent=2))


def validate_conversation_id(conv_id: Any) -> Tuple[bool, str]:
    """Validate conversation ID with specific rules.

    Args:
        conv_id: Conversation ID to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    return AccessValidator.validate_string(
        conv_id, "conversation_id", min_length=1, max_length=100
    )


def validate_search_query(query: Any) -> Tuple[bool, str]:
    """Validate search query with specific rules.

    Args:
        query: Search query to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    return AccessValidator.validate_string(
        query,
        "query",
        min_length=1,
        max_length=MAX_QUERY_LENGTH,
    )


def validate_file_types(file_types: Any) -> Tuple[bool, str]:
    """Validate file types array with extension validation.

    Args:
        file_types: Array of file extensions to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
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


def get_platform_blocked_paths(platform: str = None) -> set:
    """Get platform-specific blocked paths.

    Args:
        platform: Platform identifier (linux, macos, wsl)

    Returns:
        Set of blocked paths for the platform
    """
    if platform == "linux":
        return COMMON_BLOCKED_PATHS | LINUX_SPECIFIC_BLOCKED_PATHS
    elif platform == "macos":
        return COMMON_BLOCKED_PATHS | MACOS_SPECIFIC_BLOCKED_PATHS
    elif platform == "wsl":
        return COMMON_BLOCKED_PATHS | WSL_SPECIFIC_BLOCKED_PATHS
    else:
        return BLOCKED_PATHS
