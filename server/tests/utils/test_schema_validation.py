"""
Tests for schema validation utilities.

lotr-info: Tests the schema validation system using configuration files
modeled after the different regions of Middle-earth.
"""

import pytest

from src.config.constants.schema_defaults import (
    DEFAULT_DIRECTORIES,
    DEFAULT_FILE_EXTENSIONS,
    DEFAULT_FILE_REF_SCORE,
    DEFAULT_KEYWORD_WEIGHT,
    DEFAULT_MULTIPLIER_HIGH,
    DEFAULT_MULTIPLIER_MID,
    DEFAULT_TYPE_BONUSES,
    DEFAULT_WEIGHT_VALUE,
)
from src.utils.schema_validation import (
    WEIGHTS_SCHEMA,
    ValidationError,
    apply_schema_defaults,
    create_default_weights_file,
    create_validator,
    format_validation_errors,
    get_weights_file_path,
    get_weights_schema,
    validate_weights_config,
    _create_number_field,
    _create_integer_field,
    _create_dict_field,
)


class TestSchemaValidationUtilities:
    """Test schema validation utility functions."""

    def test_get_weights_schema(self):
        """Test schema retrieval."""
        schema = get_weights_schema()
        assert isinstance(schema, dict)
        assert "weights" in schema
        assert "conversation" in schema
        assert "context" in schema
        assert schema == WEIGHTS_SCHEMA

    def test_format_validation_errors(self):
        """Test error formatting function."""
        errors = [
            ValidationError("field1", "error message 1"),
            ValidationError("field2.subfield", "error message 2"),
        ]

        formatted = format_validation_errors(errors)
        assert isinstance(formatted, list)
        assert len(formatted) == 2
        assert "field1: error message 1" in formatted
        assert "field2.subfield: error message 2" in formatted

    def test_apply_schema_defaults(self):
        """Test default value application."""
        test_schema = {
            "field1": {"type": "string", "default": "default_value"},
            "field2": {
                "type": "dict",
                "schema": {"subfield": {"type": "number", "default": 42}},
            },
        }

        # Test with empty data
        result = apply_schema_defaults(test_schema, {})
        assert result["field1"] == "default_value"
        assert result["field2"]["subfield"] == 42

        # Test with partial data
        result = apply_schema_defaults(test_schema, {"field1": "custom_value"})
        assert result["field1"] == "custom_value"
        assert result["field2"]["subfield"] == 42

    def test_validate_weights_config_valid(self):
        """Test validation with valid config."""
        valid_config = {
            "weights": {"recent_modification": 1.0},
            "conversation": {"keyword_weight": 0.1},
            "recency_thresholds": {"days_1": 1.0},
            "context": {"file_size": {"optimal_min": 100}},
            "processing": {"conversation_early_termination_multiplier": 0.8},
        }

        is_valid, errors, normalized_config = validate_weights_config(valid_config)
        assert is_valid is True
        assert len(errors) == 0
        assert isinstance(normalized_config, dict)
        assert "weights" in normalized_config

    def test_validate_weights_config_invalid(self):
        """Test validation with invalid config."""
        invalid_config = {
            "weights": {"recent_modification": 1.0},
            "conversation": {"keyword_weight": 2.0},  # Max is 1.0
            "recency_thresholds": {"days_1": 1.0},
            "context": {"file_size": {"optimal_min": 100}},
            "processing": {"conversation_early_termination_multiplier": 0.8},
        }

        is_valid, errors, normalized_config = validate_weights_config(invalid_config)
        assert is_valid is False
        assert len(errors) > 0
        assert any("keyword_weight" in error for error in errors)

    def test_validate_weights_config_empty(self):
        """Test validation with empty config applies defaults."""
        is_valid, errors, normalized_config = validate_weights_config({})

        # Should be invalid due to missing required fields
        assert is_valid is False
        assert len(errors) > 0

        # But should still have defaults applied
        assert isinstance(normalized_config, dict)
        assert normalized_config.get("conversation", {}).get("keyword_weight") == 0.1

    def test_create_validator(self):
        """Test validator creation."""
        schema = {"field": {"type": "string"}}
        validator = create_validator(schema)

        assert validator is not None
        assert validator.validate({"field": "test"}) is True
        assert validator.validate({"field": 123}) is False

    def test_create_validator_allow_unknown(self):
        """Test validator creation with allow_unknown."""
        schema = {"field": {"type": "string"}}
        validator = create_validator(schema, allow_unknown=True)

        assert validator is not None
        assert validator.validate({"field": "test", "unknown": "value"}) is True

    def test_create_default_weights_file_functionality(self):
        """Test that create_default_weights_file can be called."""
        # Just test that the function exists and can be imported
        # The actual file creation is tested in integration tests
        assert callable(create_default_weights_file)

    def test_get_weights_file_path_functionality(self):
        """Test that get_weights_file_path can be called."""
        # Just test that the function exists and can be imported
        # The actual path resolution is tested in integration tests
        assert callable(get_weights_file_path)


class TestWeightsSchemaStructure:
    """Test the structure and content of the weights schema."""

    def test_schema_has_required_sections(self):
        """Test that schema has all required sections."""
        schema = get_weights_schema()

        required_sections = [
            "weights",
            "conversation",
            "recency_thresholds",
            "context",
            "processing",
            "file_extensions",
            "directories",
        ]

        for section in required_sections:
            assert section in schema, f"Missing required section: {section}"

    def test_schema_default_values(self):
        """Test that schema has appropriate default values."""
        schema = get_weights_schema()

        # Check some key default values
        assert schema["conversation"]["schema"]["keyword_weight"]["default"] == 0.1
        assert schema["file_extensions"]["default"]["py"] == 1.0
        assert schema["directories"]["default"]["src"] == 1.0

    def test_schema_validation_rules(self):
        """Test that schema has proper validation rules."""
        schema = get_weights_schema()

        # Check that numeric fields have min/max constraints
        keyword_weight = schema["conversation"]["schema"]["keyword_weight"]
        assert keyword_weight["min"] == 0.0  # VALIDATION_WEIGHT_MIN
        assert keyword_weight["max"] == 1

        # Check that file extensions have proper value rules
        file_extensions = schema["file_extensions"]
        assert "valuesrules" in file_extensions
        assert file_extensions["valuesrules"]["type"] == "number"

    def test_schema_uses_constants(self):
        """Test that schema uses constants from constants.py."""
        schema = get_weights_schema()

        # Check that validation ranges use constants
        weights_section = schema["weights"]["schema"]
        assert (
            weights_section["recent_modification"]["min"] == 0.0
        )  # VALIDATION_WEIGHT_MIN
        assert (
            weights_section["recent_modification"]["max"] == 10.0
        )  # VALIDATION_CONVERSATION_PARAM_MAX

        # Check file size uses constants
        context_section = schema["context"]["schema"]
        assert (
            context_section["file_size"]["schema"]["optimal_max"]["default"] == 1000000
        )  # CONTEXT_FILE_SIZE_OPTIMAL_MAX


class TestSchemaConstants:
    """Test the constants defined in schema validation."""

    def test_default_constants_exist(self):
        """Test that all default constants are properly defined."""
        assert DEFAULT_KEYWORD_WEIGHT == 0.1
        assert DEFAULT_FILE_REF_SCORE == 0.2
        assert DEFAULT_MULTIPLIER_HIGH == 0.8
        assert DEFAULT_MULTIPLIER_MID == 0.5
        assert DEFAULT_WEIGHT_VALUE == 1.0

    def test_type_bonuses_structure(self):
        """Test conversation type bonuses structure."""
        assert isinstance(DEFAULT_TYPE_BONUSES, dict)
        assert "debugging" in DEFAULT_TYPE_BONUSES
        assert "architecture" in DEFAULT_TYPE_BONUSES
        assert "testing" in DEFAULT_TYPE_BONUSES
        assert DEFAULT_TYPE_BONUSES["debugging"] == 0.25

    def test_file_extensions_structure(self):
        """Test file extensions structure."""
        assert isinstance(DEFAULT_FILE_EXTENSIONS, dict)
        assert "py" in DEFAULT_FILE_EXTENSIONS
        assert "js" in DEFAULT_FILE_EXTENSIONS
        assert DEFAULT_FILE_EXTENSIONS["py"] == 1.0

    def test_directories_structure(self):
        """Test directories structure."""
        assert isinstance(DEFAULT_DIRECTORIES, dict)
        assert "src" in DEFAULT_DIRECTORIES
        assert "tests" in DEFAULT_DIRECTORIES
        assert DEFAULT_DIRECTORIES["src"] == 1.0


class TestSchemaHelperFunctions:
    """Test helper functions for schema creation."""

    def test_create_number_field_defaults(self):
        """Test number field creation with defaults."""
        field = _create_number_field()
        assert field["type"] == "number"
        assert field["min"] == 0.0
        assert field["max"] == 10.0
        assert field["default"] == 1.0

    def test_create_number_field_custom(self):
        """Test number field creation with custom values."""
        field = _create_number_field(min_val=0.5, max_val=5.0, default_val=2.0)
        assert field["min"] == 0.5
        assert field["max"] == 5.0
        assert field["default"] == 2.0

    def test_create_integer_field_defaults(self):
        """Test integer field creation with defaults."""
        field = _create_integer_field()
        assert field["type"] == "integer"
        assert field["min"] == 1  # VALIDATION_FILE_SIZE_MIN
        assert field["default"] == 100

    def test_create_integer_field_custom(self):
        """Test integer field creation with custom values."""
        field = _create_integer_field(min_val=10, default_val=50)
        assert field["min"] == 10
        assert field["default"] == 50

    def test_create_dict_field_basic(self):
        """Test dict field creation with basic schema."""
        schema = {"field": {"type": "string"}}
        field = _create_dict_field(schema)
        assert field["type"] == "dict"
        assert field["schema"] == schema
        assert "required" not in field
        assert "default" not in field

    def test_create_dict_field_required(self):
        """Test dict field creation with required flag."""
        schema = {"field": {"type": "string"}}
        field = _create_dict_field(schema, required=True)
        assert field["required"] is True

    def test_create_dict_field_with_default(self):
        """Test dict field creation with default value."""
        schema = {"field": {"type": "string"}}
        default_val = {"field": "default"}
        field = _create_dict_field(schema, default_val=default_val)
        assert field["default"] == default_val


class TestMiddleEarthConfigurations:
    """Test configurations using Middle-earth themed data."""

    def test_hobbiton_configuration(self):
        """Test a peaceful, well-balanced configuration like Hobbiton."""
        hobbiton_config = {
            "weights": {
                "recent_modification": 1.0,
                "file_size_optimal": 1.0,
                "file_type_priority": 1.0,
                "directory_importance": 1.0,
                "git_activity": 1.0,
            },
            "conversation": {
                "keyword_match": 1.0,
                "keyword_weight": 0.1,
                "recency": 1.0,
                "file_reference": 1.0,
                "file_reference_score": 0.2,
            },
            "recency_thresholds": {
                "days_1": 1.0,
                "days_7": 0.8,
                "days_30": 0.5,
                "days_90": 0.2,
                "default": 0.1,
            },
            "context": {
                "file_size": {
                    "optimal_min": 100,
                    "optimal_max": 1000,
                    "acceptable_multiplier": 0.7,
                    "large_multiplier": 0.3,
                },
                "recent_modifications": {
                    "hour_threshold": 2,
                    "day_threshold": 24,
                    "week_threshold": 168,
                    "day_multiplier": 0.8,
                    "week_multiplier": 0.5,
                },
                "activity_score_recency_boost": 1.5,
            },
            "processing": {
                "conversation_early_termination_multiplier": 0.8,
                "early_termination_limit_multiplier": 1.5,
            },
        }

        is_valid, errors, normalized = validate_weights_config(hobbiton_config)
        assert is_valid is True
        assert len(errors) == 0
        assert normalized["weights"]["recent_modification"] == 1.0

    def test_rivendell_configuration(self):
        """Test a wisdom-focused configuration like Rivendell."""
        rivendell_config = {
            "weights": {
                "recent_modification": 0.8,
                "file_size_optimal": 1.2,
                "file_type_priority": 1.5,
                "directory_importance": 1.0,
                "git_activity": 0.9,
            },
            "conversation": {
                "keyword_match": 1.2,
                "keyword_weight": 0.15,
                "recency": 0.8,
                "file_reference": 1.3,
                "file_reference_score": 0.25,
                "type_bonuses": {
                    "debugging": 0.3,
                    "architecture": 0.4,  # Emphasize architecture in Rivendell
                    "testing": 0.2,
                    "code_discussion": 0.15,
                    "problem_solving": 0.2,
                    "general": 0.05,
                },
            },
            "recency_thresholds": {
                "days_1": 0.9,
                "days_7": 0.7,
                "days_30": 0.4,
                "days_90": 0.15,
                "default": 0.08,
            },
            "context": {
                "file_size": {
                    "optimal_min": 150,
                    "optimal_max": 2000,
                    "acceptable_multiplier": 0.75,
                    "large_multiplier": 0.35,
                },
                "activity_score_recency_boost": 1.2,
            },
            "processing": {
                "conversation_early_termination_multiplier": 0.7,
                "early_termination_limit_multiplier": 1.3,
            },
        }

        is_valid, errors, normalized = validate_weights_config(rivendell_config)
        assert is_valid is True
        assert len(errors) == 0
        assert normalized["conversation"]["type_bonuses"]["architecture"] == 0.4

    def test_moria_configuration_invalid(self):
        """Test an invalid configuration like the abandoned Moria."""
        moria_config = {
            "weights": {
                "recent_modification": -0.5,  # Invalid: negative
                "file_size_optimal": 15.0,  # Invalid: too high
                "file_type_priority": 1.0,
                "directory_importance": 1.0,
                "git_activity": 1.0,
            },
            "conversation": {
                "keyword_match": 1.0,
                "keyword_weight": 2.0,  # Invalid: max is 1.0
                "recency": 1.0,
                "file_reference": 1.0,
                "file_reference_score": 0.2,
            },
            "recency_thresholds": {
                "days_1": 1.0,
                "days_7": 0.8,
                "days_30": 0.5,
                "days_90": 0.2,
                "default": 0.1,
            },
            "context": {
                "file_size": {
                    "optimal_min": -100,  # Invalid: negative
                    "optimal_max": 1000,
                    "acceptable_multiplier": 0.7,
                    "large_multiplier": 0.3,
                },
                "activity_score_recency_boost": 1.5,
            },
            "processing": {
                "conversation_early_termination_multiplier": 0.8,
                "early_termination_limit_multiplier": 1.5,
            },
        }

        is_valid, errors, normalized = validate_weights_config(moria_config)
        assert is_valid is False
        assert len(errors) > 0

        # Check specific error messages
        error_messages = [str(err) for err in errors]
        assert any("recent_modification" in err for err in error_messages)
        assert any("keyword_weight" in err for err in error_messages)
        assert any("optimal_min" in err for err in error_messages)

    def test_shire_minimal_configuration(self):
        """Test a minimal configuration like the simple Shire."""
        shire_config = {
            "weights": {"recent_modification": 1.0},
            "conversation": {"keyword_weight": 0.1},
            "recency_thresholds": {"days_1": 1.0},
            "context": {"file_size": {"optimal_min": 100}},
            "processing": {"conversation_early_termination_multiplier": 0.8},
        }

        is_valid, errors, normalized = validate_weights_config(shire_config)
        assert is_valid is True
        assert len(errors) == 0

        # Check that defaults are applied
        assert normalized["weights"]["file_size_optimal"] == 1.0
        assert normalized["conversation"]["keyword_match"] == 1.0
        assert normalized["recency_thresholds"]["days_7"] == 0.8


class TestGandalfSchemaValidatorErrorHandling:
    """Test error handling and edge cases for GandalfSchemaValidator."""

    def test_validate_with_invalid_schema_structure(self):
        """Test validator with schema that causes internal errors."""
        from src.utils.schema_validation import GandalfSchemaValidator
        from unittest.mock import Mock

        # Create a normal schema
        schema = {
            "test_field": {"type": "dict", "schema": {"sub_field": {"type": "string"}}}
        }

        validator = GandalfSchemaValidator(schema)

        # Mock _validate_recursive to raise an exception
        original_method = validator._validate_recursive

        def mock_validate_recursive(*args, **kwargs):
            raise ValueError("Test exception for coverage")

        validator._validate_recursive = mock_validate_recursive

        # Test with data that triggers exception handling
        result = validator.validate({"test_field": {"sub_field": "test"}})

        # Should handle the exception and return False
        assert result is False
        assert len(validator.errors) > 0
        assert "Validation error: Test exception for coverage" in str(
            validator.errors[0]
        )

    def test_validate_field_type_validation_errors(self):
        """Test type validation error paths in _validate_field."""
        from src.utils.schema_validation import GandalfSchemaValidator

        schema = {
            "number_field": {"type": "number", "min": 0, "max": 10},
            "integer_field": {"type": "integer", "min": 0, "max": 10},
            "dict_field": {"type": "dict", "schema": {}},
            "string_field": {"type": "string"},
        }

        validator = GandalfSchemaValidator(schema)

        # Test with wrong types to trigger error paths
        test_data = {
            "number_field": "not_a_number",
            "integer_field": "not_an_integer",
            "dict_field": "not_a_dict",
            "string_field": 123,
        }

        result = validator.validate(test_data)

        assert result is False
        assert len(validator.errors) >= 4

        # Check specific error messages
        error_messages = [str(err) for err in validator.errors]
        assert any("must be a number" in msg for msg in error_messages)
        assert any("must be an integer" in msg for msg in error_messages)
        assert any("must be a dict" in msg for msg in error_messages)
        assert any("must be a string" in msg for msg in error_messages)

    def test_validate_field_range_validation_errors(self):
        """Test range validation error paths."""
        from src.utils.schema_validation import GandalfSchemaValidator

        schema = {
            "number_field": {"type": "number", "min": 0, "max": 10},
            "integer_field": {"type": "integer", "min": 0, "max": 10},
        }

        validator = GandalfSchemaValidator(schema)

        # Test with out-of-range values
        test_data = {
            "number_field": 15,  # Above max
            "integer_field": -5,  # Below min
        }

        result = validator.validate(test_data)

        assert result is False
        assert len(validator.errors) >= 2

        # Check specific error messages
        error_messages = [str(err) for err in validator.errors]
        assert any("must be <=" in msg for msg in error_messages)
        assert any("must be >=" in msg for msg in error_messages)


class TestFileOperationsErrorHandling:
    """Test error handling for file operations."""

    def test_create_default_weights_file_io_error(self, tmp_path, monkeypatch):
        """Test create_default_weights_file with IO errors."""
        from src.utils.schema_validation import create_default_weights_file
        import yaml

        # Mock DEFAULT_WEIGHTS_FILE to point to a path we can't write to
        unwritable_path = tmp_path / "unwritable.yaml"
        unwritable_path.parent.mkdir(parents=True, exist_ok=True)

        # Make the file unwritable by creating a directory with the same name
        unwritable_path.mkdir()

        with monkeypatch.context() as m:
            m.setattr(
                "src.utils.schema_validation.DEFAULT_WEIGHTS_FILE", unwritable_path
            )

            # This should raise an exception
            with pytest.raises((OSError, IOError)):
                create_default_weights_file()

    def test_create_default_weights_file_yaml_error(self, tmp_path, monkeypatch):
        """Test create_default_weights_file with YAML errors."""
        from src.utils.schema_validation import create_default_weights_file
        import yaml

        # Mock yaml.dump to raise a YAMLError
        def mock_yaml_dump(*args, **kwargs):
            raise yaml.YAMLError("Test YAML error")

        weights_file = tmp_path / "test_weights.yaml"

        with monkeypatch.context() as m:
            m.setattr("src.utils.schema_validation.DEFAULT_WEIGHTS_FILE", weights_file)
            m.setattr("yaml.dump", mock_yaml_dump)

            # This should raise an exception
            with pytest.raises(yaml.YAMLError):
                create_default_weights_file()

    def test_get_weights_file_path_override_scenarios(self, tmp_path, monkeypatch):
        """Test get_weights_file_path with various override scenarios."""
        from src.utils.schema_validation import get_weights_file_path

        # Test with existing override file
        override_file = tmp_path / "override_weights.yaml"
        override_file.write_text("weights: {}")

        with monkeypatch.context() as m:
            m.setenv("GANDALF_WEIGHTS_FILE", str(override_file))
            m.setattr(
                "src.utils.schema_validation.WEIGHTS_FILE_OVERRIDE", str(override_file)
            )

            result = get_weights_file_path()
            assert result == override_file

    def test_get_weights_file_path_nonexistent_override(self, tmp_path, monkeypatch):
        """Test get_weights_file_path with non-existent override file."""
        from src.utils.schema_validation import get_weights_file_path

        # Test with non-existent override file
        nonexistent_file = tmp_path / "nonexistent.yaml"

        spec_file = tmp_path / "spec_weights.yaml"
        # Create a valid spec file with required sections
        spec_file.write_text(
            """
weights:
  recent_modification: 1.0
  file_size_optimal: 1.0
  file_type_priority: 1.0
  directory_importance: 1.0
  git_activity: 1.0
conversation:
  keyword_match: 1.0
  keyword_weight: 0.1
  recency: 1.0
  file_reference: 1.0
  file_reference_score: 0.2
recency_thresholds:
  days_1: 1.0
  days_7: 0.8
  days_30: 0.5
  days_90: 0.2
  default: 0.1
context:
  activity_score_recency_boost: 1.5
processing:
  conversation_early_termination_multiplier: 0.8
  early_termination_limit_multiplier: 1.5
file_extensions:
  py: 1.0
directories:
  src: 1.0
"""
        )

        default_file = tmp_path / "default_weights.yaml"

        with monkeypatch.context() as m:
            m.setattr(
                "src.utils.schema_validation.WEIGHTS_FILE_OVERRIDE",
                str(nonexistent_file),
            )
            m.setattr("src.utils.schema_validation.SPEC_WEIGHTS_FILE", spec_file)
            m.setattr("src.utils.schema_validation.DEFAULT_WEIGHTS_FILE", default_file)

            # Mock create_default_weights_file to create the file
            def mock_create_default():
                default_file.write_text("weights: {}")
                return default_file

            m.setattr(
                "src.utils.schema_validation.create_default_weights_file",
                mock_create_default,
            )

            result = get_weights_file_path()
            # Should fall back to spec file since it exists and is valid
            assert result == spec_file

    def test_get_weights_file_path_invalid_spec_file(self, tmp_path, monkeypatch):
        """Test get_weights_file_path with invalid spec file."""
        from src.utils.schema_validation import get_weights_file_path

        # Create invalid spec file
        invalid_spec = tmp_path / "invalid_spec.yaml"
        invalid_spec.write_text("invalid: yaml: content:")

        default_file = tmp_path / "default_weights.yaml"

        with monkeypatch.context() as m:
            m.setattr("src.utils.schema_validation.WEIGHTS_FILE_OVERRIDE", None)
            m.setattr("src.utils.schema_validation.SPEC_WEIGHTS_FILE", invalid_spec)
            m.setattr("src.utils.schema_validation.DEFAULT_WEIGHTS_FILE", default_file)

            # Mock create_default_weights_file to just create the file
            def mock_create_default():
                default_file.write_text("weights: {}")
                return default_file

            m.setattr(
                "src.utils.schema_validation.create_default_weights_file",
                mock_create_default,
            )

            result = get_weights_file_path()
            # Should fall back to default file
            assert result == default_file

    def test_get_weights_file_path_io_error_on_spec(self, tmp_path, monkeypatch):
        """Test get_weights_file_path with IO error when reading spec file."""
        from src.utils.schema_validation import get_weights_file_path
        import builtins

        spec_file = tmp_path / "spec_weights.yaml"
        spec_file.write_text("weights: {}")

        default_file = tmp_path / "default_weights.yaml"

        # Mock open to raise IOError for spec file
        original_open = builtins.open

        def mock_open(file, *args, **kwargs):
            if str(file) == str(spec_file):
                raise IOError("Test IO error")
            return original_open(file, *args, **kwargs)

        with monkeypatch.context() as m:
            m.setattr("src.utils.schema_validation.WEIGHTS_FILE_OVERRIDE", None)
            m.setattr("src.utils.schema_validation.SPEC_WEIGHTS_FILE", spec_file)
            m.setattr("src.utils.schema_validation.DEFAULT_WEIGHTS_FILE", default_file)
            m.setattr("builtins.open", mock_open)

            # Mock create_default_weights_file
            def mock_create_default():
                default_file.write_text("weights: {}")
                return default_file

            m.setattr(
                "src.utils.schema_validation.create_default_weights_file",
                mock_create_default,
            )

            result = get_weights_file_path()
            # Should fall back to default file
            assert result == default_file
