"""
Core configuration constants for Gandalf MCP server.
Contains server identity, MCP protocol settings, and basic system configuration.
"""

import os
from pathlib import Path

# Project name and paths
MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "gandalf")
GANDALF_HOME = Path(
    os.getenv("GANDALF_HOME")
    or (
        str(Path(os.getenv("HOME", str(Path.home())))) + f"/.{MCP_SERVER_NAME}"
    )
)

# MCP Protocol
MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_VERSION = "1.0.0"
SERVER_INFO = {"name": "gandalf-mcp", "version": SERVER_VERSION}

# MCP server capabilities - tells clients what features this server supports
# listChanged: true = server can notify when tool list changes
# logging: {} = server supports logging notifications to client
SERVER_CAPABILITIES = {"tools": {"listChanged": True}, "logging": {}}

# Relevant only when working in Cursor
WORKSPACE_FOLDER_PATHS = os.getenv("WORKSPACE_FOLDER_PATHS")
