"""
Database configuration management for Gandalf MCP server.

This module provides configuration file support for manually specifying
database locations and custom IDE setups.
"""

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.common import log_debug, log_error, log_info


class DatabaseConfig:
    """Configuration manager for conversation database settings."""

    DEFAULT_CONFIG_LOCATIONS = [
        "~/.gandalf/database-config.json",
        "~/.config/gandalf/database-config.json",
        ".gandalf-db-config.json",  # Project-specific config
    ]

    DEFAULT_CONFIG = {
        "version": "1.0",
        "auto_discovery": True,
        "custom_locations": {
            "cursor": [],
            "claude-code": [],
        },
        "exclusions": {
            "paths": [],
            "patterns": ["*.tmp", "*.lock", "*~"],
        },
        "preferences": {
            "primary_ide": None,
            "max_databases_per_ide": 10,
            "min_conversation_count": 1,
        },
    }

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize database configuration."""
        self.config_path = config_path
        # Use deep copy to avoid mutating the class-level default
        self.config = copy.deepcopy(self.DEFAULT_CONFIG)
        self._load_config()

    def _find_config_file(self) -> Optional[Path]:
        """Find the first existing configuration file."""
        if self.config_path:
            return self.config_path if self.config_path.exists() else None

        for config_location in self.DEFAULT_CONFIG_LOCATIONS:
            config_path = Path(config_location).expanduser()
            if config_path.exists():
                return config_path

        return None

    def _load_config(self) -> None:
        """Load configuration from file."""
        config_file = self._find_config_file()
        if not config_file:
            log_debug("No database configuration file found, using defaults")
            return

        try:
            with open(config_file, "r") as f:
                file_config = json.load(f)

            # Merge with defaults
            self._merge_config(self.config, file_config)
            log_info(f"Loaded database configuration from: {config_file}")

        except (json.JSONDecodeError, OSError) as e:
            log_error(e, f"loading database configuration from {config_file}")

    def _merge_config(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> None:
        """Recursively merge configuration dictionaries."""
        for key, value in override.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def save_config(self, config_path: Optional[Path] = None) -> bool:
        """Save current configuration to file."""
        save_path = (
            config_path
            or self.config_path
            or Path(self.DEFAULT_CONFIG_LOCATIONS[0]).expanduser()
        )

        try:
            # Ensure directory exists
            save_path.parent.mkdir(parents=True, exist_ok=True)

            with open(save_path, "w") as f:
                json.dump(self.config, f, indent=2)

            log_info(f"Saved database configuration to: {save_path}")
            return True

        except (OSError, json.JSONEncodeError) as e:
            log_error(e, f"saving database configuration to {save_path}")
            return False

    def get_custom_locations(self, ide_type: str) -> List[Path]:
        """Get custom database locations for an IDE type."""
        locations = self.config.get("custom_locations", {}).get(ide_type, [])
        return [Path(loc).expanduser() for loc in locations]

    def add_custom_location(self, ide_type: str, location: Path) -> None:
        """Add a custom database location for an IDE type."""
        if "custom_locations" not in self.config:
            self.config["custom_locations"] = {}
        if ide_type not in self.config["custom_locations"]:
            self.config["custom_locations"][ide_type] = []

        location_str = str(location)
        if location_str not in self.config["custom_locations"][ide_type]:
            self.config["custom_locations"][ide_type].append(location_str)
            log_info(f"Added custom {ide_type} location: {location}")

    def remove_custom_location(self, ide_type: str, location: Path) -> bool:
        """Remove a custom database location for an IDE type."""
        locations = self.config.get("custom_locations", {}).get(ide_type, [])
        location_str = str(location)

        if location_str in locations:
            locations.remove(location_str)
            log_info(f"Removed custom {ide_type} location: {location}")
            return True

        return False

    def is_auto_discovery_enabled(self) -> bool:
        """Check if automatic database discovery is enabled."""
        return self.config.get("auto_discovery", True)

    def get_exclusion_patterns(self) -> List[str]:
        """Get file/directory exclusion patterns."""
        return self.config.get("exclusions", {}).get("patterns", [])

    def get_exclusion_paths(self) -> List[Path]:
        """Get excluded paths."""
        paths = self.config.get("exclusions", {}).get("paths", [])
        return [Path(p).expanduser() for p in paths]

    def get_primary_ide(self) -> Optional[str]:
        """Get the preferred primary IDE."""
        return self.config.get("preferences", {}).get("primary_ide")

    def set_primary_ide(self, ide_type: str) -> None:
        """Set the preferred primary IDE."""
        if "preferences" not in self.config:
            self.config["preferences"] = {}
        self.config["preferences"]["primary_ide"] = ide_type
        log_info(f"Set primary IDE to: {ide_type}")

    def get_max_databases_per_ide(self) -> int:
        """Get maximum number of databases to use per IDE."""
        return self.config.get("preferences", {}).get(
            "max_databases_per_ide", 10
        )

    def get_min_conversation_count(self) -> int:
        """Get minimum conversation count for a database to be considered."""
        return self.config.get("preferences", {}).get(
            "min_conversation_count", 1
        )

    def create_example_config(self, save_path: Optional[Path] = None) -> Path:
        """Create an example configuration file."""
        example_config = {
            "version": "1.0",
            "auto_discovery": True,
            "custom_locations": {
                "cursor": [
                    "~/custom-cursor-data/workspaceStorage",
                    "/shared/team-cursor-databases",
                ],
                "claude-code": [
                    "~/custom-claude-data",
                    "/shared/team-claude-sessions",
                ],
            },
            "exclusions": {
                "paths": [
                    "~/temp-conversations",
                    "/tmp/cursor-cache",
                ],
                "patterns": [
                    "*.tmp",
                    "*.lock",
                    "*~",
                    "*.backup",
                ],
            },
            "preferences": {
                "primary_ide": "cursor",
                "max_databases_per_ide": 5,
                "min_conversation_count": 2,
            },
        }

        save_path = (
            save_path
            or Path("~/.gandalf/database-config.example.json").expanduser()
        )
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, "w") as f:
            json.dump(example_config, f, indent=2)

        log_info(f"Created example configuration at: {save_path}")
        return save_path

    def validate_config(self) -> List[str]:
        """Validate the current configuration and return any issues."""
        issues = []

        # Check custom locations exist
        for ide_type, locations in self.config.get(
            "custom_locations", {}
        ).items():
            for location in locations:
                path = Path(location).expanduser()
                if not path.exists():
                    issues.append(
                        f"Custom {ide_type} location does not exist: {location}"
                    )

        # Check exclusion paths
        for path_str in self.config.get("exclusions", {}).get("paths", []):
            path = Path(path_str).expanduser()
            if not path.exists():
                issues.append(f"Exclusion path does not exist: {path_str}")

        return issues


# Global configuration instance
_config_instance = None


def get_database_config() -> DatabaseConfig:
    """Get the global database configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = DatabaseConfig()
    return _config_instance


def reload_database_config() -> DatabaseConfig:
    """Reload the database configuration from file."""
    global _config_instance
    _config_instance = DatabaseConfig()
    return _config_instance
