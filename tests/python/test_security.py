"""Test security validation utilities."""

import unittest.mock as mock
from pathlib import Path

from src.utils.security import (
    SecurityValidator,
    validate_conversation_id,
    validate_file_types,
    validate_search_query,
)

patch = mock.patch


class TestSecurityValidator:
    """Test SecurityValidator class methods."""

    def test_validate_string_required_missing(self):
        """Test string validation with required field missing."""
        is_valid, error = SecurityValidator.validate_string(
            None, "test_field", required=True
        )
        assert not is_valid
        assert "test_field is required" in error

    def test_validate_string_wrong_type(self):
        """Test string validation with wrong type."""
        is_valid, error = SecurityValidator.validate_string(123, "test_field")
        assert not is_valid
        assert "test_field must be a string" in error

    def test_validate_string_too_short(self):
        """Test string validation with insufficient length."""
        is_valid, error = SecurityValidator.validate_string(
            "ab", "test_field", min_length=5
        )
        assert not is_valid
        assert "must be at least 5 characters" in error

    def test_validate_string_too_long(self):
        """Test string validation with excessive length."""
        long_string = "x" * 200
        is_valid, error = SecurityValidator.validate_string(
            long_string, "test_field", max_length=100
        )
        assert not is_valid
        assert "cannot exceed 100 characters" in error

    def test_validate_string_dangerous_content(self):
        """Test string validation with dangerous patterns."""
        dangerous_input = "../etc/passwd"
        is_valid, error = SecurityValidator.validate_string(
            dangerous_input, "test_field"
        )
        assert not is_valid
        assert "potentially unsafe content" in error

    def test_validate_string_valid(self):
        """Test string validation with valid input."""
        is_valid, error = SecurityValidator.validate_string(
            "valid_string", "test_field"
        )
        assert is_valid
        assert error == ""

    def test_validate_array_required_missing(self):
        """Test array validation with required field missing."""
        is_valid, error = SecurityValidator.validate_array(
            None, "test_array", required=True
        )
        assert not is_valid
        assert "test_array is required" in error

    def test_validate_array_wrong_type(self):
        """Test array validation with wrong type."""
        is_valid, error = SecurityValidator.validate_array(
            "not_array", "test_array"
        )
        assert not is_valid
        assert "test_array must be an array" in error

    def test_validate_array_too_many_items(self):
        """Test array validation with too many items."""
        large_array = list(range(150))
        is_valid, error = SecurityValidator.validate_array(
            large_array, "test_array", max_items=100
        )
        assert not is_valid
        assert "cannot exceed 100 items" in error

    def test_validate_array_wrong_item_type(self):
        """Test array validation with wrong item type."""
        mixed_array = ["string", 123, "another_string"]
        is_valid, error = SecurityValidator.validate_array(
            mixed_array, "test_array", item_type=str
        )
        assert not is_valid
        assert "must be of type str" in error

    def test_validate_array_valid(self):
        """Test array validation with valid input."""
        valid_array = ["item1", "item2", "item3"]
        is_valid, error = SecurityValidator.validate_array(
            valid_array, "test_array", item_type=str
        )
        assert is_valid
        assert error == ""

    def test_validate_path_blocked_directory(self):
        """Test path validation with blocked directory."""
        with patch("pathlib.Path.resolve") as mock_resolve:
            mock_resolve.return_value = Path("/etc/passwd")
            is_valid, error = SecurityValidator.validate_path("/etc/passwd")
            assert not is_valid
            assert "restricted directory" in error

    def test_validate_path_too_deep(self):
        """Test path validation with excessive depth."""
        deep_path = "/".join(["level"] * 25)
        is_valid, error = SecurityValidator.validate_path(deep_path)
        assert not is_valid
        assert "exceeds maximum path depth" in error

    def test_validate_path_invalid_path(self):
        """Test path validation with invalid path."""
        with patch(
            "pathlib.Path.resolve", side_effect=OSError("Invalid path")
        ):
            is_valid, error = SecurityValidator.validate_path("/invalid/path")
            assert not is_valid
            assert "is invalid" in error

    def test_validate_path_valid(self):
        """Test path validation with valid path."""
        with patch("pathlib.Path.resolve") as mock_resolve:
            mock_resolve.return_value = Path("/valid/project/path")
            is_valid, error = SecurityValidator.validate_path(
                "/valid/project/path"
            )
            assert is_valid
            assert error == ""

    def test_validate_file_extension_unsafe(self):
        """Test file extension validation with unsafe extension."""
        is_valid, error = SecurityValidator.validate_file_extension(".exe")
        assert not is_valid
        assert "is not allowed" in error

    def test_validate_file_extension_valid(self):
        """Test file extension validation with valid extension."""
        is_valid, error = SecurityValidator.validate_file_extension(".py")
        assert is_valid
        assert error == ""

    def test_sanitize_query_dangerous_chars(self):
        """Test query sanitization with dangerous characters."""
        dangerous_query = 'search<script>alert("xss")</script>'
        result = SecurityValidator.sanitize_query(dangerous_query)
        assert "<" not in result
        assert ">" not in result
        assert "script" in result  # Should keep safe parts

    def test_sanitize_query_length_limit(self):
        """Test query sanitization with length limit."""
        long_query = "x" * 200
        result = SecurityValidator.sanitize_query(long_query)
        assert len(result) <= SecurityValidator.MAX_QUERY_LENGTH

    def test_check_for_tricks_directory_traversal(self):
        """Test dangerous pattern detection for directory traversal."""
        dangerous_text = "../etc/passwd"
        result = SecurityValidator._check_for_tricks(dangerous_text)
        assert result is True

    def test_check_for_tricks_script_injection(self):
        """Test dangerous pattern detection for script injection."""
        dangerous_text = "<script>alert('xss')</script>"
        result = SecurityValidator._check_for_tricks(dangerous_text)
        assert result is True

    def test_check_for_tricks_safe_text(self):
        """Test dangerous pattern detection with safe text."""
        safe_text = "This is a normal string without dangerous patterns"
        result = SecurityValidator._check_for_tricks(safe_text)
        assert result is False

    def test_create_error_response(self):
        """Test MCP error response creation."""
        error_msg = "Test error message"
        response = SecurityValidator.create_error_response(error_msg)

        assert response["isError"] is True
        assert response["error"] == error_msg
        assert len(response["content"]) == 1
        assert response["content"][0]["type"] == "text"
        assert error_msg in response["content"][0]["text"]

    def test_create_success_response(self):
        """Test MCP success response creation."""
        success_text = "Operation completed successfully"
        response = SecurityValidator.create_success_response(success_text)

        assert "isError" not in response
        assert len(response["content"]) == 1
        assert response["content"][0]["type"] == "text"
        assert response["content"][0]["text"] == success_text

    def test_validate_conversation_content_valid(self):
        """Test conversation content validation with valid content."""
        valid_content = "This is a normal conversation message"
        is_valid, error = SecurityValidator.validate_conversation_content(
            valid_content, "message"
        )
        assert is_valid
        assert error == ""

    def test_validate_conversation_content_dangerous(self):
        """Test conversation content validation with dangerous content."""
        dangerous_content = "<script>alert('xss')</script>"
        is_valid, error = SecurityValidator.validate_conversation_content(
            dangerous_content, "message"
        )
        assert not is_valid
        assert "potentially unsafe content" in error

    def test_check_for_conversation_tricks_script_tag(self):
        """Test conversation-specific dangerous pattern detection."""
        dangerous_content = "<script>alert('test')</script>"
        result = SecurityValidator._check_for_conversation_tricks(
            dangerous_content
        )
        assert result is True

    def test_check_for_conversation_tricks_safe_content(self):
        """Test conversation-specific pattern detection with safe content."""
        safe_content = "This is a normal conversation about coding"
        result = SecurityValidator._check_for_conversation_tricks(safe_content)
        assert result is False

    def test_sanitize_project_name_empty(self):
        """Test project name sanitization with empty input."""
        result = SecurityValidator.sanitize_project_name("")
        assert result == "unnamed_project"

    def test_sanitize_project_name_dangerous_chars(self):
        """Test project name sanitization with dangerous characters."""
        dangerous_name = "my-project<script>alert()</script>"
        result = SecurityValidator.sanitize_project_name(dangerous_name)
        assert "<" not in result
        assert ">" not in result
        assert "my-project" in result

    def test_sanitize_project_name_starts_with_dot(self):
        """Test project name sanitization starting with dot."""
        hidden_name = ".hidden-project"
        result = SecurityValidator.sanitize_project_name(hidden_name)
        assert result.startswith("project")

    def test_sanitize_project_name_too_long(self):
        """Test project name sanitization with excessive length."""
        long_name = "x" * 150
        result = SecurityValidator.sanitize_project_name(long_name)
        assert len(result) <= 100

    def test_sanitize_project_name_valid(self):
        """Test project name sanitization with valid name."""
        valid_name = "my-valid-project"
        result = SecurityValidator.sanitize_project_name(valid_name)
        assert result == valid_name


class TestConvenienceFunctions:
    """Test convenience validation functions."""

    def test_validate_conversation_id_valid(self):
        """Test conversation ID validation with valid ID."""
        valid_id = "conv_12345"
        is_valid, error = validate_conversation_id(valid_id)
        assert is_valid
        assert error == ""

    def test_validate_conversation_id_invalid(self):
        """Test conversation ID validation with invalid ID."""
        is_valid, error = validate_conversation_id(None)
        assert not is_valid
        assert "conversation_id is required" in error

    def test_validate_search_query_valid(self):
        """Test search query validation with valid query."""
        valid_query = "search term"
        is_valid, error = validate_search_query(valid_query)
        assert is_valid
        assert error == ""

    def test_validate_search_query_invalid(self):
        """Test search query validation with invalid query."""
        is_valid, error = validate_search_query("")
        assert not is_valid
        assert "search query" in error

    def test_validate_file_types_valid(self):
        """Test file types validation with valid extensions."""
        valid_types = [".py", ".js", ".md"]
        is_valid, error = validate_file_types(valid_types)
        assert is_valid
        assert error == ""

    def test_validate_file_types_invalid_extension(self):
        """Test file types validation with invalid extension."""
        invalid_types = [".py", ".exe", ".md"]
        is_valid, error = validate_file_types(invalid_types)
        assert not is_valid
        assert "not allowed" in error

    def test_validate_file_types_empty_array(self):
        """Test file types validation with empty array."""
        is_valid, error = validate_file_types([])
        assert is_valid
        assert error == ""

    def test_validate_file_types_none(self):
        """Test file types validation with None."""
        is_valid, error = validate_file_types(None)
        assert is_valid
        assert error == ""


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
        is_valid, _ = SecurityValidator.validate_string(
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
        error_response = SecurityValidator.create_error_response("Test error")
        success_response = SecurityValidator.create_success_response(
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
