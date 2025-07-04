"""
Scoring weights configuration for Gandalf MCP server.
Loads weights from gandalf-weights.yaml with clean dictionary access.
"""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional

from config.constants import CONTEXT_MIN_SCORE


class WeightsConfig:
    """Clean weights configuration loader."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize the weights configuration.

        Args:
            config_dir: Directory containing gandalf-weights.yaml. Defaults to gandalf spec.
        """
        if config_dir is None:
            # Go up to the gandalf root, then to spec directory
            config_dir = Path(__file__).parent.parent.parent.parent / "spec"

        self.config_dir = config_dir
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load the weights configuration from YAML file."""
        try:
            weights_file = self.config_dir / "gandalf-weights.yaml"
            if weights_file.exists():
                with open(weights_file, "r") as f:
                    return yaml.safe_load(f) or {}
        except (OSError, IOError, yaml.YAMLError, PermissionError):
            pass

        return {}

    def get(self, path: str) -> Any:
        """Get a value from the config using dot notation.

        Args:
            path: Dot-separated path
            default: Default value if not found, 'CONTEXT_MIN_SCORE'

        Returns:
            The value or CONTEXT_MIN_SCORE
        """
        value = self._config
        for key in path.split("."):
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return CONTEXT_MIN_SCORE
        return value

    def get_dict(self, path: str) -> Dict[str, Any]:
        """Get a dictionary from the config.

        Args:
            path: Dot-separated path to dictionary

        Returns:
            Dictionary or empty dict if not found
        """
        value = self.get(path)
        return value if isinstance(value, dict) else {}


# Global weights configuration
_weights = WeightsConfig()

# Core weights dictionaries
CONTEXT_WEIGHTS = _weights.get_dict("weights")
CONVERSATION_WEIGHTS = _weights.get_dict("conversation")

# Individual weight constants
CONVERSATION_KEYWORD_WEIGHT = _weights.get("conversation.keyword_weight")
CONVERSATION_FILE_REF_SCORE = _weights.get("conversation.file_ref_score")
ACTIVITY_SCORE_RECENCY_BOOST = _weights.get("context.activity_score_recency_boost")
CONVERSATION_EARLY_TERMINATION_MULTIPLIER = _weights.get(
    "processing.conversation_early_termination_multiplier"
)
EARLY_TERMINATION_LIMIT_MULTIPLIER = _weights.get(
    "processing.early_termination_limit_multiplier"
)

# Recency thresholds
CONVERSATION_RECENCY_THRESHOLDS = _weights.get_dict("recency_thresholds")

# Activity scoring constants
ACTIVITY_SCORE_MAX_DURATION = 30  # days

# Context file size constants
CONTEXT_FILE_SIZE_ACCEPTABLE_MULTIPLIER = _weights.get(
    "context.file_size.acceptable_multiplier"
)
CONTEXT_FILE_SIZE_LARGE_MULTIPLIER = _weights.get("context.file_size.large_multiplier")
CONTEXT_FILE_SIZE_OPTIMAL_MAX = _weights.get("context.file_size.optimal_max")
CONTEXT_FILE_SIZE_OPTIMAL_MIN = _weights.get("context.file_size.optimal_min")

# Context recent modification constants
CONTEXT_RECENT_DAY_MULTIPLIER = _weights.get(
    "context.recent_modifications.day_multiplier"
)
CONTEXT_RECENT_DAY_THRESHOLD = _weights.get(
    "context.recent_modifications.day_threshold"
)
CONTEXT_RECENT_HOUR_THRESHOLD = _weights.get(
    "context.recent_modifications.hour_threshold"
)
CONTEXT_RECENT_WEEK_MULTIPLIER = _weights.get(
    "context.recent_modifications.week_multiplier"
)
CONTEXT_RECENT_WEEK_THRESHOLD = _weights.get(
    "context.recent_modifications.week_threshold"
)


def get_file_extension_weights() -> Dict[str, float]:
    """Get file extension priority weights with dot prefixes."""
    weights_dict = _weights.get_dict("file_extensions")
    # Add dot prefixes and convert to float
    return {f".{ext}": float(weight) for ext, weight in weights_dict.items()}


def get_directory_priority_weights() -> Dict[str, float]:
    """Get directory importance scores."""
    weights_dict = _weights.get_dict("directories")
    # Convert to float
    return {dir_name: float(weight) for dir_name, weight in weights_dict.items()}
