"""Server identity and protocol configuration."""

import os

from src.utils.version import get_version

MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "gandalf")
GANDALF_SERVER_VERSION = os.getenv("GANDALF_SERVER_VERSION", get_version())

MCP_PROTOCOL_VERSION = "2025-06-18"
JSONRPC_VERSION = "2.0"

# Server info and capabilities
SERVER_INFO = {"name": "gandalf-mcp", "version": GANDALF_SERVER_VERSION}
SERVER_CAPABILITIES = {"tools": {"listChanged": True}, "logging": {}}

# Command execution timeouts
SUBPROCESS_TIMEOUT = 5  # seconds

# Environment
WORKSPACE_FOLDER_PATHS = os.getenv("WORKSPACE_FOLDER_PATHS")
DEBUG_LOGGING = bool(os.getenv("GANDALF_DEBUG_LOGGING"))
