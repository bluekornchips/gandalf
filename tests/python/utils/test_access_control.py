"""Test security validation utilities."""

import unittest.mock as mock
from pathlib import Path

from src.utils.access_control import (
    AccessValidator,
    validate_conversation_id,
    validate_file_types,
    validate_search_query,
    get_platform_blocked_paths,
)

patch = mock.patch


class TestAccessValidator:
    """Test cases for AccessValidator class."""

    def test_validate_string_valid(self):
        """Test valid string validation."""
        valid, error = AccessValidator.validate_string(
            "valid_string", "test_field"
        )
        assert valid is True
        assert error == ""

    def test_validate_string_empty_required(self):
        """Test empty string validation when required."""
        valid, error = AccessValidator.validate_string("", "test_field")
        assert valid is False
        assert "required" in error

    def test_validate_string_too_long(self):
        """Test string too long validation."""
        long_string = "a" * 60000
        valid, error = AccessValidator.validate_string(
            long_string, "test_field"
        )
        assert valid is False
        assert "cannot exceed" in error

    def test_validate_array_valid(self):
        """Test valid array validation."""
        valid, error = AccessValidator.validate_array(
            ["item1", "item2"], "test_field", item_type=str
        )
        assert valid is True
        assert error == ""

    def test_validate_array_too_many_items(self):
        """Test array with too many items."""
        large_array = ["item"] * 150
        valid, error = AccessValidator.validate_array(
            large_array, "test_field"
        )
        assert valid is False
        assert "cannot exceed" in error

    def test_validate_path_valid(self):
        """Test valid path validation."""
        valid, error = AccessValidator.validate_path(
            "/private/etc/passwd", "test_path"
        )
        # Should be invalid because /etc is blocked (resolves to /private/etc on macOS)
        assert valid is False
        assert "blocked system path" in error

    def test_validate_file_extension_valid(self):
        """Test valid file extension."""
        valid, error = AccessValidator.validate_file_extension(".py")
        assert valid is True
        assert error == ""

    def test_validate_file_extension_invalid(self):
        """Test invalid file extension."""
        valid, error = AccessValidator.validate_file_extension(".exe")
        assert valid is False
        assert "not allowed" in error

    def test_validate_integer_valid(self):
        """Test valid integer validation."""
        valid, error = AccessValidator.validate_integer(
            50, "test_field", min_value=1, max_value=100
        )
        assert valid is True
        assert error == ""

    def test_validate_integer_out_of_range(self):
        """Test integer out of range validation."""
        valid, error = AccessValidator.validate_integer(
            150, "test_field", min_value=1, max_value=100
        )
        assert valid is False
        assert "cannot exceed 100" in error

    def test_validate_integer_below_minimum(self):
        """Test integer below minimum validation."""
        valid, error = AccessValidator.validate_integer(
            -5, "test_field", min_value=1, max_value=100
        )
        assert valid is False
        assert "must be at least 1" in error

    def test_validate_integer_not_integer(self):
        """Test non-integer input validation."""
        valid, error = AccessValidator.validate_integer(
            "not_int", "test_field"
        )
        assert valid is False
        assert "must be an integer" in error

    def test_validate_enum_valid(self):
        """Test valid enum validation."""
        valid, error = AccessValidator.validate_enum(
            "json", "format", ["json", "md", "txt"]
        )
        assert valid is True
        assert error == ""

    def test_validate_enum_invalid_value(self):
        """Test invalid enum value validation."""
        valid, error = AccessValidator.validate_enum(
            "invalid", "format", ["json", "md", "txt"]
        )
        assert valid is False
        assert "must be one of: json, md, txt" in error

    def test_validate_enum_not_string(self):
        """Test non-string enum input validation."""
        valid, error = AccessValidator.validate_enum(
            123, "format", ["json", "md", "txt"]
        )
        assert valid is False
        assert "must be a string" in error


class TestPlatformSpecificPaths:
    """Test platform-specific blocked paths functionality."""

    def test_platform_specific_blocked_paths(self):
        """
        Test that platform-specific paths are properly organized.
        Pretty useless test but I want it so I don't have to think about it.
        """
        from src.config.constants.file_security import (
            COMMON_BLOCKED_PATHS,
            LINUX_SPECIFIC_BLOCKED_PATHS,
            MACOS_SPECIFIC_BLOCKED_PATHS,
            WSL_SPECIFIC_BLOCKED_PATHS,
        )

        # Check that common paths are shared, not really a good test
        assert "/etc" in COMMON_BLOCKED_PATHS
        assert "/sys" in COMMON_BLOCKED_PATHS
        assert "/proc" in COMMON_BLOCKED_PATHS

        # platform-specific paths
        assert "/private/etc" in MACOS_SPECIFIC_BLOCKED_PATHS
        assert "/mnt/c/Windows" in WSL_SPECIFIC_BLOCKED_PATHS
        assert "/snap" in LINUX_SPECIFIC_BLOCKED_PATHS

        # no duplicates between common and specific
        assert len(COMMON_BLOCKED_PATHS & MACOS_SPECIFIC_BLOCKED_PATHS) == 0
        assert len(COMMON_BLOCKED_PATHS & WSL_SPECIFIC_BLOCKED_PATHS) == 0
        assert len(COMMON_BLOCKED_PATHS & LINUX_SPECIFIC_BLOCKED_PATHS) == 0

    def test_get_platform_blocked_paths_function(self):
        """Test the get_platform_blocked_paths utility function."""
        from src.config.constants.file_security import (
            COMMON_BLOCKED_PATHS,
            LINUX_SPECIFIC_BLOCKED_PATHS,
            MACOS_SPECIFIC_BLOCKED_PATHS,
            WSL_SPECIFIC_BLOCKED_PATHS,
        )

        # linux
        linux_paths = get_platform_blocked_paths("linux")
        expected_linux = COMMON_BLOCKED_PATHS | LINUX_SPECIFIC_BLOCKED_PATHS
        assert linux_paths == expected_linux

        # macOS specific
        macos_paths = get_platform_blocked_paths("macos")
        expected_macos = COMMON_BLOCKED_PATHS | MACOS_SPECIFIC_BLOCKED_PATHS
        assert macos_paths == expected_macos

        # WSL specific
        wsl_paths = get_platform_blocked_paths("wsl")
        expected_wsl = COMMON_BLOCKED_PATHS | WSL_SPECIFIC_BLOCKED_PATHS
        assert wsl_paths == expected_wsl

        # All paths
        all_paths = get_platform_blocked_paths()
        all_paths_none = get_platform_blocked_paths(None)
        assert all_paths == all_paths_none

        # Invalid platform, returns all paths
        invalid_paths = get_platform_blocked_paths("invalid")
        assert invalid_paths == all_paths


class TestValidationFunctions:
    """Test cases for validation helper functions."""

    def test_validate_conversation_id_valid(self):
        """Test valid conversation ID."""
        valid, error = validate_conversation_id("valid_id_123")
        assert valid is True
        assert error == ""

    def test_validate_conversation_id_empty(self):
        """Test empty conversation ID."""
        valid, error = validate_conversation_id("")
        assert valid is False
        assert "required" in error

    def test_validate_search_query_valid(self):
        """Test valid search query."""
        valid, error = validate_search_query("search terms")
        assert valid is True
        assert error == ""

    def test_validate_file_types_valid(self):
        """Test valid file types."""
        valid, error = validate_file_types([".py", ".js"])
        assert valid is True
        assert error == ""

    def test_validate_file_types_invalid_extension(self):
        """Test invalid file extension in types."""
        valid, error = validate_file_types([".py", ".exe"])
        assert valid is False
        assert "not allowed" in error


class TestSecurityIntegration:
    """Test security validation integration scenarios."""

    def test_full_validation_pipeline(self):
        """Test complete validation pipeline with various inputs."""
        # Test valid inputs pass through all validations
        valid_data = {
            "string_field": "valid content",
            "array_field": [".py", ".js"],
            "path_field": "/valid/project/path",
            "query_field": "search terms",
        }

        # String validation
        is_valid, _ = AccessValidator.validate_string(
            valid_data["string_field"], "string_field"
        )
        assert is_valid

        # File types validation
        is_valid, _ = validate_file_types(valid_data["array_field"])
        assert is_valid

        # Query validation
        is_valid, _ = validate_search_query(valid_data["query_field"])
        assert is_valid

    def test_security_response_format_consistency(self):
        """Test that all security responses follow consistent format."""
        error_response = AccessValidator.create_error_response("Test error")
        success_response = AccessValidator.create_success_response(
            "Test success"
        )

        # Error response format
        assert isinstance(error_response, dict)
        assert "isError" in error_response
        assert "error" in error_response
        assert "content" in error_response

        # Success response format
        assert isinstance(success_response, dict)
        assert "content" in success_response
        assert isinstance(success_response["content"], list)
        assert len(success_response["content"]) > 0
