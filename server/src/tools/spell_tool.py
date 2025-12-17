"""
Spell tool implementation for executing spells from YAML files.
"""

import asyncio
import json
import os
import subprocess
import traceback
from pathlib import Path
from typing import Any, Dict, List

import yaml

from src.tools.base_tool import BaseTool
from src.protocol.models import ToolResult
from src.config.constants import (
    DEFAULT_TIMEOUT_SECONDS,
    MAX_TIMEOUT_SECONDS,
    SPELLS_DIRECTORY,
)
from src.utils.logger import log_info, log_error


def _get_project_root() -> Path:
    """Get the project root directory.

    Returns:
        Path to project root

    Raises:
        RuntimeError: If project root cannot be determined
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback: assume we're in server/src/tools, go up 3 levels
        return Path(__file__).parent.parent.parent


class SpellTool(BaseTool):
    """Tool for executing spells from YAML files in spells/ directory."""

    def __init__(self) -> None:
        """Initialize the spell tool."""
        super().__init__()
        self._spells: Dict[str, Dict[str, Any]] = {}
        self._spells_directory = SPELLS_DIRECTORY
        self._load_spells()

    def _load_spells(self) -> None:
        """Load spells from YAML files in spells/ directory."""
        try:
            project_root = _get_project_root()
            spells_dir = project_root / self._spells_directory

            if not spells_dir.exists():
                log_info(f"Spells directory not found: {spells_dir}, no spells loaded")
                return

            if not spells_dir.is_dir():
                log_error(f"Spells path exists but is not a directory: {spells_dir}")
                return

            self._spells = {}
            yaml_files = list(spells_dir.glob("*.yaml")) + list(
                spells_dir.glob("*.yml")
            )

            for yaml_file in yaml_files:
                try:
                    with open(yaml_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        # Expand environment variables in the YAML content
                        content = os.path.expandvars(content)
                        spell_data = yaml.safe_load(content)

                    # Expand environment variables in nested values (lists, dicts)
                    if isinstance(spell_data, dict):
                        spell_data = self._expand_env_vars_recursive(spell_data)

                    if not isinstance(spell_data, dict):
                        log_error(
                            f"Invalid spell file format in {yaml_file}: not a dictionary"
                        )
                        continue

                    # Validate required fields
                    if "name" not in spell_data:
                        log_error(
                            f"Spell file {yaml_file} missing required field: name"
                        )
                        continue

                    spell_name = spell_data["name"]
                    if not isinstance(spell_name, str) or not spell_name:
                        log_error(f"Spell file {yaml_file} has invalid name field")
                        continue

                    # Use filename as spell name if name doesn't match
                    if spell_name != yaml_file.stem:
                        log_info(
                            f"Spell name '{spell_name}' in {yaml_file} doesn't match filename, using filename"
                        )
                        spell_name = yaml_file.stem
                        spell_data["name"] = spell_name

                    self._spells[spell_name] = spell_data
                    log_info(f"Loaded spell '{spell_name}' from {yaml_file}")

                except yaml.YAMLError as e:
                    log_error(f"Error parsing YAML file {yaml_file}: {str(e)}")
                    continue
                except (IOError, OSError) as e:
                    log_error(f"Error reading spell file {yaml_file}: {str(e)}")
                    continue

            log_info(f"Loaded {len(self._spells)} spell(s) from {spells_dir}")

        except Exception as e:
            error_msg = f"Error loading spells from directory: {str(e)}"
            log_error(error_msg, {"traceback": traceback.format_exc()})
            self._spells = {}

    def _expand_env_vars_recursive(self, data: Any) -> Any:
        """Recursively expand environment variables in data structures.

        Args:
            data: Data structure (dict, list, or str) to expand

        Returns:
            Data structure with environment variables expanded
        """
        if isinstance(data, dict):
            return {
                key: self._expand_env_vars_recursive(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._expand_env_vars_recursive(item) for item in data]
        elif isinstance(data, str):
            return os.path.expandvars(data)
        else:
            return data

    def _is_spell_registered(self, spell_name: str) -> bool:
        """Check if a spell is registered.

        Args:
            spell_name: Name of the spell to check

        Returns:
            True if registered, False otherwise
        """
        return spell_name in self._spells

    def _is_path_permitted(self, path: str, allowed_paths: List[str]) -> bool:
        """Check if a path is in the allowed paths list.

        Args:
            path: Path to check
            allowed_paths: List of allowed path patterns

        Returns:
            True if path is permitted, False otherwise
        """
        if not allowed_paths:
            return False

        try:
            resolved_path = str(Path(path).resolve())
            for allowed in allowed_paths:
                allowed_resolved = str(Path(allowed).resolve())
                # Check exact match or if path is within allowed directory
                if resolved_path == allowed_resolved or resolved_path.startswith(
                    allowed_resolved + os.sep
                ):
                    return True
        except (OSError, ValueError) as e:
            log_error(f"Error resolving path {path}: {str(e)}")
            return False

        return False

    def _are_flags_permitted(self, flags: List[str], allowed_flags: List[str]) -> bool:
        """Check if flags are in the allowed flags list.

        Args:
            flags: List of flags/arguments to check
            allowed_flags: List of allowed flag patterns

        Returns:
            True if all flags are permitted, False otherwise
        """
        if not allowed_flags:
            # Empty allowed_flags means no flags permitted
            return len(flags) == 0

        # Check if all provided flags are in the allowed list
        for flag in flags:
            if flag not in allowed_flags:
                return False

        return True

    def _validate_spell_config(self, spell_config: Dict[str, Any]) -> tuple[bool, str]:
        """Validate spell configuration.

        Args:
            spell_config: Spell configuration dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ["name", "description", "command"]
        for field in required_fields:
            if field not in spell_config:
                return False, f"Missing required field: {field}"

        if not isinstance(spell_config["name"], str) or not spell_config["name"]:
            return False, "Spell name must be a non-empty string"

        if not isinstance(spell_config["description"], str):
            return False, "Spell description must be a string"

        if not isinstance(spell_config["command"], str) or not spell_config["command"]:
            return False, "Spell command must be a non-empty string"

        # Validate optional fields
        if "flags" in spell_config:
            if not isinstance(spell_config["flags"], list):
                return False, "flags must be a list"
            if not all(isinstance(f, str) for f in spell_config["flags"]):
                return False, "All flags must be strings"

        if "paths" in spell_config:
            if not isinstance(spell_config["paths"], list):
                return False, "paths must be a list"
            if not all(isinstance(p, str) for p in spell_config["paths"]):
                return False, "All paths must be strings"

        if "timeout" in spell_config:
            timeout = spell_config["timeout"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                return False, "timeout must be a positive number"
            if timeout > MAX_TIMEOUT_SECONDS:
                return False, f"timeout cannot exceed {MAX_TIMEOUT_SECONDS} seconds"

        return True, ""

    async def _execute_spell(
        self, spell_config: Dict[str, Any], arguments: Dict[str, Any] | None
    ) -> str:
        """Execute a spell command.

        Args:
            spell_config: Spell configuration
            arguments: Tool arguments (may contain flags to validate)

        Returns:
            Command output as string
        """
        command = spell_config["command"]
        allowed_flags = spell_config.get("flags", [])
        allowed_paths = spell_config.get("paths", [])
        timeout = min(
            spell_config.get("timeout", DEFAULT_TIMEOUT_SECONDS), MAX_TIMEOUT_SECONDS
        )

        # Determine working directory from allowed paths
        working_dir = None
        if allowed_paths:
            # Use first allowed path as working directory
            working_dir = allowed_paths[0]
        else:
            raise ValueError("No paths specified for spell execution")

        # Validate working directory is in allowed paths
        if not self._is_path_permitted(working_dir, allowed_paths):
            raise ValueError(f"Working directory {working_dir} is not in allowed paths")

        # Parse command and validate flags
        cmd_parts = command.split()
        if not cmd_parts:
            raise ValueError("Empty command")

        # Extract flags from command (everything after the base command)
        command_flags = []
        if len(cmd_parts) > 1:
            command_flags = cmd_parts[1:]

        # Validate flags if any are present
        if command_flags:
            # Filter to only flag-like arguments (start with -)
            actual_flags = [f for f in command_flags if f.startswith("-")]
            if actual_flags and not self._are_flags_permitted(
                actual_flags, allowed_flags
            ):
                raise ValueError(
                    f"Flags {actual_flags} in command are not permitted. Allowed flags: {allowed_flags}"
                )

        # Prepare environment variables from arguments
        env = os.environ.copy()
        if arguments:
            for key, value in arguments.items():
                env_key = f"SPELL_ARG_{key.upper()}"
                if isinstance(value, (dict, list)):
                    env[env_key] = json.dumps(value)
                else:
                    env[env_key] = str(value)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise TimeoutError(f"Spell execution timed out after {timeout} seconds")

            if process.returncode != 0:
                error_output = stderr.decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"Spell execution failed with exit code {process.returncode}: {error_output}"
                )

            return stdout.decode("utf-8", errors="replace")

        except FileNotFoundError:
            raise ValueError(f"Command not found: {cmd_parts[0]}")
        except PermissionError:
            raise ValueError(f"Permission denied executing: {cmd_parts[0]}")

    @property
    def name(self) -> str:
        """Tool name."""
        return "cast_spell"

    @property
    def description(self) -> str:
        """Tool description."""
        return "Cast a spell from YAML files in the spells/ directory"

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Tool input schema."""
        return {
            "type": "object",
            "properties": {
                "list": {
                    "type": "boolean",
                    "description": "When true, return the list of available spells",
                },
                "spell_name": {
                    "type": "string",
                    "description": "Name of the spell to cast (matches YAML filename)",
                },
                "arguments": {
                    "type": "object",
                    "description": "Arguments to pass to the spell (available as environment variables)",
                },
            },
            "required": [],
        }

    async def execute(self, arguments: Dict[str, Any] | None) -> List[ToolResult]:
        """Execute the spell tool."""
        log_info("Spell tool called")

        if not arguments:
            return [ToolResult(text="Error: No arguments provided")]

        # List available spells without requiring spell_name
        if arguments.get("list"):
            self._load_spells()
            spells_summary = []
            for name, config in sorted(self._spells.items()):
                spells_summary.append(
                    {
                        "name": name,
                        "description": config.get("description", ""),
                        "paths": config.get("paths", []),
                    }
                )

            return [
                ToolResult(
                    text=json.dumps(
                        {"status": "success", "spells": spells_summary},
                        indent=2,
                        ensure_ascii=False,
                    )
                )
            ]

        spell_name = arguments.get("spell_name")
        if not spell_name or not isinstance(spell_name, str):
            return [
                ToolResult(text="Error: spell_name is required and must be a string")
            ]

        previous_spells = self._spells.copy()
        self._load_spells()
        if not self._is_spell_registered(spell_name) and spell_name in previous_spells:
            self._spells = previous_spells

        # Check if spell is registered
        if not self._is_spell_registered(spell_name):
            return [
                ToolResult(
                    text=f"Error: Spell '{spell_name}' not found. Create {spell_name}.yaml in the spells/ directory."
                )
            ]

        spell_config = self._spells[spell_name]

        # Validate spell configuration
        is_valid, error_msg = self._validate_spell_config(spell_config)
        if not is_valid:
            return [ToolResult(text=f"Error: Invalid spell configuration: {error_msg}")]

        # Security checks
        allowed_paths = spell_config.get("paths", [])

        # Check that paths are specified
        if not allowed_paths:
            return [
                ToolResult(
                    text="Error: Spell must specify at least one path in paths array"
                )
            ]

        # Validate that paths are accessible (basic check)
        for path in allowed_paths:
            try:
                resolved = Path(path).resolve()
                if not resolved.exists():
                    log_error(f"Spell path does not exist: {path}")
            except (OSError, ValueError) as e:
                log_error(f"Error validating spell path {path}: {str(e)}")

        # Execute spell
        try:
            spell_args = arguments.get("arguments", {})
            output = await self._execute_spell(spell_config, spell_args)

            result = {
                "status": "success",
                "spell": spell_name,
                "output": output,
            }

            return [ToolResult(text=json.dumps(result, indent=2, ensure_ascii=False))]

        except TimeoutError as e:
            error_msg = f"Spell execution timeout: {str(e)}"
            log_error(error_msg, {"traceback": traceback.format_exc()})
            return [ToolResult(text=f"Error: {error_msg}")]

        except (ValueError, RuntimeError) as e:
            error_msg = f"Spell execution error: {str(e)}"
            log_error(error_msg, {"traceback": traceback.format_exc()})
            return [ToolResult(text=f"Error: {error_msg}")]

        except Exception as e:
            error_msg = f"Unexpected spell execution error: {str(e)}"
            log_error(error_msg, {"traceback": traceback.format_exc()})
            return [ToolResult(text=f"Error: {error_msg}")]
