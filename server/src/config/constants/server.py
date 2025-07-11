"""Server identity and protocol configuration."""

import os

MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "gandalf")
GANDALF_SERVER_VERSION = os.getenv("GANDALF_SERVER_VERSION", "2.2.0")

MCP_PROTOCOL_VERSION = "2024-11-05"
JSONRPC_VERSION = "2.0"

# Server info and capabilities
SERVER_INFO = {"name": "gandalf-mcp", "version": GANDALF_SERVER_VERSION}
SERVER_CAPABILITIES = {"tools": {"listChanged": True}, "logging": {}}

# Environment variables for workspace detection
WORKSPACE_FOLDER_PATHS = os.getenv("WORKSPACE_FOLDER_PATHS")
GANDALF_SCOPE = os.getenv("GANDALF_SCOPE")
GANDALF_LOCAL_DIR = os.getenv("GANDALF_LOCAL_DIR")
