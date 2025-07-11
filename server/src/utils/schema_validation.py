"""
Schema validation utilities using Cerberus.
Provides reusable validation schemas and functions for configuration.
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml
from cerberus import Validator

from src.config.constants.context import (
    CONTEXT_FILE_SIZE_OPTIMAL_MAX,
)
from src.config.constants.limits import (
    VALIDATION_CONVERSATION_PARAM_MAX,
    VALIDATION_FILE_SIZE_MIN,
    VALIDATION_TIME_THRESHOLD_MAX_HOURS,
    VALIDATION_TIME_THRESHOLD_MIN,
    VALIDATION_WEIGHT_MIN,
)
from src.config.constants.paths import (
    DEFAULT_WEIGHTS_FILE,
    SPEC_WEIGHTS_FILE,
    WEIGHTS_FILE_OVERRIDE,
)
from src.utils.common import log_debug, log_error, log_info

# Cerberus schema for weights configuration
WEIGHTS_SCHEMA = {
    "weights": {
        "type": "dict",
        "required": True,
        "schema": {
            "recent_modification": {
                "type": "number",
                "min": VALIDATION_WEIGHT_MIN,
                "max": VALIDATION_CONVERSATION_PARAM_MAX,
                "default": 1.0,
            },
            "file_size_optimal": {
                "type": "number",
                "min": VALIDATION_WEIGHT_MIN,
                "max": VALIDATION_CONVERSATION_PARAM_MAX,
                "default": 1.0,
            },
            "file_type_priority": {
                "type": "number",
                "min": VALIDATION_WEIGHT_MIN,
                "max": VALIDATION_CONVERSATION_PARAM_MAX,
                "default": 1.0,
            },
            "directory_importance": {
                "type": "number",
                "min": VALIDATION_WEIGHT_MIN,
                "max": VALIDATION_CONVERSATION_PARAM_MAX,
                "default": 1.0,
            },
            "git_activity": {
                "type": "number",
                "min": VALIDATION_WEIGHT_MIN,
                "max": VALIDATION_CONVERSATION_PARAM_MAX,
                "default": 1.0,
            },
        },
    },
    "conversation": {
        "type": "dict",
        "required": True,
        "schema": {
            "keyword_match": {
                "type": "number",
                "min": VALIDATION_WEIGHT_MIN,
                "max": VALIDATION_CONVERSATION_PARAM_MAX,
                "default": 1.0,
            },
            "keyword_weight": {
                "type": "number",
                "min": VALIDATION_WEIGHT_MIN,
                "max": 1,
                "default": 0.1,
            },
            "recency": {
                "type": "number",
                "min": VALIDATION_WEIGHT_MIN,
                "max": VALIDATION_CONVERSATION_PARAM_MAX,
                "default": 1.0,
            },
            "file_reference": {
                "type": "number",
                "min": VALIDATION_WEIGHT_MIN,
                "max": VALIDATION_CONVERSATION_PARAM_MAX,
                "default": 1.0,
            },
            "file_reference_score": {
                "type": "number",
                "min": VALIDATION_WEIGHT_MIN,
                "max": 1,
                "default": 0.2,
            },
            "type_bonuses": {
                "type": "dict",
                "default": {
                    "debugging": 0.25,
                    "architecture": 0.2,
                    "testing": 0.15,
                    "code_discussion": 0.1,
                    "problem_solving": 0.1,
                    "general": 0.0,
                },
                "valuesrules": {
                    "type": "number",
                    "min": VALIDATION_WEIGHT_MIN,
                    "max": 1,
                },
            },
        },
    },
    "recency_thresholds": {
        "type": "dict",
        "required": True,
        "schema": {
            "days_1": {
                "type": "number",
                "min": VALIDATION_WEIGHT_MIN,
                "max": VALIDATION_CONVERSATION_PARAM_MAX,
                "default": 1.0,
            },
            "days_7": {
                "type": "number",
                "min": VALIDATION_WEIGHT_MIN,
                "max": VALIDATION_CONVERSATION_PARAM_MAX,
                "default": 0.8,
            },
            "days_30": {
                "type": "number",
                "min": VALIDATION_WEIGHT_MIN,
                "max": VALIDATION_CONVERSATION_PARAM_MAX,
                "default": 0.5,
            },
            "days_90": {
                "type": "number",
                "min": VALIDATION_WEIGHT_MIN,
                "max": VALIDATION_CONVERSATION_PARAM_MAX,
                "default": 0.2,
            },
            "default": {
                "type": "number",
                "min": VALIDATION_WEIGHT_MIN,
                "max": VALIDATION_CONVERSATION_PARAM_MAX,
                "default": 0.1,
            },
        },
    },
    "context": {
        "type": "dict",
        "required": True,
        "schema": {
            "file_size": {
                "type": "dict",
                "schema": {
                    "optimal_min": {
                        "type": "integer",
                        "min": VALIDATION_FILE_SIZE_MIN,
                        "default": 100,
                    },
                    "optimal_max": {
                        "type": "integer",
                        "min": VALIDATION_FILE_SIZE_MIN,
                        "default": CONTEXT_FILE_SIZE_OPTIMAL_MAX,
                    },
                    "acceptable_multiplier": {
                        "type": "number",
                        "min": VALIDATION_WEIGHT_MIN,
                        "max": 1,
                        "default": 0.7,
                    },
                    "large_multiplier": {
                        "type": "number",
                        "min": VALIDATION_WEIGHT_MIN,
                        "max": 1,
                        "default": 0.3,
                    },
                },
            },
            "recent_modifications": {
                "type": "dict",
                "schema": {
                    "hour_threshold": {
                        "type": "integer",
                        "min": VALIDATION_TIME_THRESHOLD_MIN,
                        "default": 2,
                    },
                    "day_threshold": {
                        "type": "integer",
                        "min": VALIDATION_TIME_THRESHOLD_MIN,
                        "default": 24,
                    },
                    "week_threshold": {
                        "type": "integer",
                        "min": VALIDATION_TIME_THRESHOLD_MIN,
                        "default": VALIDATION_TIME_THRESHOLD_MAX_HOURS,
                    },
                    "day_multiplier": {
                        "type": "number",
                        "min": VALIDATION_WEIGHT_MIN,
                        "max": 1,
                        "default": 0.8,
                    },
                    "week_multiplier": {
                        "type": "number",
                        "min": VALIDATION_WEIGHT_MIN,
                        "max": 1,
                        "default": 0.5,
                    },
                },
            },
            "activity_score_recency_boost": {
                "type": "number",
                "min": VALIDATION_WEIGHT_MIN,
                "max": VALIDATION_CONVERSATION_PARAM_MAX,
                "default": 1.5,
            },
        },
    },
    "processing": {
        "type": "dict",
        "required": True,
        "schema": {
            "conversation_early_termination_multiplier": {
                "type": "number",
                "min": VALIDATION_WEIGHT_MIN,
                "max": VALIDATION_CONVERSATION_PARAM_MAX,
                "default": 0.8,
            },
            "early_termination_limit_multiplier": {
                "type": "number",
                "min": VALIDATION_WEIGHT_MIN,
                "max": VALIDATION_CONVERSATION_PARAM_MAX,
                "default": 1.5,
            },
        },
    },
    "file_extensions": {
        "type": "dict",
        "default": {
            "py": 1.0,
            "js": 0.9,
            "ts": 0.9,
            "jsx": 0.8,
            "tsx": 0.8,
            "vue": 0.8,
            "md": 0.6,
            "txt": 0.3,
            "json": 0.5,
            "yaml": 0.5,
            "yml": 0.5,
        },
        "valuesrules": {
            "type": "number",
            "min": VALIDATION_WEIGHT_MIN,
            "max": VALIDATION_CONVERSATION_PARAM_MAX,
        },
    },
    "directories": {
        "type": "dict",
        "default": {
            "src": 1.0,
            "lib": 0.9,
            "app": 0.9,
            "components": 0.8,
            "utils": 0.7,
            "tests": 0.6,
            "docs": 0.4,
            "examples": 0.3,
        },
        "valuesrules": {
            "type": "number",
            "min": VALIDATION_WEIGHT_MIN,
            "max": VALIDATION_CONVERSATION_PARAM_MAX,
        },
    },
}


def create_default_weights_file() -> Path:
    """Create a default weights configuration file in ~/.gandalf/config.

    Returns:
        Path to the created default weights file
    """
    DEFAULT_WEIGHTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    default_config = apply_schema_defaults(WEIGHTS_SCHEMA, {})

    try:
        with open(DEFAULT_WEIGHTS_FILE, "w", encoding="utf-8") as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)
        log_info(f"Created default weights file: {DEFAULT_WEIGHTS_FILE}")
        return DEFAULT_WEIGHTS_FILE
    except (OSError, IOError, yaml.YAMLError) as e:
        log_error(e, f"Failed to create default weights file: {DEFAULT_WEIGHTS_FILE}")
        raise


def get_weights_file_path(spec_dir: Path = None) -> Path:
    """Get the appropriate weights file path based on validation.

    Args:
        spec_dir: Directory containing potential gandalf-weights.yaml
                 (optional, defaults to SPEC_WEIGHTS_FILE)

    Returns:
        Path to the weights file to use (override, spec, or default)
    """
    if WEIGHTS_FILE_OVERRIDE:
        override_path = Path(WEIGHTS_FILE_OVERRIDE)
        if override_path.exists():
            log_debug(f"Using weights file override: {override_path}")
            return override_path
        else:
            log_debug(
                "Weights file override specified but doesn't exist: " f"{override_path}"
            )

    if spec_dir is not None:
        spec_weights_file = spec_dir / "gandalf-weights.yaml"
    else:
        spec_weights_file = SPEC_WEIGHTS_FILE

    if spec_weights_file.exists():
        try:
            with open(spec_weights_file, "r", encoding="utf-8") as f:
                spec_config = yaml.safe_load(f) or {}

            is_valid, errors, _ = validate_weights_config(spec_config)

            if is_valid:
                log_debug(f"Using valid weights file from spec: {spec_weights_file}")
                return spec_weights_file
            else:
                log_info(
                    f"Spec weights file is invalid ({len(errors)} errors), "
                    "using default"
                )
                for error in errors:
                    log_error(None, f"Spec validation error: {error}")

        except (OSError, IOError, yaml.YAMLError) as e:
            log_error(e, f"Failed to read spec weights file: {spec_weights_file}")

    # Use default file, creating it if it doesn't exist
    if not DEFAULT_WEIGHTS_FILE.exists():
        create_default_weights_file()

    log_debug(f"Using default weights file: {DEFAULT_WEIGHTS_FILE}")
    return DEFAULT_WEIGHTS_FILE


def format_cerberus_errors(errors: Dict[str, Any]) -> List[str]:
    """Format Cerberus validation errors into readable strings.

    Args:
        errors: Cerberus validation errors dictionary

    Returns:
        List of formatted error messages
    """
    formatted_errors = []

    def format_error(path: str, error_info: Any) -> None:
        if isinstance(error_info, dict):
            for key, value in error_info.items():
                new_path = f"{path}.{key}" if path else key
                format_error(new_path, value)
        elif isinstance(error_info, list):
            for error in error_info:
                formatted_errors.append(f"{path}: {error}")
        else:
            formatted_errors.append(f"{path}: {error_info}")

    format_error("", errors)
    return formatted_errors


def apply_schema_defaults(
    schema: Dict[str, Any], data: Dict[str, Any]
) -> Dict[str, Any]:
    """Apply default values from schema to configuration data.

    Args:
        schema: Cerberus schema with default values
        data: Configuration data to apply defaults to

    Returns:
        Configuration data with defaults applied
    """

    def apply_defaults_recursive(
        schema_def: Dict[str, Any], config_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        result = config_data.copy()

        for key, schema_spec in schema_def.items():
            if isinstance(schema_spec, dict):
                if "default" in schema_spec:
                    if key not in result:
                        result[key] = schema_spec["default"]
                elif "schema" in schema_spec:
                    if key not in result:
                        result[key] = {}
                    result[key] = apply_defaults_recursive(
                        schema_spec["schema"], result[key]
                    )

        return result

    return apply_defaults_recursive(schema, data)


def validate_weights_config(
    config: Dict[str, Any],
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Validate weights configuration using Cerberus schema.

    Args:
        config: Configuration dictionary to validate

    Returns:
        Tuple of (is_valid, error_messages, normalized_config)
    """
    validator = Validator(WEIGHTS_SCHEMA)
    validator.allow_unknown = False

    # Validate the configuration
    if validator.validate(config):
        log_debug("Configuration validation passed")
        return True, [], validator.normalized(config)
    else:
        log_info("Configuration validation found errors")
        error_messages = format_cerberus_errors(validator.errors)

        for error in error_messages:
            log_error(None, f"Config validation error: {error}")

        # Return config with defaults applied as fallback
        return (
            False,
            error_messages,
            apply_schema_defaults(WEIGHTS_SCHEMA, config),
        )


def get_weights_schema() -> Dict[str, Any]:
    """Get the Cerberus schema for weights configuration.

    Returns:
        The weights configuration schema
    """
    return WEIGHTS_SCHEMA


def create_validator(schema: Dict[str, Any], allow_unknown: bool = False) -> Validator:
    """Create a Cerberus validator instance.

    Args:
        schema: Cerberus schema dictionary
        allow_unknown: Whether to allow unknown fields

    Returns:
        Validator instance
    """
    validator = Validator(schema)
    validator.allow_unknown = allow_unknown
    return validator
