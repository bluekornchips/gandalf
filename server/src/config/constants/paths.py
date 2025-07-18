"""Path management with proper separation of gandalf home and file system context."""

import os
from pathlib import Path

# Project structure constants
GANDALF_HOME = Path(os.getenv("GANDALF_HOME", str(Path.home() / ".gandalf")))

# Gandalf installation detection - find spec directory relative to this file
# This file is at: gandalf/server/src/config/constants/paths.py
# Spec directory is at: gandalf/spec/
_CURRENT_FILE = Path(__file__).resolve()
_GANDALF_ROOT = _CURRENT_FILE.parent.parent.parent.parent.parent  # Go up 5 levels
GANDALF_SPEC_DIR = _GANDALF_ROOT / "spec"

# Gandalf configuration directories
GANDALF_CONFIG_DIR = GANDALF_HOME / "config"

# Weights Configuration - can be overridden for testing
DEFAULT_WEIGHTS_FILE = GANDALF_CONFIG_DIR / "gandalf-weights.yaml"
SPEC_WEIGHTS_FILE = GANDALF_SPEC_DIR / "gandalf-weights.yaml"

# Allow override for testing via environment variable
WEIGHTS_FILE_OVERRIDE = os.getenv("GANDALF_WEIGHTS_FILE")

# Cache Directories
CACHE_ROOT_DIR = GANDALF_HOME / "cache"
CONVERSATION_CACHE_DIR = CACHE_ROOT_DIR / "conversations"
FILE_CACHE_DIR = CACHE_ROOT_DIR / "files"
GIT_CACHE_DIR = CACHE_ROOT_DIR / "git"

# Cache Files
CONVERSATION_CACHE_FILE = CONVERSATION_CACHE_DIR / "conversations.json"
CONVERSATION_CACHE_METADATA_FILE = CONVERSATION_CACHE_DIR / "metadata.json"

# Application directories - Cursor
CURSOR_WORKSPACE_STORAGE_PATH = "Application Support/Cursor/User/workspaceStorage"
CURSOR_WORKSPACE_STORAGE = [
    Path.home()
    / "Library"
    / "Application Support"
    / "Cursor"
    / "User"
    / "workspaceStorage"
]

# Application directories - Windsurf
WINDSURF_WORKSPACE_STORAGE = [
    Path.home()
    / "Library"
    / "Application Support"
    / "Windsurf"
    / "User"
    / "workspaceStorage"
]

WINDSURF_GLOBAL_STORAGE = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Windsurf"
    / "User"
    / "globalStorage"
)

CLAUDE_HOME = [Path.home() / ".claude"]
