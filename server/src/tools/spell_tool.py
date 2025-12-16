"""
Spell tool implementation for executing external API tools.
"""

import asyncio
import json
import os
import traceback
from pathlib import Path
from typing import Any, Dict, List

from src.tools.base_tool import BaseTool
from src.protocol.models import ToolResult
from src.config.constants import (
    GANDALF_REGISTRY_FILE,
    SPELLS_REGISTRY_KEY,
    DEFAULT_ALLOWED_PATHS,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_TIMEOUT_SECONDS,
)
from src.utils.logger import log_info, log_error


class SpellTool(BaseTool):
    """Tool for executing registered external spells."""

    def __init__(self) -> None:
        """Initialize the spell tool."""
        super().__init__()
        self._spells: Dict[str, Dict[str, Any]] = {}
        self._load_spells()

    def _load_spells(self) -> None:
        """Load spells from registry file."""
        try:
            if not os.path.exists(GANDALF_REGISTRY_FILE):
                log_info("Registry file not found, no spells loaded")
                return

            with open(GANDALF_REGISTRY_FILE, "r", encoding="utf-8") as f:
                registry_data = json.load(f)

            spells = registry_data.get(SPELLS_REGISTRY_KEY, {})
            if isinstance(spells, dict):
                self._spells = spells
                log_info(f"Loaded {len(self._spells)} spell(s) from registry")
            else:
                log_error("Invalid spells format in registry file")
                self._spells = {}
        except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
            error_msg = f"Error loading spells from registry: {str(e)}"
            log_error(error_msg, {"traceback": traceback.format_exc()})
            self._spells = {}

    def _is_tool_registered(self, tool_name: str) -> bool:
        """Check if a spell tool is registered.

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if registered, False otherwise
        """
        return tool_name in self._spells

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

    def _is_command_permitted(self, command: str, allowed_commands: List[str]) -> bool:
        """Check if a command is in the allowed commands list.

        Args:
            command: Command to check
            allowed_commands: List of allowed command patterns

        Returns:
            True if command is permitted, False otherwise
        """
        if not allowed_commands:
            return False

        # Extract base command (first word)
        base_command = command.split()[0] if command else ""
        if not base_command:
            return False

        # Check if base command matches any allowed command
        for allowed in allowed_commands:
            if base_command == allowed or command.startswith(allowed + " "):
                return True

        return False

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
        if "path" in spell_config and not isinstance(spell_config["path"], str):
            return False, "Spell path must be a string"

        if "allowed_paths" in spell_config:
            if not isinstance(spell_config["allowed_paths"], list):
                return False, "allowed_paths must be a list"
            if not all(isinstance(p, str) for p in spell_config["allowed_paths"]):
                return False, "All allowed_paths must be strings"

        if "allowed_commands" in spell_config:
            if not isinstance(spell_config["allowed_commands"], list):
                return False, "allowed_commands must be a list"
            if not all(isinstance(c, str) for c in spell_config["allowed_commands"]):
                return False, "All allowed_commands must be strings"

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
            arguments: Tool arguments

        Returns:
            Command output as string
        """
        command = spell_config["command"]
        working_dir = spell_config.get("path")
        timeout = min(
            spell_config.get("timeout", DEFAULT_TIMEOUT_SECONDS), MAX_TIMEOUT_SECONDS
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

        # Prepare command arguments
        cmd_parts = command.split()
        if not cmd_parts:
            raise ValueError("Empty command")

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
        return "Cast a registered external spell with security checks"

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Tool input schema."""
        return {
            "type": "object",
            "properties": {
                "spell_name": {
                    "type": "string",
                    "description": "Name of the registered spell to cast",
                },
                "arguments": {
                    "type": "object",
                    "description": "Arguments to pass to the spell (available as environment variables)",
                },
            },
            "required": ["spell_name"],
        }

    async def execute(self, arguments: Dict[str, Any] | None) -> List[ToolResult]:
        """Execute the spell tool."""
        log_info("Spell tool called")

        if not arguments:
            return [ToolResult(text="Error: No arguments provided")]

        spell_name = arguments.get("spell_name")
        if not spell_name or not isinstance(spell_name, str):
            return [ToolResult(text="Error: spell_name is required and must be a string")]

        # Check if tool is registered
        if not self._is_tool_registered(spell_name):
            return [
                ToolResult(
                    text=f"Error: Spell '{spell_name}' is not registered. Use spells.sh to register spells."
                )
            ]

        spell_config = self._spells[spell_name]

        # Validate spell configuration
        is_valid, error_msg = self._validate_spell_config(spell_config)
        if not is_valid:
            return [ToolResult(text=f"Error: Invalid spell configuration: {error_msg}")]

        # Security checks
        command = spell_config["command"]
        spell_path = spell_config.get("path")
        allowed_paths = spell_config.get("allowed_paths", DEFAULT_ALLOWED_PATHS)
        allowed_commands = spell_config.get("allowed_commands", [])

        # Check path permission if path is specified
        if spell_path:
            if not self._is_path_permitted(spell_path, allowed_paths):
                return [
                    ToolResult(
                        text=f"Error: Spell path '{spell_path}' is not in allowed_paths"
                    )
                ]

        # Check command permission if allowed_commands is specified
        if allowed_commands:
            if not self._is_command_permitted(command, allowed_commands):
                return [
                    ToolResult(
                        text=f"Error: Spell command '{command}' is not in allowed_commands"
                    )
                ]

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
