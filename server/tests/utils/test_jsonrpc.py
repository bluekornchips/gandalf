"""Test JSON-RPC utility functions."""

import pytest

from src.config.constants import ErrorCodes
from src.utils.jsonrpc import create_error_response, create_success_response


class TestErrorResponseCreation:
    """Test error response creation utilities."""

    def test_create_error_response_basic(self):
        """Test creating basic error response."""
        response = create_error_response(
            ErrorCodes.METHOD_NOT_FOUND,
            "The method 'summon_eagles' was not found in the Shire",
            "gandalf_1",
        )

        expected = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": "The method 'summon_eagles' was not found in the Shire",
            },
            "id": "gandalf_1",
        }

        assert response == expected

    def test_create_error_response_no_id(self):
        """Test creating error response without request ID (parse errors)."""
        response = create_error_response(
            ErrorCodes.PARSE_ERROR, "The One Ring corrupted the JSON"
        )

        expected = {
            "jsonrpc": "2.0",
            "error": {"code": -32700, "message": "The One Ring corrupted the JSON"},
            "id": None,
        }

        assert response == expected

    def test_create_error_response_with_data(self):
        """Test creating error response with additional data."""
        error_data = {
            "location": "Mount Doom",
            "cause": "Ring destroyed",
            "severity": "controversial",
        }

        response = create_error_response(
            ErrorCodes.INTERNAL_ERROR,
            "The server has fallen into shadow",
            "sauron",
            error_data,
        )

        expected = {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "The server has fallen into shadow",
                "data": error_data,
            },
            "id": "sauron",
        }

        assert response == expected

    def test_create_error_response_numeric_id(self):
        """Test creating error response with numeric ID."""
        response = create_error_response(
            ErrorCodes.INVALID_PARAMS,
            "The parameters for crossing the Bridge of Khazad-dûm are invalid",
            100,
        )

        assert response["id"] == 100
        assert response["error"]["code"] == ErrorCodes.INVALID_PARAMS

    def test_create_error_response_null_id(self):
        """Test creating error response with explicit null ID."""
        response = create_error_response(
            ErrorCodes.PARSE_ERROR, "JSON parsing failed in Moria", None
        )

        assert response["id"] is None

    def test_create_error_response_empty_data(self):
        """Test creating error response with empty data dict."""
        response = create_error_response(
            ErrorCodes.INTERNAL_ERROR, "Something went wrong in Rohan", "theoden_1", {}
        )

        # Empty data should be omitted (JSON-RPC spec compliance)
        assert "data" not in response["error"]
        assert response["error"]["code"] == ErrorCodes.INTERNAL_ERROR
        assert response["error"]["message"] == "Something went wrong in Rohan"
        assert response["id"] == "theoden_1"

    def test_create_error_response_with_enum(self):
        """Test creating error response using enum values directly."""
        response = create_error_response(
            ErrorCodes.PARSE_ERROR,
            "Enum-based error in the Prancing Pony",
            "barliman_1",
        )

        assert response["error"]["code"] == -32700
        assert response["error"]["code"] == ErrorCodes.PARSE_ERROR
        assert "Enum-based error" in response["error"]["message"]


class TestSuccessResponseCreation:
    """Test success response creation utilities."""

    def test_create_success_response_basic(self):
        """Test creating basic success response."""
        result_data = {"status": "The Shire is safe", "hobbits_saved": 4}

        response = create_success_response(result_data, "frodo_1")

        expected = {"jsonrpc": "2.0", "result": result_data, "id": "frodo_1"}

        assert response == expected

    def test_create_success_response_numeric_id(self):
        """Test creating success response with numeric ID."""
        result_data = {"message": "The beacons are lit"}

        response = create_success_response(result_data, 123)

        assert response["id"] == 123
        assert response["result"] == result_data

    def test_create_success_response_null_result(self):
        """Test creating success response with null result."""
        response = create_success_response(None, "sam_2")

        expected = {"jsonrpc": "2.0", "result": None, "id": "sam_2"}

        assert response == expected

    def test_create_success_response_empty_result(self):
        """Test creating success response with empty result."""
        response = create_success_response({}, "merry_3")

        expected = {"jsonrpc": "2.0", "result": {}, "id": "merry_3"}

        assert response == expected

    def test_create_success_response_list_result(self):
        """Test creating success response with list result."""
        result_data = ["Aragorn", "Legolas", "Gimli"]

        response = create_success_response(result_data, "pippin_4")

        expected = {"jsonrpc": "2.0", "result": result_data, "id": "pippin_4"}

        assert response == expected

    def test_create_success_response_string_result(self):
        """Test creating success response with string result."""
        result_data = "You shall not pass!"

        response = create_success_response(result_data, "gandalf_the_grey")

        expected = {"jsonrpc": "2.0", "result": result_data, "id": "gandalf_the_grey"}

        assert response == expected


class TestResponseStructureValidation:
    """Test that generated responses have correct structure."""

    def test_error_response_has_required_fields(self):
        """Test that error responses have all required fields."""
        response = create_error_response(
            ErrorCodes.METHOD_NOT_FOUND, "Test error", "test_id"
        )

        # Required fields for error response
        assert "jsonrpc" in response
        assert "error" in response
        assert "id" in response

        # Error object structure
        assert "code" in response["error"]
        assert "message" in response["error"]

        # Values
        assert response["jsonrpc"] == "2.0"
        assert isinstance(response["error"]["code"], int)
        assert isinstance(response["error"]["message"], str)

    def test_success_response_has_required_fields(self):
        """Test that success responses have all required fields."""
        response = create_success_response({"test": "data"}, "test_id")

        # Required fields for success response
        assert "jsonrpc" in response
        assert "result" in response
        assert "id" in response

        # Values
        assert response["jsonrpc"] == "2.0"

    def test_error_response_no_result_field(self):
        """Test that error responses don't have result field."""
        response = create_error_response(
            ErrorCodes.INTERNAL_ERROR, "Test error", "test_id"
        )

        assert "result" not in response

    def test_success_response_no_error_field(self):
        """Test that success responses don't have error field."""
        response = create_success_response({"test": "data"}, "test_id")

        assert "error" not in response

    def test_enum_integration(self):
        """Test that enum values work correctly in responses."""
        # Test that we can use the enum directly
        response = create_error_response(
            ErrorCodes.INVALID_REQUEST,
            "The request from Bag End was malformed",
            "hobbit_1",
        )

        # Verify the enum value is correctly converted to int
        assert response["error"]["code"] == -32600
        assert response["error"]["code"] == ErrorCodes.INVALID_REQUEST.value

        # Test enum comparison
        assert response["error"]["code"] == ErrorCodes.INVALID_REQUEST
