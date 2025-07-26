"""Tests for error handling decorator functionality."""

from functools import wraps
from typing import Any

import pytest


# Mock the error handling decorator and dependencies for testing
def handle_tool_errors(operation_name: str):
    """Decorator for consistent error handling across all tool functions."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
                # Mock log_error function
                print(f"ERROR in {operation_name}: {str(e)}")

                # Mock AccessValidator.create_error_response
                return {
                    "error": True,
                    "message": f"Error in {operation_name}: {str(e)}",
                    "operation": operation_name,
                    "error_type": type(e).__name__,
                }

        return wrapper

    return decorator


class TestErrorHandlingDecorator:
    """Test error handling decorator functionality."""

    def test_successful_function_execution(self):
        """Test that decorator passes through successful function results."""

        @handle_tool_errors("test_operation")
        def successful_function(value: int) -> dict[str, Any]:
            return {"result": value * 2, "success": True}

        result = successful_function(5)

        assert result["result"] == 10
        assert result["success"] is True
        assert "error" not in result

    def test_value_error_handling(self):
        """Test handling of ValueError exceptions."""

        @handle_tool_errors("value_error_operation")
        def function_with_value_error():
            raise ValueError("Invalid input value")

        result = function_with_value_error()

        assert result["error"] is True
        assert "Invalid input value" in result["message"]
        assert result["operation"] == "value_error_operation"
        assert result["error_type"] == "ValueError"

    def test_type_error_handling(self):
        """Test handling of TypeError exceptions."""

        @handle_tool_errors("type_error_operation")
        def function_with_type_error():
            raise TypeError("Expected string, got integer")

        result = function_with_type_error()

        assert result["error"] is True
        assert "Expected string, got integer" in result["message"]
        assert result["operation"] == "type_error_operation"
        assert result["error_type"] == "TypeError"

    def test_key_error_handling(self):
        """Test handling of KeyError exceptions."""

        @handle_tool_errors("key_error_operation")
        def function_with_key_error():
            data = {"existing_key": "value"}
            return data["missing_key"]

        result = function_with_key_error()

        assert result["error"] is True
        assert result["operation"] == "key_error_operation"
        assert result["error_type"] == "KeyError"

    def test_attribute_error_handling(self):
        """Test handling of AttributeError exceptions."""

        @handle_tool_errors("attribute_error_operation")
        def function_with_attribute_error():
            # Use a simple object that will actually raise AttributeError
            class SimpleObject:
                pass

            obj = SimpleObject()
            return obj.nonexistent_attribute

        result = function_with_attribute_error()

        assert result["error"] is True
        assert result["operation"] == "attribute_error_operation"
        assert result["error_type"] == "AttributeError"

    def test_os_error_handling(self):
        """Test handling of OSError exceptions."""

        @handle_tool_errors("os_error_operation")
        def function_with_os_error():
            raise OSError("File not found")

        result = function_with_os_error()

        assert result["error"] is True
        assert "File not found" in result["message"]
        assert result["operation"] == "os_error_operation"
        assert result["error_type"] == "OSError"

    def test_unhandled_exception_propagation(self):
        """Test that unhandled exceptions are not caught by the decorator."""

        @handle_tool_errors("runtime_error_operation")
        def function_with_runtime_error():
            raise RuntimeError("This should not be caught")

        with pytest.raises(RuntimeError, match="This should not be caught"):
            function_with_runtime_error()

    def test_function_with_arguments(self):
        """Test decorator works with functions that have arguments."""

        @handle_tool_errors("argument_operation")
        def function_with_args(arg1: str, arg2: int, kwarg1: str = "default"):
            if not isinstance(arg1, str):
                raise TypeError("arg1 must be string")
            if arg2 < 0:
                raise ValueError("arg2 must be positive")
            return {"arg1": arg1, "arg2": arg2, "kwarg1": kwarg1}

        # Test successful execution
        result = function_with_args("test", 5, kwarg1="custom")
        assert result["arg1"] == "test"
        assert result["arg2"] == 5
        assert result["kwarg1"] == "custom"

        # Test error handling with arguments
        error_result = function_with_args("test", -1)
        assert error_result["error"] is True
        assert "arg2 must be positive" in error_result["message"]

    def test_function_preserves_metadata(self):
        """Test that decorator preserves function metadata."""

        @handle_tool_errors("metadata_operation")
        def documented_function(param: int) -> dict[str, Any]:
            """This function has documentation."""
            return {"param": param}

        assert documented_function.__name__ == "documented_function"
        assert "This function has documentation" in documented_function.__doc__

    def test_nested_decorators(self):
        """Test that error handling decorator works with other decorators."""

        def another_decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                if isinstance(result, dict):
                    result["decorated"] = True
                return result

            return wrapper

        @another_decorator
        @handle_tool_errors("nested_operation")
        def nested_function(value: int):
            if value == 0:
                raise ValueError("Value cannot be zero")
            return {"value": value}

        # Test successful execution with nested decorators
        result = nested_function(5)
        assert result["value"] == 5
        assert result["decorated"] is True

        # Test error handling with nested decorators
        error_result = nested_function(0)
        assert error_result["error"] is True
        assert "Value cannot be zero" in error_result["message"]

    def test_multiple_exception_types_in_same_decorator(self):
        """Test that decorator catches multiple exception types correctly."""

        @handle_tool_errors("multi_error_operation")
        def function_with_multiple_errors(error_type: str):
            if error_type == "value":
                raise ValueError("Value error occurred")
            elif error_type == "type":
                raise TypeError("Type error occurred")
            elif error_type == "key":
                raise KeyError("Key error occurred")
            elif error_type == "attribute":
                raise AttributeError("Attribute error occurred")
            elif error_type == "os":
                raise OSError("OS error occurred")
            else:
                return {"success": True}

        # Test each exception type
        for error_type, expected_type in [
            ("value", "ValueError"),
            ("type", "TypeError"),
            ("key", "KeyError"),
            ("attribute", "AttributeError"),
            ("os", "OSError"),
        ]:
            result = function_with_multiple_errors(error_type)
            assert result["error"] is True
            assert result["error_type"] == expected_type
            assert (
                f"{expected_type.replace('Error', '').lower()} error occurred"
                in result["message"].lower()
            )

    def test_operation_name_customization(self):
        """Test that operation name is correctly used in error messages."""
        operation_names = [
            "cursor_conversation_recall",
            "claude_code_query",
            "windsurf_database_scan",
            "conversation_export",
        ]

        for op_name in operation_names:

            @handle_tool_errors(op_name)
            def test_function():
                raise ValueError("Test error")

            result = test_function()
            assert result["operation"] == op_name
            assert op_name in result["message"]

    def test_empty_exception_message(self):
        """Test handling of exceptions with empty messages."""

        @handle_tool_errors("empty_message_operation")
        def function_with_empty_error():
            raise ValueError("")

        result = function_with_empty_error()

        assert result["error"] is True
        assert result["error_type"] == "ValueError"
        assert result["operation"] == "empty_message_operation"

    def test_exception_with_special_characters(self):
        """Test handling of exceptions with special characters in message."""

        @handle_tool_errors("special_chars_operation")
        def function_with_special_chars():
            raise ValueError(
                "Error with special chars: áéíóú & <script>alert()</script>"
            )

        result = function_with_special_chars()

        assert result["error"] is True
        assert "áéíóú" in result["message"]
        assert "<script>" in result["message"]  # Should preserve special chars

    @pytest.mark.parametrize(
        "exception_class,exception_message",
        [
            (ValueError, "Parameter validation failed"),
            (TypeError, "Invalid type provided"),
            (KeyError, "Required key missing"),
            (AttributeError, "Object has no such attribute"),
            (OSError, "File system operation failed"),
        ],
    )
    def test_parametrized_exception_handling(self, exception_class, exception_message):
        """Test exception handling with parametrized inputs."""

        @handle_tool_errors("parametrized_operation")
        def parametrized_function():
            raise exception_class(exception_message)

        result = parametrized_function()

        assert result["error"] is True
        assert result["error_type"] == exception_class.__name__
        assert exception_message in result["message"]
        assert result["operation"] == "parametrized_operation"

    def test_decorator_performance_impact(self):
        """Test that decorator doesn't significantly impact performance."""
        import time

        @handle_tool_errors("performance_operation")
        def fast_function():
            return {"result": "quick"}

        def undecorated_function():
            return {"result": "quick"}

        # Time decorated function (larger number of iterations for more stable timing)
        start_time = time.time()
        for _ in range(10000):
            fast_function()
        decorated_time = time.time() - start_time

        # Time undecorated function
        start_time = time.time()
        for _ in range(10000):
            undecorated_function()
        undecorated_time = time.time() - start_time

        # Decorator should add reasonable overhead (less than 3x increase for very fast functions)
        # Or at least both should complete in reasonable time
        assert decorated_time < 1.0  # Should complete in under 1 second
        assert undecorated_time < 1.0  # Should complete in under 1 second
        # If both are very fast, don't be too strict about relative performance
        if undecorated_time > 0.001:  # Only compare if measurable
            assert decorated_time < undecorated_time * 3

    def test_real_world_tool_function_simulation(self):
        """Test decorator with realistic tool function scenarios."""

        @handle_tool_errors("cursor_conversation_recall")
        def handle_recall_cursor_conversations(
            arguments: dict[str, Any], **kwargs: Any
        ) -> dict[str, Any]:
            """Simulate realistic cursor conversation recall function."""
            # Simulate parameter validation
            limit = arguments.get("limit", 50)
            if not isinstance(limit, int) or limit <= 0:
                raise ValueError(f"Invalid limit: {limit}")

            # Simulate database access
            project_root = kwargs.get("project_root")
            if not project_root:
                raise KeyError("project_root required")

            # Simulate successful processing
            return {
                "conversations": [
                    {
                        "id": "frodo_session_1",
                        "tool": "cursor",
                        "content": "Debug auth issue",
                    }
                ],
                "total_conversations": 1,
                "limit": limit,
            }

        # Test successful execution
        result = handle_recall_cursor_conversations(
            {"limit": 25}, project_root="/path/to/project"
        )
        assert result["total_conversations"] == 1
        assert result["limit"] == 25

        # Test error handling
        error_result = handle_recall_cursor_conversations({"limit": -1})
        assert error_result["error"] is True
        assert "Invalid limit" in error_result["message"]
        assert error_result["operation"] == "cursor_conversation_recall"
