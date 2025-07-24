"""Test JSONRPC constants and enums."""

from src.config.constants.server_config import JSONRPC_VERSION
from src.config.enums import ErrorCodes


class TestJsonRpcConstants:
    """Test JSON-RPC protocol constants."""

    def test_jsonrpc_version(self):
        """Test JSON-RPC version constant."""
        assert JSONRPC_VERSION == "2.0"

    def test_error_codes_values(self):
        """Test that error codes match JSON-RPC specification."""
        assert ErrorCodes.PARSE_ERROR == -32700
        assert ErrorCodes.INVALID_REQUEST == -32600
        assert ErrorCodes.METHOD_NOT_FOUND == -32601
        assert ErrorCodes.INVALID_PARAMS == -32602
        assert ErrorCodes.INTERNAL_ERROR == -32603

    def test_error_codes_are_enum(self):
        """Test that ErrorCodes is a proper enum."""
        assert isinstance(ErrorCodes.PARSE_ERROR, int)
        assert ErrorCodes.PARSE_ERROR.name == "PARSE_ERROR"
        assert ErrorCodes.PARSE_ERROR.value == -32700

    def test_error_codes_iteration(self):
        """Test that ErrorCodes can be iterated over."""
        error_codes = list(ErrorCodes)
        assert len(error_codes) >= 5  # We have at least the JSON-RPC error codes
        assert ErrorCodes.PARSE_ERROR in error_codes
        assert ErrorCodes.INTERNAL_ERROR in error_codes
        assert ErrorCodes.METHOD_NOT_FOUND in error_codes
        assert ErrorCodes.INVALID_REQUEST in error_codes
        assert ErrorCodes.INVALID_PARAMS in error_codes
