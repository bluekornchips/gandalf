"""Agentic tool configuration and constants."""

# Supported Tools
AGENTIC_TOOL_CURSOR = "cursor"
AGENTIC_TOOL_CLAUDE_CODE = "claude-code"
AGENTIC_TOOL_WINDSURF = "windsurf"
SUPPORTED_AGENTIC_TOOLS = [
    AGENTIC_TOOL_CURSOR,
    AGENTIC_TOOL_CLAUDE_CODE,
    AGENTIC_TOOL_WINDSURF,
]

# Registry
REGISTRY_FILENAME = "registry.json"
GANDALF_HOME_ENV = "GANDALF_HOME"  # Why do we need this?
DEFAULT_GANDALF_HOME = "~/.gandalf"
