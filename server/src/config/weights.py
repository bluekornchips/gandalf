"""
Scoring weights configuration for Gandalf MCP server.
Uses custom schema validation for robust YAML validation.
"""

from pathlib import Path
from typing import Any

import yaml

from src.config.constants.limits import CONTEXT_MIN_SCORE
from src.utils.common import log_debug, log_error
from src.utils.schema_validation import (
    apply_schema_defaults,
    get_weights_file_path,
    get_weights_schema,
    validate_weights_config,
)


class WeightsConfig:
    """Schema-validated weights configuration using custom validation."""

    def __init__(self, config_dir: Path | None = None, validate: bool = True):
        """Initialize the weights configuration."""
        self.config_dir = config_dir
        self.validation_errors: list[str] = []
        self.is_valid = True

        # Load and validate configuration using the fallback system
        if validate:
            # Get the appropriate weights file (override, spec, or default)
            if config_dir is not None:
                weights_file = get_weights_file_path(config_dir)
            else:
                weights_file = get_weights_file_path()
            raw_config = self._load_config_from_file(weights_file)
            self.is_valid, self.validation_errors, self._config = (
                validate_weights_config(raw_config)
            )
        else:
            # Load from specified directory or use global system
            if config_dir is not None:
                weights_file = config_dir / "gandalf-weights.yaml"
            else:
                weights_file = get_weights_file_path()
            raw_config = self._load_config_from_file(weights_file)
            self._config = apply_schema_defaults(get_weights_schema(), raw_config)

    def _load_config_from_file(self, weights_file: Path) -> dict[str, Any]:
        """Load the weights configuration from a specific YAML file."""
        try:
            if weights_file.exists():
                with open(weights_file, encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            else:
                log_debug(f"No weights file found at {weights_file}, using defaults")
        except (OSError, yaml.YAMLError, PermissionError) as e:
            log_error(e, f"loading weights configuration from {weights_file}")

        return {}

    def get(self, path: str, default: Any = None) -> Any:
        """Get a value from the config using dot notation."""
        if default is None:
            default = CONTEXT_MIN_SCORE

        value = self._config
        for key in path.split("."):
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def get_dict(self, path: str) -> dict[str, Any]:
        """Get a dictionary from the config using dot notation."""
        value = self.get(path)
        return value if isinstance(value, dict) else {}

    def has_validation_errors(self) -> bool:
        """Check if configuration has validation errors."""
        return not self.is_valid

    def get_validation_errors(self) -> list[str]:
        """Get list of validation errors."""
        return self.validation_errors

    def get_file_extension_weights(self) -> dict[str, float]:
        """Get file extension priority weights with dot prefixes."""
        weights_dict = self.get_dict("file_extensions")
        # Add dot prefixes and convert to float
        return {f".{ext}": float(weight) for ext, weight in weights_dict.items()}

    def get_directory_priority_weights(self) -> dict[str, float]:
        """Get directory importance scores."""
        weights_dict = self.get_dict("directories")
        # Convert to float
        return {dir_name: float(weight) for dir_name, weight in weights_dict.items()}

    def get_weights_validation_status(self) -> dict[str, Any]:
        """Get validation status of the weights configuration."""
        has_errors = self.has_validation_errors()
        error_count = len(self.validation_errors)

        if has_errors:
            message = f"Configuration has {error_count} validation errors"
        else:
            message = "Configuration is valid"

        return {
            "has_errors": has_errors,
            "error_count": error_count,
            "status": "invalid" if has_errors else "valid",
            "message": message,
        }

    def get_schema(self) -> dict[str, Any]:
        """Get the schema for weights configuration."""
        return get_weights_schema()


class WeightsManager:
    """Manages weights configuration instances with dependency injection."""

    _default_instance: WeightsConfig | None = None

    @classmethod
    def get_default(cls) -> WeightsConfig:
        """Get the default weights configuration instance."""
        if cls._default_instance is None:
            cls._default_instance = WeightsConfig()
        return cls._default_instance

    @classmethod
    def set_default(cls, config: WeightsConfig) -> None:
        """Set the default weights configuration instance."""
        cls._default_instance = config

    @classmethod
    def create_instance(
        cls, config_dir: Path | None = None, validate: bool = True
    ) -> WeightsConfig:
        """Create a new weights configuration instance."""
        return WeightsConfig(config_dir=config_dir, validate=validate)

    @classmethod
    def reset_default(cls) -> None:
        """Reset the default instance (useful for testing)."""
        cls._default_instance = None
