"""
Configuration validation for Gandalf MCP server.
Validates gandalf-weights.yaml structure and values.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from src.config.constants.limits import (
    VALIDATION_DIRECTORY_MAX_VALUE,
    VALIDATION_DIRECTORY_MIN_VALUE,
    VALIDATION_FILE_EXT_MAX_VALUE,
    VALIDATION_FILE_EXT_MIN_VALUE,
)
from src.config.enums import Severity
from src.config.schemas import (
    VALIDATION_REQUIRED_CONTEXT,
    VALIDATION_REQUIRED_CONVERSATION,
    VALIDATION_REQUIRED_SECTIONS,
    VALIDATION_REQUIRED_WEIGHTS,
)


@dataclass
class ValidationError:
    """Represents a configuration validation error."""

    path: str
    message: str
    severity: Severity
    current_value: Any = None

    def __str__(self) -> str:
        """Format error message for display."""
        prefix = self.severity.value.upper()
        result = f"{prefix}: {self.message}"

        if self.path:
            result += f" (path: {self.path})"

        if self.current_value is not None:
            result += f" (current: {self.current_value})"

        return result


class WeightsValidator:
    """Validates gandalf-weights.yaml configuration."""

    def __init__(self):
        """Initialize the validator."""
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []

    def validate_config(self, config_path: Path) -> Tuple[bool, List[ValidationError]]:
        """Validate the entire configuration file."""
        self.errors = []
        self.warnings = []

        if not config_path.exists():
            self.errors.append(
                ValidationError(
                    path=str(config_path),
                    message="Configuration file not found",
                    severity=Severity.ERROR,
                )
            )
            return False, self.errors

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            self.errors.append(
                ValidationError(
                    path=str(config_path),
                    message=f"Invalid YAML syntax: {e}",
                    severity=Severity.ERROR,
                )
            )
            return False, self.errors
        except (OSError, IOError) as e:
            self.errors.append(
                ValidationError(
                    path=str(config_path),
                    message=f"Cannot read file: {e}",
                    severity=Severity.ERROR,
                )
            )
            return False, self.errors

        if not isinstance(config, dict):
            self.errors.append(
                ValidationError(
                    path=str(config_path),
                    message="Configuration must be a YAML dictionary",
                    severity=Severity.ERROR,
                    current_value=type(config).__name__,
                )
            )
            return False, self.errors

        # Run all validations
        self._validate_structure(config)
        self._validate_weights(config.get("weights", {}))
        self._validate_conversation(config.get("conversation", {}))
        self._validate_context(config.get("context", {}))
        self._validate_file_extensions(config.get("file_extensions", {}))
        self._validate_directories(config.get("directories", {}))
        self._validate_consistency(config)

        all_issues = self.errors + self.warnings
        is_valid = len(self.errors) == 0
        return is_valid, all_issues

    def _validate_structure(self, config: Dict[str, Any]) -> None:
        """Validate required sections exist."""
        for section, expected_type in VALIDATION_REQUIRED_SECTIONS.items():
            if section not in config:
                self.errors.append(
                    ValidationError(
                        path=section,
                        message=f"Required section '{section}' missing",
                        severity=Severity.ERROR,
                    )
                )
            elif not isinstance(config[section], expected_type):
                self.errors.append(
                    ValidationError(
                        path=section,
                        message=f"Section '{section}' must be "
                        f"{expected_type.__name__}",
                        severity=Severity.ERROR,
                        current_value=type(config[section]).__name__,
                    )
                )

    def _validate_weights(self, weights: Dict[str, Any]) -> None:
        """Validate weights section."""
        if not weights:
            return

        for key, (
            expected_type,
            min_val,
            max_val,
        ) in VALIDATION_REQUIRED_WEIGHTS.items():
            if key not in weights:
                self.warnings.append(
                    ValidationError(
                        path=f"weights.{key}",
                        message=f"Missing weight '{key}', using default",
                        severity=Severity.WARNING,
                    )
                )
            else:
                self._validate_numeric(
                    f"weights.{key}",
                    weights[key],
                    expected_type,
                    min_val,
                    max_val,
                )

    def _validate_conversation(self, conversation: Dict[str, Any]) -> None:
        """Validate conversation section."""
        if not conversation:
            return

        for key, (
            expected_type,
            min_val,
            max_val,
        ) in VALIDATION_REQUIRED_CONVERSATION.items():
            if key not in conversation:
                self.warnings.append(
                    ValidationError(
                        path=f"conversation.{key}",
                        message=f"Missing conversation parameter '{key}', "
                        "using default",
                        severity=Severity.WARNING,
                    )
                )
            else:
                self._validate_numeric(
                    f"conversation.{key}",
                    conversation[key],
                    expected_type,
                    min_val,
                    max_val,
                )

    def _validate_context(self, context: Dict[str, Any]) -> None:
        """Validate context section."""
        if not context:
            return

        for section_key, section_config in VALIDATION_REQUIRED_CONTEXT.items():
            if isinstance(section_config, dict):
                # Handle nested sections
                if section_key not in context:
                    self.warnings.append(
                        ValidationError(
                            path=f"context.{section_key}",
                            message=(
                                f"Missing context section '{section_key}', "
                                f"creating with defaults"
                            ),
                            severity=Severity.WARNING,
                        )
                    )
                    continue

                section_data = context[section_key]
                if not isinstance(section_data, dict):
                    self.errors.append(
                        ValidationError(
                            path=f"context.{section_key}",
                            message=f"Context section '{section_key}' must be "
                            "dictionary",
                            severity=Severity.ERROR,
                            current_value=type(section_data).__name__,
                        )
                    )
                    continue

                # Validate nested keys
                for key, (
                    expected_type,
                    min_val,
                    max_val,
                ) in section_config.items():
                    if key not in section_data:
                        self.warnings.append(
                            ValidationError(
                                path=f"context.{section_key}.{key}",
                                message=(
                                    f"Missing context parameter '{key}', "
                                    f"using default value"
                                ),
                                severity=Severity.WARNING,
                            )
                        )
                    else:
                        self._validate_numeric(
                            f"context.{section_key}.{key}",
                            section_data[key],
                            expected_type,
                            min_val,
                            max_val,
                        )
            else:
                # Handle direct values
                expected_type, min_val, max_val = section_config
                if section_key not in context:
                    self.warnings.append(
                        ValidationError(
                            path=f"context.{section_key}",
                            message=(
                                f"Missing context parameter '{section_key}', "
                                f"using default value"
                            ),
                            severity=Severity.WARNING,
                        )
                    )
                else:
                    self._validate_numeric(
                        f"context.{section_key}",
                        context[section_key],
                        expected_type,
                        min_val,
                        max_val,
                    )

    def _validate_file_extensions(self, file_extensions: Dict[str, Any]) -> None:
        """Validate file extensions section."""
        if not file_extensions:
            self.warnings.append(
                ValidationError(
                    path="file_extensions",
                    message="No file extensions defined, using defaults",
                    severity=Severity.WARNING,
                )
            )
            return

        for ext, weight in file_extensions.items():
            # Check for leading dots
            if isinstance(ext, str) and ext.startswith("."):
                self.warnings.append(
                    ValidationError(
                        path=f"file_extensions.{ext}",
                        message=f"File extension '{ext}' should not include "
                        "leading dot",
                        severity=Severity.WARNING,
                        current_value=ext,
                    )
                )

            self._validate_numeric(
                f"file_extensions.{ext}",
                weight,
                float,
                VALIDATION_FILE_EXT_MIN_VALUE,
                VALIDATION_FILE_EXT_MAX_VALUE,
            )

    def _validate_directories(self, directories: Dict[str, Any]) -> None:
        """Validate directories section."""
        if not directories:
            self.warnings.append(
                ValidationError(
                    path="directories",
                    message="No directories defined, using defaults",
                    severity=Severity.WARNING,
                )
            )
            return

        for dir_name, weight in directories.items():
            self._validate_numeric(
                f"directories.{dir_name}",
                weight,
                float,
                VALIDATION_DIRECTORY_MIN_VALUE,
                VALIDATION_DIRECTORY_MAX_VALUE,
            )

    def _validate_consistency(self, config: Dict[str, Any]) -> None:
        """Validate logical consistency between values."""
        context = config.get("context", {})
        file_size = context.get("file_size", {})

        # Check file size consistency
        if "optimal_min" in file_size and "optimal_max" in file_size:
            try:
                optimal_min = int(file_size["optimal_min"])
                optimal_max = int(file_size["optimal_max"])
                if optimal_min >= optimal_max:
                    self.errors.append(
                        ValidationError(
                            path="context.file_size",
                            message=("optimal_min must be less than optimal_max"),
                            severity=Severity.ERROR,
                            current_value=(f"min={optimal_min}, max={optimal_max}"),
                        )
                    )
            except (ValueError, TypeError):
                pass

        if "optimal_max" in file_size and "acceptable_max" in file_size:
            try:
                optimal_max = int(file_size["optimal_max"])
                acceptable_max = int(file_size["acceptable_max"])
                if optimal_max >= acceptable_max:
                    self.errors.append(
                        ValidationError(
                            path="context.file_size",
                            message=("optimal_max must be less than acceptable_max"),
                            severity=Severity.ERROR,
                            current_value=f"optimal={optimal_max}, "
                            f"acceptable={acceptable_max}",
                        )
                    )
            except (ValueError, TypeError):
                pass

    def _validate_numeric(
        self,
        path: str,
        value: Any,
        expected_type: type,
        min_val: float,
        max_val: float,
    ) -> None:
        """Validate a numeric value is within expected range."""
        if not isinstance(value, (int, float)):
            self.errors.append(
                ValidationError(
                    path=path,
                    message=f"Value must be {expected_type.__name__}",
                    severity=Severity.ERROR,
                    current_value=f"{type(value).__name__}: {value}",
                )
            )
            return

        try:
            numeric_value = expected_type(value)
        except (ValueError, TypeError):
            self.errors.append(
                ValidationError(
                    path=path,
                    message=f"Cannot convert to {expected_type.__name__}",
                    severity=Severity.ERROR,
                    current_value=value,
                )
            )
            return

        if numeric_value < min_val or numeric_value > max_val:
            self.errors.append(
                ValidationError(
                    path=path,
                    message=f"Value {numeric_value} outside valid range "
                    f"{min_val}-{max_val}",
                    severity=Severity.ERROR,
                    current_value=numeric_value,
                )
            )


def validate_weights_config(
    config_path: Path,
) -> Tuple[bool, List[ValidationError]]:
    """Validate a weights configuration file."""
    validator = WeightsValidator()
    return validator.validate_config(config_path)


def format_validation_report(errors: List[ValidationError]) -> str:
    """Format validation errors into a readable report."""
    if not errors:
        return "Configuration validation: PASSED"

    actual_errors = [e for e in errors if e.severity == Severity.ERROR]
    warnings = [e for e in errors if e.severity == Severity.WARNING]

    lines = [
        f"Configuration validation: {len(actual_errors)} errors, "
        f"{len(warnings)} warnings"
    ]

    if actual_errors:
        lines.append("\nERRORS:")
        for error in actual_errors:
            lines.append(f"  {error}")

    if warnings:
        lines.append("\nWARNINGS:")
        for warning in warnings:
            lines.append(f"  {warning}")

    if actual_errors:
        lines.append("\nResult: FAILED - Configuration has errors")
    else:
        lines.append("\nResult: PASSED - Configuration valid with warnings")

    return "\n".join(lines)
