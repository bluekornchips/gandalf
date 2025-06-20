"""
Scoring weights configuration for Gandalf MCP server.
Contains configurable weight values that affect agentic context for intelligence.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Try to import yaml, fall back to None if not available
try:
    import yaml

    HAS_YAML = True
except ImportError:
    yaml = None
    HAS_YAML = False


class WeightsLoader:
    """Handles loading configurable weight values from YAML with environment variable fallbacks.

    This class is specifically for AI scoring weights - multipliers and factors that
    affect how content is prioritized. System constants should use direct configuration.

    If PyYAML is not available, falls back to environment variables and defaults.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize the weights loader.

        Args:
            config_dir: Directory containing weights.yaml. Defaults to gandalf root.
        """
        if config_dir is None:
            # Default to gandalf directory (parent of config directory)
            config_dir = Path(__file__).parent.parent

        self.config_dir = config_dir
        self._weights_config = None
        self._weights_loaded = False

    def _load_weights_yaml(self) -> Optional[Dict[str, Any]]:
        """Load weights.yaml configuration file if PyYAML is available."""
        if not HAS_YAML:
            return None

        try:
            weights_file = self.config_dir / "weights.yaml"
            if weights_file.exists():
                with open(weights_file, "r") as f:
                    return yaml.safe_load(f)
        except (FileNotFoundError, Exception):
            pass

        return None

    def get_weight(
        self, yaml_path: str, env_var: str, default: float, description: str = ""
    ) -> float:
        """Get a scoring weight from YAML file or environment variable.

        This method is specifically for weights (multipliers/factors), not constants.

        Args:
            yaml_path: Dot-separated path in YAML (e.g., 'weights.recent_modification')
            env_var: Environment variable name
            default: Default weight value
            description: Human-readable description of what this weight affects

        Returns:
            The weight value as a float
        """
        # Ensure weights are loaded
        if not self._weights_loaded:
            self._weights_config = self._load_weights_yaml()
            self._weights_loaded = True

        config = self._weights_config
        if config and HAS_YAML:
            # Navigate YAML path
            value = config
            for key in yaml_path.split("."):
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    value = None
                    break

            if value is not None:
                return float(value)

        # Fall back to environment variable
        env_value = os.getenv(env_var, str(default))
        return float(env_value)

    def get_weight_dict(
        self, yaml_path: str, env_var: str = None, defaults: Dict[str, float] = None
    ) -> Dict[str, float]:
        """Get a dictionary of weights from YAML.

        Args:
            yaml_path: Path to the weight dictionary section in YAML
            env_var: Environment variable for JSON fallback (optional)
            defaults: Default weight dictionary if nothing found

        Returns:
            Dictionary with weight values as floats
        """
        # Ensure weights are loaded
        if not self._weights_loaded:
            self._weights_config = self._load_weights_yaml()
            self._weights_loaded = True

        # Try from weights config first (if YAML available)
        if self._weights_config and HAS_YAML:
            value = self._weights_config
            for key in yaml_path.split("."):
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    value = None
                    break

            if isinstance(value, dict):
                return {k: float(v) for k, v in value.items()}

        # Fall back to environment variable (JSON format)
        if env_var:
            try:
                env_data = json.loads(os.getenv(env_var, "{}"))
                return {k: float(v) for k, v in env_data.items()}
            except (json.JSONDecodeError, ValueError):
                pass

        # Return defaults
        defaults = defaults or {}
        return {k: float(v) for k, v in defaults.items()}


# Global weights loader instance
_weights_loader = WeightsLoader()

# Context Intelligence Weights

# File relevance scoring weights
CONTEXT_WEIGHTS = {
    "recent_modification": _weights_loader.get_weight(
        "weights.recent_modification",
        "WEIGHT_RECENT_MODIFICATION",
        5.0,
        "How much to prioritize recently modified files",
    ),
    "file_size_optimal": _weights_loader.get_weight(
        "weights.file_size_optimal",
        "WEIGHT_FILE_SIZE_OPTIMAL",
        2.0,
        "Bonus for files in the optimal size range",
    ),
    "import_relationship": _weights_loader.get_weight(
        "weights.import_relationship",
        "WEIGHT_IMPORT_RELATIONSHIP",
        4.0,
        "How much to prioritize files with import relationships",
    ),
    "conversation_mention": _weights_loader.get_weight(
        "weights.conversation_mention",
        "WEIGHT_CONVERSATION_MENTION",
        3.0,
        "Boost for files mentioned in recent conversations",
    ),
    "git_activity": _weights_loader.get_weight(
        "weights.git_activity",
        "WEIGHT_GIT_ACTIVITY",
        3.5,
        "How much to prioritize files with recent git activity",
    ),
    "file_type_priority": _weights_loader.get_weight(
        "weights.file_type_priority",
        "WEIGHT_FILE_TYPE_PRIORITY",
        1.5,
        "Multiplier for high-priority file extensions",
    ),
    "directory_importance": _weights_loader.get_weight(
        "weights.directory_importance",
        "WEIGHT_DIRECTORY_IMPORTANCE",
        1.0,
        "Multiplier for files in important directories",
    ),
}

# Conversation Analysis Weights

# Conversation prioritization weights
CONVERSATION_WEIGHTS = {
    "keyword_match": _weights_loader.get_weight(
        "conversation.keyword_match",
        "CONV_WEIGHT_KEYWORD_MATCH",
        3.0,
        "Weight for conversations matching project keywords",
    ),
    "file_reference": _weights_loader.get_weight(
        "conversation.file_reference",
        "CONV_WEIGHT_FILE_REFERENCE",
        4.0,
        "Weight for conversations referencing project files",
    ),
    "recency": _weights_loader.get_weight(
        "conversation.recency",
        "CONV_WEIGHT_RECENCY",
        2.0,
        "Weight for recent conversations",
    ),
    "technical_content": _weights_loader.get_weight(
        "conversation.technical_content",
        "CONV_WEIGHT_TECHNICAL",
        1.5,
        "Weight for conversations with technical content",
    ),
    "problem_solving": _weights_loader.get_weight(
        "conversation.problem_solving",
        "CONV_WEIGHT_PROBLEM_SOLVING",
        2.5,
        "Weight for problem-solving conversations",
    ),
    "architecture": _weights_loader.get_weight(
        "conversation.architecture",
        "CONV_WEIGHT_ARCHITECTURE",
        3.0,
        "Weight for architectural discussions",
    ),
    "debugging": _weights_loader.get_weight(
        "conversation.debugging",
        "CONV_WEIGHT_DEBUGGING",
        2.5,
        "Weight for debugging conversations",
    ),
}

# File Extension Weights


def get_file_extension_weights() -> Dict[str, float]:
    """Get file extension priority weights with dot prefixes.

    Priorities based on actual project usage analysis.
    Higher values mean the AI will consider these files more important.
    """
    defaults = {
        # Primary languages - highest priority
        ".py": 4.0,  # Python
        ".js": 3.8,  # JavaScript
        ".ts": 3.8,  # TypeScript
        ".tsx": 3.5,  # TypeScript React
        ".pyi": 3.0,  # Python type stubs
        # Infrastructure & Configuration - high priority
        ".tf": 3.5,  # Terraform
        ".yaml": 3.0,  # YAML
        ".yml": 3.0,  # YAML
        ".json": 2.8,  # JSON
        ".toml": 2.5,  # TOML
        # Web Technologies - medium-high priority
        ".html": 2.5,  # HTML
        ".css": 2.3,  # CSS
        ".scss": 2.3,  # SASS
        ".less": 2.0,  # LESS
        # Documentation - medium priority
        ".md": 2.0,  # Markdown
        ".mdx": 2.0,  # MDX
        ".txt": 1.5,  # Text
        # Scripts - medium priority
        ".sh": 2.2,  # Shell scripts
        # Configuration files - medium priority
        ".ini": 1.8,  # INI config
        ".cfg": 1.8,  # Config
        ".conf": 1.8,  # Config
        # Other formats - lower priority
        ".xml": 1.5,  # XML
        ".svg": 1.3,  # SVG
        # JavaScript variants - medium-high priority
        ".cjs": 3.0,  # CommonJS
        ".mjs": 3.0,  # ES Modules
        ".cts": 3.0,  # TypeScript CommonJS
        ".mts": 3.0,  # TypeScript Modules
    }

    return _weights_loader.get_weight_dict(
        "file_extensions", "FILE_EXTENSION_WEIGHTS", defaults
    )


# Directory Priority Weights


def get_directory_priority_weights() -> Dict[str, float]:
    """Get directory importance scores.

    These weights determine how much to prioritize files in different directories.
    """
    defaults = {
        # Source code directories - highest priority
        "src": 4.0,
        "lib": 3.8,
        "app": 3.5,
        "components": 3.3,
        "modules": 3.0,
        # Configuration and infrastructure - high priority
        "config": 3.0,
        "configs": 3.0,
        "terraform": 2.8,
        "infrastructure": 2.8,
        # Documentation - medium priority
        "docs": 2.5,
        "documentation": 2.5,
        "readme": 2.0,
        # Tests - medium priority
        "tests": 2.3,
        "test": 2.3,
        "__tests__": 2.3,
        "spec": 2.0,
        # Scripts and tools - medium priority
        "scripts": 2.2,
        "tools": 2.0,
        "bin": 2.0,
        "utils": 2.5,
        "utilities": 2.5,
        # Build and deployment - lower priority
        "build": 1.5,
        "dist": 1.2,
        "target": 1.2,
        # Assets and static files - lower priority
        "assets": 1.8,
        "static": 1.5,
        "public": 1.5,
        "images": 1.0,
        "img": 1.0,
        # Root level files - medium-high priority
        ".": 3.2,
        "": 3.2,  # Root directory
    }

    return _weights_loader.get_weight_dict(
        "directories", "DIRECTORY_PRIORITY_WEIGHTS", defaults
    )
