"""Tests for schema validation utilities."""

from src.utils.schema_validation import (
    WEIGHTS_SCHEMA,
    apply_schema_defaults,
    create_default_weights_file,
    create_validator,
    format_cerberus_errors,
    get_weights_file_path,
    get_weights_schema,
    validate_weights_config,
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

    def test_format_cerberus_errors(self):
        """Test error formatting function."""
        errors = {
            "field1": ["error message 1"],
            "field2": {"subfield": ["error message 2"]},
        }

        formatted = format_cerberus_errors(errors)
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
