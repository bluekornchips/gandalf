"""Tests for configuration validation."""

import tempfile
from pathlib import Path

import yaml

from src.config.enums import Severity
from src.config.schemas import (
    VALIDATION_REQUIRED_CONVERSATION,
    VALIDATION_REQUIRED_WEIGHTS,
)
from src.config.validation import (
    ValidationError,
    WeightsValidator,
    format_validation_report,
    validate_weights_config,
)


class TestValidationError:
    """Test ValidationError dataclass."""

    def test_validation_error_str_format(self):
        """Test that ValidationError formats correctly."""
        error = ValidationError(
            path="weights.recent_modification",
            message="Value is out of range",
            severity=Severity.ERROR,
            current_value=150.0,
        )

        result = str(error)
        assert "ERROR: Value is out of range" in result
        assert "(path: weights.recent_modification)" in result
        assert "(current: 150.0)" in result

    def test_validation_warning_str_format(self):
        """Test that ValidationError formats warnings correctly."""
        warning = ValidationError(
            path="file_extensions",
            message="No file extensions defined",
            severity=Severity.WARNING,
        )

        result = str(warning)
        assert "WARNING: No file extensions defined" in result
        assert "(path: file_extensions)" in result


class TestWeightsValidator:
    """Test WeightsValidator class."""

    def test_valid_configuration(self):
        """Test that valid configuration passes validation."""
        validator = WeightsValidator()

        # Create a valid configuration
        config = {
            "enabled": True,
            "weights": {
                "recent_modification": 5.0,
                "file_size_optimal": 2.0,
                "import_relationship": 4.0,
                "conversation_mention": 3.0,
                "git_activity": 3.5,
                "file_type_priority": 1.5,
                "directory_importance": 1.0,
            },
            "conversation": {
                "keyword_match": 3.0,
                "file_reference": 4.0,
                "recency": 2.0,
                "technical_content": 1.5,
                "problem_solving": 2.5,
                "architecture": 3.0,
                "debugging": 2.5,
                "keyword_weight": 0.3,
                "file_ref_score": 0.5,
            },
            "context": {
                "file_size": {
                    "optimal_min": 100,
                    "optimal_max": 50000,
                    "acceptable_max": 512000,
                    "acceptable_multiplier": 0.8,
                    "large_multiplier": 0.5,
                },
                "recent_modifications": {
                    "hour_threshold": 1,
                    "day_threshold": 24,
                    "week_threshold": 168,
                    "day_multiplier": 0.8,
                    "week_multiplier": 0.6,
                },
                "activity_score_recency_boost": 1.3,
            },
            "file_extensions": {
                "py": 4.0,
                "js": 3.8,
                "ts": 3.8,
            },
            "directories": {
                "src": 4.0,
                "lib": 3.8,
                "tests": 2.3,
            },
        }

        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            temp_path = Path(f.name)

        try:
            is_valid, errors = validator.validate_config(temp_path)
            assert is_valid
            assert len([e for e in errors if e.severity == Severity.ERROR]) == 0
        finally:
            temp_path.unlink()

    def test_missing_required_sections(self):
        """Test detection of missing required sections."""
        validator = WeightsValidator()

        # Create configuration missing required sections
        config = {
            "enabled": True,
            # Missing weights, conversation, context, etc.
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            temp_path = Path(f.name)

        try:
            is_valid, errors = validator.validate_config(temp_path)
            assert not is_valid

            error_messages = [e.message for e in errors if e.severity == Severity.ERROR]
            assert any(
                "Required section 'weights' missing" in msg for msg in error_messages
            )
            assert any(
                "Required section 'conversation' missing" in msg
                for msg in error_messages
            )
            assert any(
                "Required section 'context' missing" in msg for msg in error_messages
            )
        finally:
            temp_path.unlink()

    def test_invalid_numeric_ranges(self):
        """Test detection of out-of-range numeric values."""
        validator = WeightsValidator()

        config = {
            "enabled": True,
            "weights": {
                "recent_modification": 150.0,  # Too high
                "file_size_optimal": -5.0,  # Too low
                "import_relationship": "not_a_number",  # Wrong type
            },
            "conversation": {},
            "context": {},
            "file_extensions": {},
            "directories": {},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            temp_path = Path(f.name)

        try:
            is_valid, errors = validator.validate_config(temp_path)
            assert not is_valid

            error_messages = [e.message for e in errors if e.severity == Severity.ERROR]
            assert any(
                "Value 150.0 outside valid range" in msg for msg in error_messages
            )
            assert any(
                "Value -5.0 outside valid range" in msg for msg in error_messages
            )
            assert any("Value must be float" in msg for msg in error_messages)
        finally:
            temp_path.unlink()

    def test_logical_consistency_errors(self):
        """Test detection of logical inconsistencies."""
        validator = WeightsValidator()

        config = {
            "enabled": True,
            "weights": {},
            "conversation": {},
            "context": {
                "file_size": {
                    "optimal_min": 100000,  # Greater than optimal_max
                    "optimal_max": 50000,
                    "acceptable_max": 30000,  # Less than optimal_max
                },
            },
            "file_extensions": {},
            "directories": {},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            temp_path = Path(f.name)

        try:
            is_valid, errors = validator.validate_config(temp_path)
            assert not is_valid

            error_messages = [e.message for e in errors if e.severity == Severity.ERROR]
            assert any(
                "optimal_min must be less than optimal_max" in msg
                for msg in error_messages
            )
            assert any(
                "optimal_max must be less than acceptable_max" in msg
                for msg in error_messages
            )
        finally:
            temp_path.unlink()

    def test_file_extension_validation(self):
        """Test file extension validation."""
        validator = WeightsValidator()

        config = {
            "enabled": True,
            "weights": {},
            "conversation": {},
            "context": {},
            "file_extensions": {
                ".py": 4.0,  # Should warn about leading dot
                "js": 150.0,  # Out of range
            },
            "directories": {},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            temp_path = Path(f.name)

        try:
            is_valid, errors = validator.validate_config(temp_path)
            assert not is_valid

            # Check for warnings about leading dot
            warning_messages = [
                e.message for e in errors if e.severity == Severity.WARNING
            ]
            assert any(
                "should not include leading dot" in msg for msg in warning_messages
            )

            # Check for errors
            error_messages = [e.message for e in errors if e.severity == Severity.ERROR]
            assert any(
                "Value 150.0 outside valid range" in msg for msg in error_messages
            )
        finally:
            temp_path.unlink()

    def test_nonexistent_file(self):
        """Test handling of nonexistent configuration file."""
        validator = WeightsValidator()

        nonexistent_path = Path("/nonexistent/config.yaml")
        is_valid, errors = validator.validate_config(nonexistent_path)

        assert not is_valid
        assert len(errors) == 1
        assert errors[0].severity == Severity.ERROR
        assert "Configuration file not found" in errors[0].message

    def test_invalid_yaml_syntax(self):
        """Test handling of invalid YAML syntax."""
        validator = WeightsValidator()

        # Create file with invalid YAML
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: syntax: [unclosed")
            temp_path = Path(f.name)

        try:
            is_valid, errors = validator.validate_config(temp_path)
            assert not is_valid
            assert len(errors) == 1
            assert errors[0].severity == Severity.ERROR
            assert "Invalid YAML syntax" in errors[0].message
        finally:
            temp_path.unlink()

    def test_non_dict_config(self):
        """Test handling of non-dictionary configuration."""
        validator = WeightsValidator()

        # Create file with list instead of dict
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(["not", "a", "dict"], f)
            temp_path = Path(f.name)

        try:
            is_valid, errors = validator.validate_config(temp_path)
            assert not is_valid
            assert len(errors) == 1
            assert errors[0].severity == Severity.ERROR
            assert "Configuration must be a YAML dictionary" in errors[0].message
        finally:
            temp_path.unlink()


class TestValidationFunctions:
    """Test standalone validation functions."""

    def test_validate_weights_config_function(self):
        """Test the validate_weights_config function."""
        # Create a minimal valid configuration
        config = {
            "enabled": True,
            "weights": {"recent_modification": 5.0},
            "conversation": {"keyword_match": 3.0},
            "context": {"activity_score_recency_boost": 1.0},
            "file_extensions": {"py": 4.0},
            "directories": {"src": 3.0},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            temp_path = Path(f.name)

        try:
            is_valid, errors = validate_weights_config(temp_path)
            # Should be valid but have warnings for missing keys
            assert is_valid
            warning_count = len([e for e in errors if e.severity == Severity.WARNING])
            assert warning_count > 0  # Should have warnings for missing keys
        finally:
            temp_path.unlink()

    def test_format_validation_report_no_errors(self):
        """Test formatting when there are no errors."""
        result = format_validation_report([])
        assert result == "Configuration validation: PASSED"

    def test_format_validation_report_with_errors(self):
        """Test formatting with errors and warnings."""
        errors = [
            ValidationError(
                path="weights.test",
                message="Test error",
                severity=Severity.ERROR,
            ),
            ValidationError(
                path="conversation.test",
                message="Test warning",
                severity=Severity.WARNING,
            ),
        ]

        result = format_validation_report(errors)
        assert "Configuration validation: 1 errors, 1 warnings" in result
        assert "ERRORS:" in result
        assert "WARNINGS:" in result
        assert "Result: FAILED - Configuration has errors" in result

    def test_format_validation_report_warnings_only(self):
        """Test formatting with only warnings."""
        warnings = [
            ValidationError(
                path="file_extensions",
                message="No extensions defined",
                severity=Severity.WARNING,
            )
        ]

        result = format_validation_report(warnings)
        assert "Configuration validation: 0 errors, 1 warnings" in result
        assert "WARNINGS:" in result
        assert "Result: PASSED - Configuration valid with warnings" in result


class TestIntegrationScenarios:
    """Test real-world configuration scenarios using LOTR references."""

    def test_sauron_weights_extreme_values(self):
        """Test that extreme values are properly detected."""
        # Simulate Sauron's extreme weights (all 10.0)
        config = {
            "enabled": True,
            "weights": {key: 10.0 for key in VALIDATION_REQUIRED_WEIGHTS.keys()},
            "conversation": {
                key: 10.0 for key in VALIDATION_REQUIRED_CONVERSATION.keys()
            },
            "context": {
                "file_size": {
                    "optimal_min": 100,
                    "optimal_max": 50000,
                    "acceptable_max": 512000,
                    "acceptable_multiplier": 10.0,
                    "large_multiplier": 10.0,
                },
                "recent_modifications": {
                    "hour_threshold": 1,
                    "day_threshold": 24,
                    "week_threshold": 168,
                    "day_multiplier": 10.0,
                    "week_multiplier": 10.0,
                },
                "activity_score_recency_boost": 10.0,
            },
            "file_extensions": {"py": 10.0, "js": 10.0},
            "directories": {"src": 10.0, "lib": 10.0},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            temp_path = Path(f.name)

        try:
            is_valid, errors = validate_weights_config(temp_path)
            # Should be valid as all values are within acceptable ranges
            assert is_valid

            # But should have warnings for extreme values if implemented
            # Note: Current implementation doesn't warn about extreme values,
            # but configuration is technically valid
        finally:
            temp_path.unlink()

    def test_shire_weights_minimal_values(self):
        """Test that minimal values are properly handled."""
        # Simulate Shire's minimal weights (all 0.1)
        config = {
            "enabled": True,
            "weights": {key: 0.1 for key in VALIDATION_REQUIRED_WEIGHTS.keys()},
            "conversation": {
                key: 0.1 for key in VALIDATION_REQUIRED_CONVERSATION.keys()
            },
            "context": {
                "file_size": {
                    "optimal_min": 100,
                    "optimal_max": 50000,
                    "acceptable_max": 512000,
                    "acceptable_multiplier": 0.1,
                    "large_multiplier": 0.1,
                },
                "recent_modifications": {
                    "hour_threshold": 1,
                    "day_threshold": 24,
                    "week_threshold": 168,
                    "day_multiplier": 0.1,
                    "week_multiplier": 0.1,
                },
                "activity_score_recency_boost": 0.1,
            },
            "file_extensions": {"py": 0.1, "js": 0.1},
            "directories": {"src": 0.1, "lib": 0.1},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            temp_path = Path(f.name)

        try:
            is_valid, errors = validate_weights_config(temp_path)
            # Should be valid as all values are within acceptable ranges
            assert is_valid

            # Should have minimal warnings since all required keys are present
            error_count = len([e for e in errors if e.severity == Severity.ERROR])
            assert error_count == 0
        finally:
            temp_path.unlink()
