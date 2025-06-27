"""
Tests for database configuration functionality.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.config.database_config import (
    DatabaseConfig,
    get_database_config,
    reload_database_config,
)


class TestDatabaseConfig:
    """Tests for DatabaseConfig class"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "gandalf_config.json"
        # Create fresh config instance for each test
        self.config = DatabaseConfig(config_path=self.config_path)

        # Reset global instance to avoid test interference
        import src.config.database_config

        src.config.database_config._config_instance = None

    def teardown_method(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

        # Reset global instance after each test
        import src.config.database_config

        src.config.database_config._config_instance = None

    def test_config_initialization_with_defaults(self):
        """Test config initialization with default values"""
        config = DatabaseConfig()

        assert config.is_auto_discovery_enabled() is True
        assert config.get_primary_ide() is None
        assert config.get_max_databases_per_ide() == 10
        assert config.get_min_conversation_count() == 1

    def test_save_and_load_config(self):
        """Test saving and loading configuration"""
        # Modify some settings
        self.config.set_primary_ide("cursor")
        self.config.add_custom_location(
            "cursor", Path("/minas_tirith/conversations")
        )

        # Save configuration
        assert self.config.save_config() is True
        assert self.config_path.exists()

        # Load configuration in new instance
        new_config = DatabaseConfig(config_path=self.config_path)
        assert new_config.get_primary_ide() == "cursor"
        custom_locations = new_config.get_custom_locations("cursor")
        assert len(custom_locations) == 1
        assert str(custom_locations[0]).endswith("minas_tirith/conversations")

    def test_custom_locations_management(self):
        """Test managing custom database locations"""
        # Use a completely fresh config to avoid state pollution
        fresh_config = DatabaseConfig()

        rivendell_path = Path("/rivendell/elrond_conversations")
        rohan_path = Path("/edoras/theoden_discussions")

        # Add custom locations
        fresh_config.add_custom_location("cursor", rivendell_path)
        fresh_config.add_custom_location("claude-code", rohan_path)

        # Verify locations were added
        cursor_locations = fresh_config.get_custom_locations("cursor")
        claude_locations = fresh_config.get_custom_locations("claude-code")

        assert len(cursor_locations) == 1
        assert len(claude_locations) == 1
        assert rivendell_path in cursor_locations
        assert rohan_path in claude_locations

        # Remove a location
        removed = fresh_config.remove_custom_location("cursor", rivendell_path)
        assert removed is True

        # Verify removal
        cursor_locations_after = fresh_config.get_custom_locations("cursor")
        assert len(cursor_locations_after) == 0

        # Try to remove non-existent location
        not_removed = fresh_config.remove_custom_location(
            "cursor", Path("/mordor/sauron_evil")
        )
        assert not_removed is False

    def test_exclusion_patterns_and_paths(self):
        """Test exclusion settings"""
        # Test default exclusion patterns
        patterns = self.config.get_exclusion_patterns()
        assert "*.tmp" in patterns
        assert "*.lock" in patterns
        assert "*~" in patterns

        # Test exclusion paths (should be empty by default)
        paths = self.config.get_exclusion_paths()
        assert len(paths) == 0

    def test_primary_ide_setting(self):
        """Test setting primary IDE preference"""
        # Create a completely fresh config to ensure clean state
        fresh_config = DatabaseConfig()

        # Default should be None for fresh instance
        assert fresh_config.get_primary_ide() is None

        # Set primary IDE
        fresh_config.set_primary_ide("cursor")
        assert fresh_config.get_primary_ide() == "cursor"

        # Change primary IDE
        fresh_config.set_primary_ide("claude-code")
        assert fresh_config.get_primary_ide() == "claude-code"

    def test_create_example_config(self):
        """Test creating example configuration"""
        example_path = Path(self.temp_dir.name) / "example_config.json"

        created_path = self.config.create_example_config(example_path)

        assert created_path == example_path
        assert example_path.exists()

        # Verify example config content
        with open(example_path, "r") as f:
            example_data = json.load(f)

        assert example_data["version"] == "1.0"
        assert "custom_locations" in example_data
        assert "cursor" in example_data["custom_locations"]
        assert "claude-code" in example_data["custom_locations"]

    def test_config_validation(self):
        """Test configuration validation"""
        # Add some invalid paths
        self.config.add_custom_location(
            "cursor", Path("/nonexistent/path/to/nowhere")
        )

        issues = self.config.validate_config()

        # Should find the non-existent path issue
        assert len(issues) > 0
        assert any("does not exist" in issue for issue in issues)

    @patch("src.config.database_config.log_error")
    def test_load_config_with_invalid_json(self, mock_log_error):
        """Test loading configuration with invalid JSON"""
        # Create invalid JSON file
        invalid_config_path = Path(self.temp_dir.name) / "invalid.json"
        with open(invalid_config_path, "w") as f:
            f.write("{ invalid json content")

        # Try to load invalid config
        config = DatabaseConfig(config_path=invalid_config_path)

        # Should use defaults and log error
        assert config.is_auto_discovery_enabled() is True
        mock_log_error.assert_called_once()

    def test_merge_config_behavior(self):
        """Test configuration merging"""
        # Create base config with some custom settings
        base_config = {
            "auto_discovery": False,
            "custom_locations": {"cursor": ["/existing/path"]},
            "preferences": {"primary_ide": "cursor"},
        }

        # Create override config
        override_config = {
            "custom_locations": {
                "cursor": ["/new/path"],
                "claude-code": ["/claude/path"],
            },
            "preferences": {"max_databases_per_ide": 5},
        }

        # Test merging
        self.config._merge_config(base_config, override_config)

        # Verify merge results
        assert base_config["auto_discovery"] is False  # Unchanged
        assert base_config["custom_locations"]["cursor"] == [
            "/new/path"
        ]  # Overridden
        assert base_config["custom_locations"]["claude-code"] == [
            "/claude/path"
        ]  # Added
        assert (
            base_config["preferences"]["primary_ide"] == "cursor"
        )  # Unchanged
        assert (
            base_config["preferences"]["max_databases_per_ide"] == 5
        )  # Added


class TestGlobalConfigFunctions:
    """Tests for global configuration functions"""

    def test_get_database_config_singleton(self):
        """Test that get_database_config returns the same instance"""
        config1 = get_database_config()
        config2 = get_database_config()

        # Should be the same instance
        assert config1 is config2

    @patch("src.config.database_config.DatabaseConfig")
    def test_reload_database_config(self, mock_config_class):
        """Test reloading database configuration"""
        mock_instance = Mock()
        mock_config_class.return_value = mock_instance

        result = reload_database_config()

        # Should create new instance
        mock_config_class.assert_called_once()
        assert result == mock_instance


class TestConfigurationIntegration:
    """Integration tests for configuration system"""

    def test_real_config_file_workflow(self):
        """Test complete workflow with real config file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"

            # Create initial config
            config = DatabaseConfig(config_path=config_path)
            config.set_primary_ide("cursor")
            config.add_custom_location(
                "cursor", Path("/fellowship/conversations")
            )
            config.add_custom_location(
                "claude-code", Path("/white_council/meetings")
            )

            # Save config
            assert config.save_config() is True

            # Reload from file
            new_config = DatabaseConfig(config_path=config_path)

            # Verify all settings persisted
            assert new_config.get_primary_ide() == "cursor"
            cursor_locations = new_config.get_custom_locations("cursor")
            claude_locations = new_config.get_custom_locations("claude-code")

            assert len(cursor_locations) == 1
            assert len(claude_locations) == 1
            assert str(cursor_locations[0]).endswith(
                "fellowship/conversations"
            )
            assert str(claude_locations[0]).endswith("white_council/meetings")

            # Validate configuration
            issues = new_config.validate_config()
            # Should have issues since paths don't exist
            assert len(issues) > 0
