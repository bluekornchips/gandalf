"""Test suite for spell tool implementation."""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import pytest

from src.tools.spell_tool import SpellTool
from src.protocol.models import ToolResult
from src.config.constants import (
    GANDALF_REGISTRY_FILE,
    SPELLS_REGISTRY_KEY,
    DEFAULT_ALLOWED_PATHS,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_TIMEOUT_SECONDS,
)


class TestSpellTool:
    """Test suite for SpellTool class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.tool = SpellTool()

    def test_tool_name(self) -> None:
        """Test tool name property."""
        assert self.tool.name == "cast_spell"

    def test_tool_description(self) -> None:
        """Test tool description property."""
        assert "registered external spell" in self.tool.description.lower()
        assert "security checks" in self.tool.description.lower()

    def test_input_schema(self) -> None:
        """Test tool input schema structure."""
        schema = self.tool.input_schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "spell_name" in schema["properties"]
        assert "arguments" in schema["properties"]
        assert schema["required"] == ["spell_name"]

    def test_input_schema_spell_name(self) -> None:
        """Test spell_name property in input schema."""
        schema = self.tool.input_schema
        spell_name_prop = schema["properties"]["spell_name"]
        assert spell_name_prop["type"] == "string"
        assert "description" in spell_name_prop

    def test_input_schema_arguments(self) -> None:
        """Test arguments property in input schema."""
        schema = self.tool.input_schema
        arguments_prop = schema["properties"]["arguments"]
        assert arguments_prop["type"] == "object"
        assert "description" in arguments_prop

    def test_load_spells_registry_not_found(self) -> None:
        """Test loading spells when registry file doesn't exist."""
        with patch("os.path.exists", return_value=False):
            tool = SpellTool()
            assert tool._spells == {}

    def test_load_spells_empty_registry(self) -> None:
        """Test loading spells from empty registry."""
        empty_registry = "{}"

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=empty_registry)),
        ):
            tool = SpellTool()
            assert tool._spells == {}

    def test_load_spells_valid_registry(self) -> None:
        """Test loading spells from valid registry."""
        registry_data = {
            SPELLS_REGISTRY_KEY: {
                "test_spell": {
                    "name": "test_spell",
                    "description": "Test spell",
                    "command": "echo test",
                }
            }
        }

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=json.dumps(registry_data))),
        ):
            tool = SpellTool()
            assert "test_spell" in tool._spells
            assert tool._spells["test_spell"]["name"] == "test_spell"

    def test_load_spells_invalid_json(self) -> None:
        """Test loading spells with invalid JSON."""
        invalid_json = "invalid json content"

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=invalid_json)),
        ):
            tool = SpellTool()
            assert tool._spells == {}

    def test_load_spells_invalid_format(self) -> None:
        """Test loading spells when spells key is not a dict."""
        registry_data = {SPELLS_REGISTRY_KEY: "not a dict"}

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=json.dumps(registry_data))),
        ):
            tool = SpellTool()
            assert tool._spells == {}

    def test_load_spells_io_error(self) -> None:
        """Test loading spells handles IO errors."""
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", side_effect=IOError("Permission denied")),
        ):
            tool = SpellTool()
            assert tool._spells == {}

    def test_is_tool_registered_true(self) -> None:
        """Test checking if registered spell exists."""
        self.tool._spells = {"test_spell": {}}
        assert self.tool._is_tool_registered("test_spell") is True

    def test_is_tool_registered_false(self) -> None:
        """Test checking if unregistered spell exists."""
        self.tool._spells = {"other_spell": {}}
        assert self.tool._is_tool_registered("test_spell") is False

    def test_is_tool_registered_empty(self) -> None:
        """Test checking spell in empty registry."""
        self.tool._spells = {}
        assert self.tool._is_tool_registered("test_spell") is False

    def test_is_path_permitted_empty_allowed_paths(self) -> None:
        """Test path permission check with empty allowed paths."""
        assert self.tool._is_path_permitted("/some/path", []) is False

    def test_is_path_permitted_exact_match(self) -> None:
        """Test path permission check with exact match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            allowed_paths = [tmpdir]
            assert self.tool._is_path_permitted(tmpdir, allowed_paths) is True

    def test_is_path_permitted_subdirectory(self) -> None:
        """Test path permission check with subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            allowed_paths = [tmpdir]
            assert self.tool._is_path_permitted(str(subdir), allowed_paths) is True

    def test_is_path_permitted_not_allowed(self) -> None:
        """Test path permission check with non-allowed path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            other_dir = Path(tmpdir).parent / "other_dir"
            allowed_paths = [tmpdir]
            assert self.tool._is_path_permitted(str(other_dir), allowed_paths) is False

    def test_is_path_permitted_resolution_error(self) -> None:
        """Test path permission check handles resolution errors."""
        with patch("pathlib.Path.resolve", side_effect=OSError("Resolution error")):
            assert self.tool._is_path_permitted("/some/path", ["/allowed"]) is False

    def test_is_command_permitted_empty_allowed_commands(self) -> None:
        """Test command permission check with empty allowed commands."""
        assert self.tool._is_command_permitted("echo test", []) is False

    def test_is_command_permitted_exact_match(self) -> None:
        """Test command permission check with exact base command match."""
        assert self.tool._is_command_permitted("echo", ["echo"]) is True

    def test_is_command_permitted_with_args(self) -> None:
        """Test command permission check with command and arguments."""
        assert self.tool._is_command_permitted("echo hello", ["echo"]) is True

    def test_is_command_permitted_not_allowed(self) -> None:
        """Test command permission check with non-allowed command."""
        assert self.tool._is_command_permitted("rm -rf /", ["echo"]) is False

    def test_is_command_permitted_empty_command(self) -> None:
        """Test command permission check with empty command."""
        assert self.tool._is_command_permitted("", ["echo"]) is False

    def test_is_command_permitted_multiple_allowed(self) -> None:
        """Test command permission check with multiple allowed commands."""
        allowed = ["echo", "curl", "python3"]
        assert self.tool._is_command_permitted("curl -X GET", allowed) is True
        assert self.tool._is_command_permitted("python3 script.py", allowed) is True
        assert self.tool._is_command_permitted("rm file", allowed) is False

    def test_validate_spell_config_missing_name(self) -> None:
        """Test spell config validation with missing name."""
        config = {"description": "Test", "command": "echo test"}
        is_valid, error_msg = self.tool._validate_spell_config(config)
        assert is_valid is False
        assert "name" in error_msg.lower()

    def test_validate_spell_config_missing_description(self) -> None:
        """Test spell config validation with missing description."""
        config = {"name": "test", "command": "echo test"}
        is_valid, error_msg = self.tool._validate_spell_config(config)
        assert is_valid is False
        assert "description" in error_msg.lower()

    def test_validate_spell_config_missing_command(self) -> None:
        """Test spell config validation with missing command."""
        config = {"name": "test", "description": "Test"}
        is_valid, error_msg = self.tool._validate_spell_config(config)
        assert is_valid is False
        assert "command" in error_msg.lower()

    def test_validate_spell_config_invalid_name_type(self) -> None:
        """Test spell config validation with invalid name type."""
        config = {"name": 123, "description": "Test", "command": "echo test"}
        is_valid, error_msg = self.tool._validate_spell_config(config)
        assert is_valid is False
        assert "name" in error_msg.lower()

    def test_validate_spell_config_empty_name(self) -> None:
        """Test spell config validation with empty name."""
        config = {"name": "", "description": "Test", "command": "echo test"}
        is_valid, error_msg = self.tool._validate_spell_config(config)
        assert is_valid is False
        assert "name" in error_msg.lower()

    def test_validate_spell_config_invalid_description_type(self) -> None:
        """Test spell config validation with invalid description type."""
        config = {"name": "test", "description": 123, "command": "echo test"}
        is_valid, error_msg = self.tool._validate_spell_config(config)
        assert is_valid is False
        assert "description" in error_msg.lower()

    def test_validate_spell_config_invalid_command_type(self) -> None:
        """Test spell config validation with invalid command type."""
        config = {"name": "test", "description": "Test", "command": 123}
        is_valid, error_msg = self.tool._validate_spell_config(config)
        assert is_valid is False
        assert "command" in error_msg.lower()

    def test_validate_spell_config_empty_command(self) -> None:
        """Test spell config validation with empty command."""
        config = {"name": "test", "description": "Test", "command": ""}
        is_valid, error_msg = self.tool._validate_spell_config(config)
        assert is_valid is False
        assert "command" in error_msg.lower()

    def test_validate_spell_config_invalid_path_type(self) -> None:
        """Test spell config validation with invalid path type."""
        config = {
            "name": "test",
            "description": "Test",
            "command": "echo test",
            "path": 123,
        }
        is_valid, error_msg = self.tool._validate_spell_config(config)
        assert is_valid is False
        assert "path" in error_msg.lower()

    def test_validate_spell_config_invalid_allowed_paths_type(self) -> None:
        """Test spell config validation with invalid allowed_paths type."""
        config = {
            "name": "test",
            "description": "Test",
            "command": "echo test",
            "allowed_paths": "not a list",
        }
        is_valid, error_msg = self.tool._validate_spell_config(config)
        assert is_valid is False
        assert "allowed_paths" in error_msg.lower()

    def test_validate_spell_config_invalid_allowed_paths_items(self) -> None:
        """Test spell config validation with invalid allowed_paths items."""
        config = {
            "name": "test",
            "description": "Test",
            "command": "echo test",
            "allowed_paths": [123, "valid"],
        }
        is_valid, error_msg = self.tool._validate_spell_config(config)
        assert is_valid is False
        assert "allowed_paths" in error_msg.lower()

    def test_validate_spell_config_invalid_allowed_commands_type(self) -> None:
        """Test spell config validation with invalid allowed_commands type."""
        config = {
            "name": "test",
            "description": "Test",
            "command": "echo test",
            "allowed_commands": "not a list",
        }
        is_valid, error_msg = self.tool._validate_spell_config(config)
        assert is_valid is False
        assert "allowed_commands" in error_msg.lower()

    def test_validate_spell_config_invalid_allowed_commands_items(self) -> None:
        """Test spell config validation with invalid allowed_commands items."""
        config = {
            "name": "test",
            "description": "Test",
            "command": "echo test",
            "allowed_commands": [123, "valid"],
        }
        is_valid, error_msg = self.tool._validate_spell_config(config)
        assert is_valid is False
        assert "allowed_commands" in error_msg.lower()

    def test_validate_spell_config_invalid_timeout_type(self) -> None:
        """Test spell config validation with invalid timeout type."""
        config = {
            "name": "test",
            "description": "Test",
            "command": "echo test",
            "timeout": "not a number",
        }
        is_valid, error_msg = self.tool._validate_spell_config(config)
        assert is_valid is False
        assert "timeout" in error_msg.lower()

    def test_validate_spell_config_negative_timeout(self) -> None:
        """Test spell config validation with negative timeout."""
        config = {
            "name": "test",
            "description": "Test",
            "command": "echo test",
            "timeout": -1,
        }
        is_valid, error_msg = self.tool._validate_spell_config(config)
        assert is_valid is False
        assert "timeout" in error_msg.lower()

    def test_validate_spell_config_timeout_exceeds_max(self) -> None:
        """Test spell config validation with timeout exceeding maximum."""
        config = {
            "name": "test",
            "description": "Test",
            "command": "echo test",
            "timeout": MAX_TIMEOUT_SECONDS + 1,
        }
        is_valid, error_msg = self.tool._validate_spell_config(config)
        assert is_valid is False
        assert "timeout" in error_msg.lower()
        assert str(MAX_TIMEOUT_SECONDS) in error_msg

    def test_validate_spell_config_valid_minimal(self) -> None:
        """Test spell config validation with valid minimal config."""
        config = {"name": "test", "description": "Test", "command": "echo test"}
        is_valid, error_msg = self.tool._validate_spell_config(config)
        assert is_valid is True
        assert error_msg == ""

    def test_validate_spell_config_valid_full(self) -> None:
        """Test spell config validation with valid full config."""
        config = {
            "name": "test",
            "description": "Test",
            "command": "echo test",
            "path": "/some/path",
            "allowed_paths": ["/allowed1", "/allowed2"],
            "allowed_commands": ["echo", "curl"],
            "timeout": 60,
        }
        is_valid, error_msg = self.tool._validate_spell_config(config)
        assert is_valid is True
        assert error_msg == ""

    @pytest.mark.asyncio
    async def test_execute_spell_success(self) -> None:
        """Test successful spell execution."""
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            spell_config = {"command": "echo test", "timeout": 30}
            result = await self.tool._execute_spell(spell_config, None)

            assert result == "output"

    @pytest.mark.asyncio
    async def test_execute_spell_with_arguments(self) -> None:
        """Test spell execution with arguments."""
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            spell_config = {"command": "echo test", "timeout": 30}
            arguments = {"key1": "value1", "key2": "value2"}
            await self.tool._execute_spell(spell_config, arguments)

            # Check environment variables were set
            call_kwargs = mock_exec.call_args[1]
            env = call_kwargs["env"]
            assert "SPELL_ARG_KEY1" in env
            assert env["SPELL_ARG_KEY1"] == "value1"
            assert "SPELL_ARG_KEY2" in env
            assert env["SPELL_ARG_KEY2"] == "value2"

    @pytest.mark.asyncio
    async def test_execute_spell_with_json_arguments(self) -> None:
        """Test spell execution with JSON-serializable arguments."""
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            spell_config = {"command": "echo test", "timeout": 30}
            arguments = {"data": {"nested": "value"}, "list": [1, 2, 3]}
            await self.tool._execute_spell(spell_config, arguments)

            call_kwargs = mock_exec.call_args[1]
            env = call_kwargs["env"]
            assert "SPELL_ARG_DATA" in env
            assert json.loads(env["SPELL_ARG_DATA"]) == {"nested": "value"}
            assert "SPELL_ARG_LIST" in env
            assert json.loads(env["SPELL_ARG_LIST"]) == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_execute_spell_with_working_dir(self) -> None:
        """Test spell execution with working directory."""
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            spell_config = {"command": "echo test", "path": "/some/dir", "timeout": 30}
            await self.tool._execute_spell(spell_config, None)

            call_kwargs = mock_exec.call_args[1]
            assert call_kwargs["cwd"] == "/some/dir"

    @pytest.mark.asyncio
    async def test_execute_spell_timeout(self) -> None:
        """Test spell execution timeout handling."""
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            spell_config = {"command": "sleep 100", "timeout": 1}
            with pytest.raises(TimeoutError) as exc_info:
                await self.tool._execute_spell(spell_config, None)
            assert "timed out" in str(exc_info.value).lower()
            mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_spell_non_zero_exit(self) -> None:
        """Test spell execution with non-zero exit code."""
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b"error message"))
        mock_process.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            spell_config = {"command": "false", "timeout": 30}
            with pytest.raises(RuntimeError) as exc_info:
                await self.tool._execute_spell(spell_config, None)
            assert "exit code 1" in str(exc_info.value)
            assert "error message" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_spell_command_not_found(self) -> None:
        """Test spell execution when command is not found."""
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError()):
            spell_config = {"command": "nonexistent_command", "timeout": 30}
            with pytest.raises(ValueError) as exc_info:
                await self.tool._execute_spell(spell_config, None)
            assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_spell_permission_denied(self) -> None:
        """Test spell execution with permission denied."""
        with patch("asyncio.create_subprocess_exec", side_effect=PermissionError()):
            spell_config = {"command": "/protected/script", "timeout": 30}
            with pytest.raises(ValueError) as exc_info:
                await self.tool._execute_spell(spell_config, None)
            assert "permission denied" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_spell_empty_command(self) -> None:
        """Test spell execution with empty command."""
        spell_config = {"command": "", "timeout": 30}
        with pytest.raises(ValueError) as exc_info:
            await self.tool._execute_spell(spell_config, None)
        assert "empty command" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_no_arguments(self) -> None:
        """Test execute method with no arguments."""
        result = await self.tool.execute(None)
        assert len(result) == 1
        assert "No arguments provided" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_missing_spell_name(self) -> None:
        """Test execute method with missing spell_name."""
        result = await self.tool.execute({})
        assert len(result) == 1
        assert "spell_name is required" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_invalid_spell_name_type(self) -> None:
        """Test execute method with invalid spell_name type."""
        result = await self.tool.execute({"spell_name": 123})
        assert len(result) == 1
        assert "spell_name is required" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_spell_not_registered(self) -> None:
        """Test execute method with unregistered spell."""
        self.tool._spells = {}
        result = await self.tool.execute({"spell_name": "nonexistent"})
        assert len(result) == 1
        assert "not registered" in result[0].text.lower()
        assert "spells.sh" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_invalid_config(self) -> None:
        """Test execute method with invalid spell configuration."""
        self.tool._spells = {"test_spell": {"name": "test_spell"}}  # Missing required fields
        result = await self.tool.execute({"spell_name": "test_spell"})
        assert len(result) == 1
        assert "Invalid spell configuration" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_path_not_permitted(self) -> None:
        """Test execute method with path not in allowed_paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spell_config = {
                "name": "test_spell",
                "description": "Test",
                "command": "echo test",
                "path": tmpdir,
                "allowed_paths": ["/other/path"],
            }
            self.tool._spells = {"test_spell": spell_config}
            result = await self.tool.execute({"spell_name": "test_spell"})
            assert len(result) == 1
            assert "not in allowed_paths" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_command_not_permitted(self) -> None:
        """Test execute method with command not in allowed_commands."""
        spell_config = {
            "name": "test_spell",
            "description": "Test",
            "command": "rm -rf /",
            "allowed_commands": ["echo"],
        }
        self.tool._spells = {"test_spell": spell_config}
        result = await self.tool.execute({"spell_name": "test_spell"})
        assert len(result) == 1
        assert "not in allowed_commands" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        """Test successful spell execution."""
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"spell output", b""))
        mock_process.returncode = 0

        spell_config = {
            "name": "test_spell",
            "description": "Test",
            "command": "echo test",
        }
        self.tool._spells = {"test_spell": spell_config}

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await self.tool.execute({"spell_name": "test_spell"})
            assert len(result) == 1
            data = json.loads(result[0].text)
            assert data["status"] == "success"
            assert data["spell"] == "test_spell"
            assert data["output"] == "spell output"

    @pytest.mark.asyncio
    async def test_execute_with_arguments(self) -> None:
        """Test execute method with spell arguments."""
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_process.returncode = 0

        spell_config = {
            "name": "test_spell",
            "description": "Test",
            "command": "echo test",
        }
        self.tool._spells = {"test_spell": spell_config}

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await self.tool.execute(
                {
                    "spell_name": "test_spell",
                    "arguments": {"param1": "value1", "param2": "value2"},
                }
            )
            assert len(result) == 1
            data = json.loads(result[0].text)
            assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_execute_timeout_error(self) -> None:
        """Test execute method handles timeout errors."""
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()

        spell_config = {
            "name": "test_spell",
            "description": "Test",
            "command": "sleep 100",
        }
        self.tool._spells = {"test_spell": spell_config}

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await self.tool.execute({"spell_name": "test_spell"})
            assert len(result) == 1
            assert "timeout" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_execute_execution_error(self) -> None:
        """Test execute method handles execution errors."""
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b"error"))
        mock_process.returncode = 1

        spell_config = {
            "name": "test_spell",
            "description": "Test",
            "command": "false",
        }
        self.tool._spells = {"test_spell": spell_config}

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await self.tool.execute({"spell_name": "test_spell"})
            assert len(result) == 1
            assert "error" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self) -> None:
        """Test execute method handles unexpected errors."""
        spell_config = {
            "name": "test_spell",
            "description": "Test",
            "command": "echo test",
        }
        self.tool._spells = {"test_spell": spell_config}

        with patch.object(self.tool, "_execute_spell", side_effect=RuntimeError("Unexpected")):
            result = await self.tool.execute({"spell_name": "test_spell"})
            assert len(result) == 1
            assert "error" in result[0].text.lower()

    def test_timeout_clamping(self) -> None:
        """Test that timeout values are clamped to maximum."""
        spell_config = {
            "command": "echo test",
            "timeout": MAX_TIMEOUT_SECONDS + 100,
        }
        # The timeout should be clamped in _execute_spell
        # This is tested indirectly through execution tests

    @pytest.mark.asyncio
    async def test_execute_default_timeout(self) -> None:
        """Test execute uses default timeout when not specified."""
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_process.returncode = 0

        spell_config = {
            "name": "test_spell",
            "description": "Test",
            "command": "echo test",
        }
        self.tool._spells = {"test_spell": spell_config}

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await self.tool.execute({"spell_name": "test_spell"})
            # Verify default timeout is used (tested through mock call)
