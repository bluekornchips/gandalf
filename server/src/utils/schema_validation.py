"""
Schema validation utilities with custom validation implementation.
Provides reusable validation schemas and functions for configuration.
"""

from pathlib import Path
from typing import Any

import yaml

from src.config.conversation_config import CONTEXT_FILE_SIZE_OPTIMAL_MAX
from src.config.core_constants import (
    DEFAULT_ACTIVITY_BOOST,
    DEFAULT_DIRECTORIES,
    DEFAULT_FILE_EXTENSIONS,
    DEFAULT_FILE_REF_SCORE,
    DEFAULT_KEYWORD_WEIGHT,
    DEFAULT_MULTIPLIER_HIGH,
    DEFAULT_MULTIPLIER_LOW,
    DEFAULT_MULTIPLIER_MID,
    DEFAULT_OPTIMAL_FILE_SIZE_MIN,
    DEFAULT_TERMINATION_LIMIT_MULTIPLIER,
    DEFAULT_TERMINATION_MULTIPLIER,
    DEFAULT_TYPE_BONUSES,
    DEFAULT_WEIGHT_VALUE,
    DEFAULT_WEIGHTS_FILE,
    SPEC_WEIGHTS_FILE,
    VALIDATION_CONVERSATION_PARAM_MAX,
    VALIDATION_FILE_SIZE_MIN,
    VALIDATION_TIME_THRESHOLD_MAX_HOURS,
    VALIDATION_TIME_THRESHOLD_MIN,
    VALIDATION_WEIGHT_MIN,
    WEIGHTS_FILE_OVERRIDE,
)
from src.utils.common import log_debug, log_error, log_info


def _create_number_field(
    min_val: float = VALIDATION_WEIGHT_MIN,
    max_val: float = VALIDATION_CONVERSATION_PARAM_MAX,
    default_val: float = DEFAULT_WEIGHT_VALUE,
) -> dict[str, Any]:
    """Create a number field validation schema."""
    return {
        "type": "number",
        "min": min_val,
        "max": max_val,
        "default": default_val,
    }


def _create_integer_field(
    min_val: int = VALIDATION_FILE_SIZE_MIN,
    default_val: int = DEFAULT_OPTIMAL_FILE_SIZE_MIN,
) -> dict[str, Any]:
    """Create an integer field validation schema."""
    return {
        "type": "integer",
        "min": min_val,
        "default": default_val,
    }


def _create_dict_field(
    schema: dict[str, Any],
    required: bool = False,
    default_val: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a dictionary field validation schema."""
    field_def: dict[str, Any] = {
        "type": "dict",
        "schema": schema,
    }

    if required:
        field_def["required"] = True

    if default_val is not None:
        field_def["default"] = default_val

    return field_def


# Schema for weights configuration
WEIGHTS_SCHEMA = {
    "weights": _create_dict_field(
        schema={
            "recent_modification": _create_number_field(),
            "file_size_optimal": _create_number_field(),
            "file_type_priority": _create_number_field(),
            "directory_importance": _create_number_field(),
            "git_activity": _create_number_field(),
        },
        required=True,
    ),
    "conversation": _create_dict_field(
        schema={
            "keyword_match": _create_number_field(),
            "keyword_weight": _create_number_field(
                max_val=1, default_val=DEFAULT_KEYWORD_WEIGHT
            ),
            "recency": _create_number_field(),
            "file_reference": _create_number_field(),
            "file_reference_score": _create_number_field(
                max_val=1, default_val=DEFAULT_FILE_REF_SCORE
            ),
            "type_bonuses": {
                "type": "dict",
                "default": DEFAULT_TYPE_BONUSES,
                "valuesrules": _create_number_field(max_val=1),
            },
        },
        required=True,
    ),
    "recency_thresholds": _create_dict_field(
        schema={
            "days_1": _create_number_field(),
            "days_7": _create_number_field(default_val=DEFAULT_MULTIPLIER_HIGH),
            "days_30": _create_number_field(default_val=DEFAULT_MULTIPLIER_MID),
            "days_90": _create_number_field(default_val=DEFAULT_FILE_REF_SCORE),
            "default": _create_number_field(default_val=DEFAULT_KEYWORD_WEIGHT),
        },
        required=True,
    ),
    "context": _create_dict_field(
        schema={
            "file_size": _create_dict_field(
                schema={
                    "optimal_min": _create_integer_field(),
                    "optimal_max": _create_integer_field(
                        default_val=CONTEXT_FILE_SIZE_OPTIMAL_MAX
                    ),
                    "acceptable_multiplier": _create_number_field(
                        max_val=1, default_val=0.7
                    ),
                    "large_multiplier": _create_number_field(
                        max_val=1, default_val=DEFAULT_MULTIPLIER_LOW
                    ),
                },
            ),
            "recent_modifications": _create_dict_field(
                schema={
                    "hour_threshold": _create_integer_field(
                        min_val=VALIDATION_TIME_THRESHOLD_MIN, default_val=2
                    ),
                    "day_threshold": _create_integer_field(
                        min_val=VALIDATION_TIME_THRESHOLD_MIN, default_val=24
                    ),
                    "week_threshold": _create_integer_field(
                        min_val=VALIDATION_TIME_THRESHOLD_MIN,
                        default_val=VALIDATION_TIME_THRESHOLD_MAX_HOURS,
                    ),
                    "day_multiplier": _create_number_field(
                        max_val=1, default_val=DEFAULT_MULTIPLIER_HIGH
                    ),
                    "week_multiplier": _create_number_field(
                        max_val=1, default_val=DEFAULT_MULTIPLIER_MID
                    ),
                },
            ),
            "activity_score_recency_boost": _create_number_field(
                default_val=DEFAULT_ACTIVITY_BOOST
            ),
        },
        required=True,
    ),
    "processing": _create_dict_field(
        schema={
            "conversation_early_termination_multiplier": _create_number_field(
                default_val=DEFAULT_TERMINATION_MULTIPLIER
            ),
            "early_termination_limit_multiplier": _create_number_field(
                default_val=DEFAULT_TERMINATION_LIMIT_MULTIPLIER
            ),
        },
        required=True,
    ),
    "file_extensions": {
        "type": "dict",
        "default": DEFAULT_FILE_EXTENSIONS,
        "valuesrules": _create_number_field(),
    },
    "directories": {
        "type": "dict",
        "default": DEFAULT_DIRECTORIES,
        "valuesrules": _create_number_field(),
    },
}


class ValidationError:
    """Custom validation error class."""

    def __init__(self, path: str, message: str):
        self.path = path
        self.message = message

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


class GandalfSchemaValidator:
    """Gandalf schema validator for configuration validation."""

    def __init__(self, schema: dict[str, Any], allow_unknown: bool = False):
        self.schema = schema
        self.allow_unknown = allow_unknown
        self.errors: list[ValidationError] = []
        self.normalized_data: dict[str, Any] = {}

    def validate(self, data: dict[str, Any]) -> bool:
        """Validate data against schema."""
        self.errors = []
        self.normalized_data = {}

        try:
            self.normalized_data = self._validate_recursive(data, self.schema, "")
            return len(self.errors) == 0
        except (KeyError, TypeError, ValueError) as e:
            self.errors.append(ValidationError("", f"Validation error: {str(e)}"))
            return False

    def _validate_recursive(
        self, data: dict[str, Any], schema: dict[str, Any], path: str
    ) -> dict[str, Any]:
        """Recursively validate and normalize data."""
        result = {}

        # Check for required fields
        for key, field_schema in schema.items():
            current_path = f"{path}.{key}" if path else key

            if isinstance(field_schema, dict):
                if field_schema.get("required", False) and key not in data:
                    self.errors.append(ValidationError(current_path, "required field"))
                    continue

                # Apply defaults
                if key not in data and "default" in field_schema:
                    result[key] = field_schema["default"]
                elif key in data:
                    result[key] = self._validate_field(
                        data[key], field_schema, current_path
                    )
                elif "schema" in field_schema:
                    # Apply defaults for nested schemas
                    result[key] = self._validate_recursive(
                        {}, field_schema["schema"], current_path
                    )

        # Check for unknown fields
        if not self.allow_unknown:
            for key in data:
                if key not in schema:
                    self.errors.append(
                        ValidationError(
                            f"{path}.{key}" if path else key, "unknown field"
                        )
                    )

        return result

    def _validate_field(
        self, value: Any, field_schema: dict[str, Any], path: str
    ) -> Any:
        """Validate a single field."""
        # Type validation
        expected_type = field_schema.get("type")
        if expected_type == "number":
            if not isinstance(value, int | float):
                self.errors.append(
                    ValidationError(
                        path, f"must be a number, got {type(value).__name__}"
                    )
                )
                return value
        elif expected_type == "integer":
            if not isinstance(value, int):
                self.errors.append(
                    ValidationError(
                        path, f"must be an integer, got {type(value).__name__}"
                    )
                )
                return value
        elif expected_type == "dict":
            if not isinstance(value, dict):
                self.errors.append(
                    ValidationError(path, f"must be a dict, got {type(value).__name__}")
                )
                return value
        elif expected_type == "string":
            if not isinstance(value, str):
                self.errors.append(
                    ValidationError(
                        path, f"must be a string, got {type(value).__name__}"
                    )
                )
                return value

        # Range validation for numbers
        if expected_type in ["number", "integer"] and isinstance(value, int | float):
            if "min" in field_schema and value < field_schema["min"]:
                self.errors.append(
                    ValidationError(
                        path, f"must be >= {field_schema['min']}, got {value}"
                    )
                )
            if "max" in field_schema and value > field_schema["max"]:
                self.errors.append(
                    ValidationError(
                        path, f"must be <= {field_schema['max']}, got {value}"
                    )
                )

        # Dict validation
        if expected_type == "dict" and isinstance(value, dict):
            if "schema" in field_schema:
                return self._validate_recursive(value, field_schema["schema"], path)
            elif "valuesrules" in field_schema:
                # Validate all values in the dict
                result = {}
                for k, v in value.items():
                    result[k] = self._validate_field(
                        v, field_schema["valuesrules"], f"{path}.{k}"
                    )
                return result

        return value

    def normalized(self, data: dict[str, Any]) -> dict[str, Any]:
        """Return normalized data with defaults applied."""
        return self.normalized_data if self.normalized_data else data


def create_default_weights_file() -> Path:
    """Create a default weights configuration file in ~/.gandalf/config."""
    DEFAULT_WEIGHTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    default_config = apply_schema_defaults(WEIGHTS_SCHEMA, {})

    try:
        with open(DEFAULT_WEIGHTS_FILE, "w", encoding="utf-8") as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)
        log_info(f"Created default weights file: {DEFAULT_WEIGHTS_FILE}")
        return DEFAULT_WEIGHTS_FILE
    except (OSError, yaml.YAMLError) as e:
        log_error(e, f"Failed to create default weights file: {DEFAULT_WEIGHTS_FILE}")
        raise


def get_weights_file_path(spec_dir: Path | None = None) -> Path:
    """Get the appropriate weights file path based on validation."""
    if WEIGHTS_FILE_OVERRIDE:
        override_path = Path(WEIGHTS_FILE_OVERRIDE)
        if override_path.exists():
            log_debug(f"Using weights file override: {override_path}")
            return override_path
        else:
            log_debug(
                f"Weights file override specified but doesn't exist: {override_path}"
            )

    if spec_dir is not None:
        spec_weights_file = spec_dir / "gandalf-weights.yaml"
    else:
        spec_weights_file = SPEC_WEIGHTS_FILE

    if spec_weights_file.exists():
        try:
            with open(spec_weights_file, encoding="utf-8") as f:
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
                    log_info(f"Spec validation error: {error}")

        except (OSError, yaml.YAMLError) as e:
            log_error(e, f"Failed to read spec weights file: {spec_weights_file}")

    # Use default file, creating it if it doesn't exist
    if not DEFAULT_WEIGHTS_FILE.exists():
        create_default_weights_file()

    log_debug(f"Using default weights file: {DEFAULT_WEIGHTS_FILE}")
    return DEFAULT_WEIGHTS_FILE


def format_validation_errors(errors: list[ValidationError]) -> list[str]:
    """Format validation errors into readable strings."""
    return [str(error) for error in errors]


def apply_schema_defaults(
    schema: dict[str, Any], data: dict[str, Any]
) -> dict[str, Any]:
    """Apply default values from schema to configuration data."""

    def apply_defaults_recursive(
        schema_def: dict[str, Any], config_data: dict[str, Any]
    ) -> dict[str, Any]:
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
    config: dict[str, Any],
) -> tuple[bool, list[str], dict[str, Any]]:
    """Validate weights configuration using custom schema validation."""
    validator = GandalfSchemaValidator(WEIGHTS_SCHEMA, allow_unknown=False)

    # Validate the configuration
    if validator.validate(config):
        log_debug("Configuration validation passed")
        return True, [], validator.normalized(config)
    else:
        log_info("Configuration validation found errors")
        error_messages = format_validation_errors(validator.errors)

        for error in error_messages:
            log_info(f"Config validation error: {error}")

        # Return config with defaults applied as fallback
        return (
            False,
            error_messages,
            apply_schema_defaults(WEIGHTS_SCHEMA, config),
        )


def get_weights_schema() -> dict[str, Any]:
    """Get the schema for weights configuration."""
    return WEIGHTS_SCHEMA


def create_validator(
    schema: dict[str, Any], allow_unknown: bool = False
) -> GandalfSchemaValidator:
    """Create a Gandalf schema validator instance."""
    return GandalfSchemaValidator(schema, allow_unknown=allow_unknown)
