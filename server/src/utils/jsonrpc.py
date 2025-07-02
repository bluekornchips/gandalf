"""
JSON-RPC utilities for Gandalf MCP server.
Contains helper functions for creating standardized JSON-RPC responses.
"""

from typing import Any, Dict, Optional

from config.constants import JSONRPC_VERSION


def create_error_response(
    code: int,
    message: str,
    request_id: Optional[Any] = None,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a standardized JSON-RPC error response.

    Args:
        code: JSON-RPC error code
        message: Human-readable error message
        request_id: ID from the original request (None for parse errors)
        data: Additional error data (optional)

    Returns:
        Dict containing the JSON-RPC error response
    """
    error_response = {
        "jsonrpc": JSONRPC_VERSION,
        "error": {"code": code, "message": message},
        "id": request_id,
    }

    if data:
        error_response["error"]["data"] = data

    return error_response


def create_success_response(result: Any, request_id: Any) -> Dict[str, Any]:
    """Create a standardized JSON-RPC success response.

    Args:
        result: The result data to return
        request_id: ID from the original request

    Returns:
        Dict containing the JSON-RPC success response
    """
    return {
        "jsonrpc": JSONRPC_VERSION,
        "result": result,
        "id": request_id,
    }
