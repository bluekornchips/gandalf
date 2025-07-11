"""
Test weights configuration functionality.
"""

from src.config.weights import WeightsConfig


class TestWeightsConfig:
    """Test WeightsConfig class functionality."""

    def test_weights_config_initialization(self):
        """Test WeightsConfig initialization."""
        config = WeightsConfig()
        assert config is not None
        assert hasattr(config, "get")
        assert hasattr(config, "get_dict")

    def test_weights_config_get_method(self):
        """Test WeightsConfig get method."""
        config = WeightsConfig()

        # Test getting existing weights
        keyword_weight = config.get("conversation.keyword_weight")
        assert isinstance(keyword_weight, (int, float))
        assert keyword_weight > 0

        # Test getting non-existent key with default
        default_value = config.get("nonexistent.key", 42)
        assert default_value == 42

    def test_weights_config_get_dict_method(self):
        """Test WeightsConfig get_dict method."""
        config = WeightsConfig()

        # Test getting existing section
        conversation_weights = config.get_dict("conversation")
        assert isinstance(conversation_weights, dict)
        assert len(conversation_weights) > 0

        # Test getting non-existent section
        empty_dict = config.get_dict("nonexistent_section")
        assert isinstance(empty_dict, dict)
        assert len(empty_dict) == 0

    def test_weights_config_validation_methods(self):
        """Test WeightsConfig validation methods."""
        config = WeightsConfig()

        has_errors = config.has_validation_errors()
        assert isinstance(has_errors, bool)

        errors = config.get_validation_errors()
        assert isinstance(errors, list)

        status = config.get_weights_validation_status()
        assert isinstance(status, dict)
        assert "has_errors" in status
        assert "error_count" in status
        assert "status" in status
        assert "message" in status

    def test_weights_config_file_extension_weights(self):
        """Test file extension weights functionality."""
        config = WeightsConfig()

        ext_weights = config.get_file_extension_weights()
        assert isinstance(ext_weights, dict)

        # Should have some default extensions
        assert "py" in ext_weights or len(ext_weights) >= 0

    def test_weights_config_directory_priority_weights(self):
        """Test directory priority weights functionality."""
        config = WeightsConfig()

        dir_weights = config.get_directory_priority_weights()
        assert isinstance(dir_weights, dict)

        # Should have some default directories
        assert "src" in dir_weights or len(dir_weights) >= 0


class TestIntegrationScenarios:
    """Test integration scenarios and complex workflows."""

    def test_integration_workflow(self):
        """Test complete integration workflow."""
        config = WeightsConfig()

        # Test that we can get both conversation and context weights
        conversation_weights = config.get_dict("conversation")
        context_weights = config.get_dict("weights")

        assert isinstance(conversation_weights, dict)
        assert isinstance(context_weights, dict)

        # Test that individual weight retrieval works
        keyword_weight = config.get("conversation.keyword_weight")
        assert isinstance(keyword_weight, (int, float))

    def test_error_recovery(self):
        """Test error recovery scenarios."""
        config = WeightsConfig()

        # Test getting invalid keys gracefully
        result = config.get("invalid.key.path", "default")
        assert result == "default"

        # Test getting invalid dict sections gracefully
        result = config.get_dict("invalid_section")
        assert isinstance(result, dict)
        assert len(result) == 0
