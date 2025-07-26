"""
JSON-RPC utilities for Gandalf MCP server.
Contains helper functions for creating standardized JSON-RPC responses.
"""

from typing import Any

from src.config.core_constants import JSONRPC_VERSION


def create_error_response(
    code: int,
    message: str,
    request_id: Any | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a standardized JSON-RPC error response."""
    error_dict: dict[str, Any] = {"code": code, "message": message}
    if data:
        error_dict["data"] = data

    error_response: dict[str, Any] = {
        "jsonrpc": JSONRPC_VERSION,
        "error": error_dict,
        "id": request_id,
    }

    return error_response


def create_success_response(result: Any, request_id: Any) -> dict[str, Any]:
    """Create a standardized JSON-RPC success response."""
    return {
        "jsonrpc": JSONRPC_VERSION,
        "result": result,
        "id": request_id,
    }
