"""
Simple registry reader for agentic tool installations.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from config.constants import (
    AGENTIC_TOOL_CLAUDE_CODE,
    AGENTIC_TOOL_CURSOR,
    AGENTIC_TOOL_WINDSURF,
    CLAUDE_CONVERSATION_PATTERNS,
    CURSOR_DB_PATTERNS,
    WINDSURF_DB_PATTERNS,
    CURSOR_WORKSPACE_STORAGE_PATH,
    DEFAULT_GANDALF_HOME,
    GANDALF_HOME_ENV,
    REGISTRY_FILENAME,
)
from utils.common import log_debug, log_error


def get_registry_path() -> Path:
    """Get the path to the registry file."""
    gandalf_home = os.environ.get(GANDALF_HOME_ENV)
    if gandalf_home is None:
        gandalf_home = os.path.expanduser(DEFAULT_GANDALF_HOME)
    return Path(gandalf_home) / REGISTRY_FILENAME


def read_registry() -> Dict[str, str]:
    """Read the registry file and return agentic tool name to path mapping."""
    registry_path = get_registry_path()

    if not registry_path.exists():
        log_debug("Registry file not found, returning empty registry")
        return {}

    try:
        with open(registry_path, "r") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            log_error("Registry file is not a valid JSON object")
            return {}

        return data

    except json.JSONDecodeError as e:
        log_error(e, "parsing registry file")
        return {}
    except (OSError, IOError, PermissionError) as e:
        log_error(e, "reading registry file")
        return {}


def get_agentic_tool_path(tool_name: str) -> Optional[str]:
    """Get the installation path for a specific agentic tool."""
    registry = read_registry()
    return registry.get(tool_name)


def get_registered_agentic_tools() -> List[str]:
    """Get list of registered agentic tool names."""
    registry = read_registry()
    return list(registry.keys())


def find_cursor_conversations(cursor_path: str) -> List[str]:
    """Find conversation databases for Cursor installation."""
    conversations = []

    # Cursor stores conversations in workspaceStorage
    workspace_storage = Path(cursor_path).parent / CURSOR_WORKSPACE_STORAGE_PATH

    if not workspace_storage.exists():
        log_debug(f"Cursor workspace storage not found: {workspace_storage}")
        return conversations

    # Find database files using defined patterns
    for pattern in CURSOR_DB_PATTERNS:
        for db_file in workspace_storage.rglob(pattern):
            db_path = str(db_file)
            if db_path not in conversations:
                conversations.append(db_path)

    log_debug(f"Found {len(conversations)} Cursor conversation databases")
    return conversations


def find_claude_conversations(claude_path: str) -> List[str]:
    """Find conversation files for Claude Code installation."""
    conversations = []

    # Claude Code stores conversations in consistent folder structure
    claude_config = Path(claude_path)

    # Check common conversation file locations using defined patterns
    for pattern in CLAUDE_CONVERSATION_PATTERNS:
        for conv_file in claude_config.glob(pattern):
            if conv_file.is_file():
                conversations.append(str(conv_file))

    log_debug(f"Found {len(conversations)} Claude Code conversation files")
    return conversations


def find_windsurf_conversations(windsurf_path: str) -> List[str]:
    """Find conversation databases for Windsurf installation."""
    conversations = []

    # Windsurf stores conversations in workspace-specific directories
    # The path structure is similar to Cursor because its a fork of vscode
    windsurf_storage = Path(windsurf_path)

    if not windsurf_storage.exists():
        log_debug(f"Windsurf storage not found: {windsurf_storage}")
        return conversations

    # Find database files in workspace directories using defined patterns
    for workspace_dir in windsurf_storage.iterdir():
        if workspace_dir.is_dir():
            for pattern in WINDSURF_DB_PATTERNS:
                for db_file in workspace_dir.glob(pattern):
                    if db_file.is_file():
                        db_path = str(db_file)
                        if db_path not in conversations:
                            conversations.append(db_path)

    log_debug(f"Found {len(conversations)} Windsurf conversation databases")
    return conversations


def get_all_conversations() -> Dict[str, List[str]]:
    """Get all conversation files for all registered agentic tools."""
    registry = read_registry()
    all_conversations = {}

    for tool_name, tool_path in registry.items():
        if tool_name == AGENTIC_TOOL_CURSOR:
            conversations = find_cursor_conversations(tool_path)
        elif tool_name == AGENTIC_TOOL_CLAUDE_CODE:
            conversations = find_claude_conversations(tool_path)
        elif tool_name == AGENTIC_TOOL_WINDSURF:
            conversations = find_windsurf_conversations(tool_path)
        else:
            log_debug(f"Unknown agentic tool type: {tool_name}")
            conversations = []

        if conversations:
            all_conversations[tool_name] = conversations

    return all_conversations
