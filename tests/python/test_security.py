"""Test security validation utilities."""

import unittest.mock as mock
from pathlib import Path

from src.utils.access_control import (
    AccessValidator,
    validate_conversation_id,
    validate_file_types,
    validate_search_query,
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
        valid, error = AccessValidator.validate_path("/tmp/test", "test_path")
        # Should be invalid because /tmp is blocked
        assert valid is False
        assert "restricted directory" in error

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
