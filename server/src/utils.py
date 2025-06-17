"""Utility functions for the MCP server."""

import json
import re
from typing import Any, Dict, Optional

from config.constants import MCP_DEBUG


def send_json_rpc_message(method: str, params: Dict[str, Any], logger: Optional[str] = None):
    """Send a JSON-RPC message to stdout."""
    message = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params
    }
    
    if logger:
        message["params"]["logger"] = logger
    
    print(json.dumps(message), flush=True)


def send_log_notification(level: str, message: str, logger: Optional[str] = None, data: Optional[dict] = None) -> None:
    """Send a log notification via JSON-RPC."""
    params = {
        "level": level,
        "message": message
    }
    
    if logger:
        params["logger"] = logger
    
    if data:
        params["data"] = data
    
    send_json_rpc_message("notifications/message", params)


def log_info(message: str) -> None:
    """Log an info message via MCP notification if MCP_DEBUG is enabled."""
    if MCP_DEBUG:
        send_log_notification("info", message)


def log_error(error: Exception, context: str = "") -> None:
    """Log an error message via MCP notification if MCP_DEBUG is enabled."""
    if MCP_DEBUG:
        error_msg = f"{context}: {error}" if context else str(error)
        send_log_notification("error", error_msg)


def debug_log(message: str) -> None:
    """Send debug log via MCP notification if MCP_DEBUG is enabled."""
    if MCP_DEBUG:
        send_log_notification("debug", message)


def validate_conversation_id(conversation_id: str) -> bool:
    """Validate conversation ID format."""
    if not conversation_id or len(conversation_id) < 1:
        return False
    
    # Allow alphanumeric, hyphens, underscores
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', conversation_id))


def sanitize_filename(filename: str) -> str:
    """Convert a string to a safe filename."""
    # Remove or replace unsafe characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(' .')
    # Limit length
    return sanitized[:255] if sanitized else 'unnamed'
