"""Test suite for spell tool implementation."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from src.tools.spell_tool import SpellTool


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
        assert "spell" in self.tool.description.lower()

    def test_input_schema(self) -> None:
        """Test tool input schema structure."""
        schema = self.tool.input_schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "spell_name" in schema["properties"]
        assert "arguments" in schema["properties"]
        assert schema["required"] == ["spell_name"]

    def test_load_spells_directory_not_found(self) -> None:
        """Test loading spells when spells directory doesn't exist."""
        self.tool._spells = {}  # Clear spells loaded from init
        original_dir = self.tool._spells_directory
        self.tool._spells_directory = "nonexistent_dir"
        try:
            with patch(
                "src.tools.spell_tool._get_project_root", return_value=Path("/tmp")
            ):
                self.tool._load_spells()
                assert self.tool._spells == {}
        finally:
            self.tool._spells_directory = original_dir

    def test_load_spells_empty_directory(self) -> None:
        """Test loading spells from empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spells_dir = Path(tmpdir) / "spells"
            spells_dir.mkdir()

            with patch(
                "src.tools.spell_tool._get_project_root", return_value=Path(tmpdir)
            ):
                with patch.object(self.tool, "_spells_directory", "spells"):
                    self.tool._load_spells()
                    assert self.tool._spells == {}

    def test_load_spells_valid_yaml(self) -> None:
        """Test loading spells from valid YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spells_dir = Path(tmpdir) / "spells"
            spells_dir.mkdir()

            spell_file = spells_dir / "test-spell.yaml"
            spell_data = {
                "name": "test-spell",
                "description": "Test spell",
                "command": "echo test",
            }
            with open(spell_file, "w", encoding="utf-8") as f:
                yaml.dump(spell_data, f)

            with patch(
                "src.tools.spell_tool._get_project_root", return_value=Path(tmpdir)
            ):
                with patch.object(self.tool, "_spells_directory", "spells"):
                    self.tool._load_spells()
                    assert "test-spell" in self.tool._spells
                    assert self.tool._spells["test-spell"]["name"] == "test-spell"

    def test_load_spells_invalid_yaml(self) -> None:
        """Test loading spells with invalid YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spells_dir = Path(tmpdir) / "spells"
            spells_dir.mkdir()

            spell_file = spells_dir / "invalid.yaml"
            spell_file.write_text("invalid: yaml: content: [unclosed")

            with patch(
                "src.tools.spell_tool._get_project_root", return_value=Path(tmpdir)
            ):
                with patch.object(self.tool, "_spells_directory", "spells"):
                    self.tool._load_spells()
                    assert "invalid" not in self.tool._spells

    def test_load_spells_missing_name_field(self) -> None:
        """Test loading spell with missing name field."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spells_dir = Path(tmpdir) / "spells"
            spells_dir.mkdir()

            spell_file = spells_dir / "test.yaml"
            spell_data = {"description": "Test", "command": "echo test"}
            with open(spell_file, "w", encoding="utf-8") as f:
                yaml.dump(spell_data, f)

            with patch(
                "src.tools.spell_tool._get_project_root", return_value=Path(tmpdir)
            ):
                with patch.object(self.tool, "_spells_directory", "spells"):
                    self.tool._load_spells()
                    assert "test" not in self.tool._spells

    def test_load_spells_filename_as_name(self) -> None:
        """Test that filename is used as spell name when name doesn't match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spells_dir = Path(tmpdir) / "spells"
            spells_dir.mkdir()

            spell_file = spells_dir / "actual-name.yaml"
            spell_data = {
                "name": "different-name",
                "description": "Test",
                "command": "echo",
            }
            with open(spell_file, "w", encoding="utf-8") as f:
                yaml.dump(spell_data, f)

            with patch(
                "src.tools.spell_tool._get_project_root", return_value=Path(tmpdir)
            ):
                with patch.object(self.tool, "_spells_directory", "spells"):
                    self.tool._load_spells()
                    assert "actual-name" in self.tool._spells
                    assert self.tool._spells["actual-name"]["name"] == "actual-name"

    def test_load_spells_environment_variable_expansion(self) -> None:
        """Test that environment variables are expanded in YAML files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spells_dir = Path(tmpdir) / "spells"
            spells_dir.mkdir()

            spell_file = spells_dir / "test.yaml"
            spell_file.write_text(
                "name: test\ncommand: echo test\npaths:\n  - ${HOME}\nflags: []"
            )

            with patch(
                "src.tools.spell_tool._get_project_root", return_value=Path(tmpdir)
            ):
                with patch.object(self.tool, "_spells_directory", "spells"):
                    self.tool._load_spells()
                    assert "test" in self.tool._spells
                    assert (
                        os.path.expandvars("${HOME}")
                        in self.tool._spells["test"]["paths"]
                    )

    def test_load_spells_multiple_files(self) -> None:
        """Test loading multiple spell files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spells_dir = Path(tmpdir) / "spells"
            spells_dir.mkdir()

            for i in range(3):
                spell_file = spells_dir / f"spell{i}.yaml"
                spell_data = {
                    "name": f"spell{i}",
                    "description": f"Spell {i}",
                    "command": f"echo spell{i}",
                }
                with open(spell_file, "w", encoding="utf-8") as f:
                    yaml.dump(spell_data, f)

            with patch(
                "src.tools.spell_tool._get_project_root", return_value=Path(tmpdir)
            ):
                with patch.object(self.tool, "_spells_directory", "spells"):
                    self.tool._load_spells()
                    assert len(self.tool._spells) == 3
                    for i in range(3):
                        assert f"spell{i}" in self.tool._spells

    def test_load_spells_both_yaml_and_yml(self) -> None:
        """Test loading both .yaml and .yml files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spells_dir = Path(tmpdir) / "spells"
            spells_dir.mkdir()

            yaml_file = spells_dir / "spell1.yaml"
            yml_file = spells_dir / "spell2.yml"

            with open(yaml_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    {"name": "spell1", "description": "Test", "command": "echo"}, f
                )

            with open(yml_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    {"name": "spell2", "description": "Test", "command": "echo"}, f
                )

            with patch(
                "src.tools.spell_tool._get_project_root", return_value=Path(tmpdir)
            ):
                with patch.object(self.tool, "_spells_directory", "spells"):
                    self.tool._load_spells()
                    assert "spell1" in self.tool._spells
                    assert "spell2" in self.tool._spells

    def test_is_spell_registered_true(self) -> None:
        """Test checking if registered spell exists."""
        self.tool._spells = {"test_spell": {}}
        assert self.tool._is_spell_registered("test_spell") is True

    def test_is_spell_registered_false(self) -> None:
        """Test checking if unregistered spell exists."""
        self.tool._spells = {"other_spell": {}}
        assert self.tool._is_spell_registered("test_spell") is False

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

    def test_are_flags_permitted_empty_allowed(self) -> None:
        """Test flag permission check with empty allowed flags (no flags permitted)."""
        assert self.tool._are_flags_permitted([], []) is True
        assert self.tool._are_flags_permitted(["-a"], []) is False

    def test_are_flags_permitted_valid_flags(self) -> None:
        """Test flag permission check with valid flags."""
        assert self.tool._are_flags_permitted(["-a", "-l"], ["-a", "-l", "-h"]) is True
        assert self.tool._are_flags_permitted(["-a", "-x"], ["-a", "-l"]) is False

    def test_validate_spell_config_valid(self) -> None:
        """Test spell config validation with valid config."""
        config = {
            "name": "test",
            "description": "Test",
            "command": "echo test",
            "paths": ["/tmp"],
            "flags": [],
        }
        is_valid, error_msg = self.tool._validate_spell_config(config)
        assert is_valid is True
        assert error_msg == ""

    def test_validate_spell_config_missing_field(self) -> None:
        """Test spell config validation with missing required field."""
        config = {"name": "test", "description": "Test"}
        is_valid, error_msg = self.tool._validate_spell_config(config)
        assert is_valid is False
        assert "command" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_execute_spell_success(self) -> None:
        """Test successful spell execution."""
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_process.returncode = 0
        mock_process.wait = AsyncMock()

        self.tool._spells = {
            "test_spell": {
                "name": "test_spell",
                "description": "Test",
                "command": "echo test",
                "paths": ["/tmp"],
                "flags": [],
            }
        }

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await self.tool.execute({"spell_name": "test_spell"})
            assert len(result) == 1
            data = json.loads(result[0].text)
            assert data["status"] == "success"
            assert data["spell"] == "test_spell"

    @pytest.mark.asyncio
    async def test_execute_spell_not_found(self) -> None:
        """Test executing non-existent spell."""
        self.tool._spells = {}
        result = await self.tool.execute({"spell_name": "nonexistent"})
        assert len(result) == 1
        assert "not found" in result[0].text.lower()
        assert "spells/" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_execute_reloads_spells(self) -> None:
        """Test that execute reloads spells on each call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spells_dir = Path(tmpdir) / "spells"
            spells_dir.mkdir()

            spell_file = spells_dir / "dynamic.yaml"
            spell_data = {
                "name": "dynamic",
                "description": "Dynamic spell",
                "command": "echo dynamic",
                "paths": ["/tmp"],
                "flags": [],
            }
            with open(spell_file, "w", encoding="utf-8") as f:
                yaml.dump(spell_data, f)

            with patch(
                "src.tools.spell_tool._get_project_root", return_value=Path(tmpdir)
            ):
                with patch.object(self.tool, "_spells_directory", "spells"):
                    # First call should load the spell
                    mock_process = AsyncMock()
                    mock_process.communicate = AsyncMock(return_value=(b"output", b""))
                    mock_process.returncode = 0

                    with patch(
                        "asyncio.create_subprocess_exec", return_value=mock_process
                    ):
                        result = await self.tool.execute({"spell_name": "dynamic"})
                        assert len(result) == 1
                        data = json.loads(result[0].text)
                        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_os_commands_spell_loads_from_yaml(self) -> None:
        """Test that os-commands spell can be loaded from YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spells_dir = Path(tmpdir) / "spells"
            spells_dir.mkdir()

            spell_file = spells_dir / "os-commands.yaml"
            spell_data = {
                "name": "os-commands",
                "description": "Run basic OS commands (pwd, ls, whoami) in home directory",
                "command": "pwd",
                "paths": ["${HOME}"],
                "flags": [],
                "timeout": 10,
            }
            with open(spell_file, "w", encoding="utf-8") as f:
                yaml.dump(spell_data, f)

            tool = SpellTool()
            with patch(
                "src.tools.spell_tool._get_project_root", return_value=Path(tmpdir)
            ):
                with patch.object(tool, "_spells_directory", "spells"):
                    tool._load_spells()
                    assert "os-commands" in tool._spells
                    loaded_spell = tool._spells["os-commands"]
                    assert loaded_spell["name"] == "os-commands"
                    # Environment variables should be expanded
                    assert "${HOME}" not in loaded_spell["paths"][0]
                    assert os.path.expandvars("${HOME}") in loaded_spell["paths"]


class TestOSCommandsSpell:
    """Test suite for OS commands spell example loaded from YAML."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.tool = SpellTool()
        self.home_dir = str(Path.home())

        # Manually configure OS commands spell for testing
        # (In real usage, this would be loaded from spells/os-commands.yaml)
        self.tool._spells = {
            "os-commands": {
                "name": "os-commands",
                "description": "Run basic OS commands (pwd, ls, whoami) in home directory",
                "command": "pwd",
                "paths": [self.home_dir],
                "flags": [],
                "timeout": 10,
            }
        }

    @pytest.mark.asyncio
    async def test_os_commands_spell_loads_from_yaml(self) -> None:
        """Test that os-commands spell can be loaded from YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            spells_dir = Path(tmpdir) / "spells"
            spells_dir.mkdir()

            spell_file = spells_dir / "os-commands.yaml"
            spell_data = {
                "name": "os-commands",
                "description": "Run basic OS commands (pwd, ls, whoami) in home directory",
                "command": "pwd",
                "paths": ["${HOME}"],
                "flags": [],
                "timeout": 10,
            }
            with open(spell_file, "w", encoding="utf-8") as f:
                yaml.dump(spell_data, f)

            with patch(
                "src.tools.spell_tool._get_project_root", return_value=Path(tmpdir)
            ):
                tool = SpellTool()
                with patch.object(tool, "_spells_directory", "spells"):
                    tool._load_spells()
                    assert "os-commands" in tool._spells
                    loaded_spell = tool._spells["os-commands"]
                    assert loaded_spell["name"] == "os-commands"
                    # Environment variables should be expanded
                    assert "${HOME}" not in loaded_spell["paths"][0]
                    assert self.home_dir in loaded_spell["paths"]

    @pytest.mark.asyncio
    async def test_os_commands_spell_pwd_execution(self) -> None:
        """Test executing pwd command through os-commands spell."""
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(self.home_dir.encode(), b""))
        mock_process.returncode = 0

        with patch(
            "asyncio.create_subprocess_exec", return_value=mock_process
        ) as mock_exec:
            result = await self.tool.execute({"spell_name": "os-commands"})

            assert len(result) == 1
            data = json.loads(result[0].text)
            assert data["status"] == "success"
            assert data["spell"] == "os-commands"
            assert self.home_dir in data["output"]

            # Verify command was executed in home directory
            call_kwargs = mock_exec.call_args[1]
            assert call_kwargs["cwd"] == self.home_dir

    @pytest.mark.asyncio
    async def test_os_commands_spell_rejects_no_paths(self) -> None:
        """Test that os-commands spell rejects execution when no paths specified."""
        # Remove paths
        self.tool._spells["os-commands"]["paths"] = []

        # Prevent reload from overwriting our test config
        original_load = self.tool._load_spells
        setattr(self.tool, "_load_spells", lambda: None)
        try:
            result = await self.tool.execute({"spell_name": "os-commands"})
        finally:
            setattr(self.tool, "_load_spells", original_load)

        assert len(result) == 1
        assert "paths" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_os_commands_spell_validates_flags(self) -> None:
        """Test that os-commands spell validates flags in command."""
        # Try to use a command with disallowed flags
        self.tool._spells["os-commands"]["command"] = "pwd -P"
        self.tool._spells["os-commands"]["flags"] = []  # No flags allowed

        # Prevent reload from overwriting our test config
        original_load = self.tool._load_spells
        setattr(self.tool, "_load_spells", lambda: None)
        try:
            result = await self.tool.execute({"spell_name": "os-commands"})
        finally:
            setattr(self.tool, "_load_spells", original_load)

        assert len(result) == 1
        assert (
            "not permitted" in result[0].text.lower()
            or "error" in result[0].text.lower()
        )

    @pytest.mark.asyncio
    async def test_os_commands_spell_allows_subdirectory_of_home(self) -> None:
        """Test that os-commands spell allows subdirectories of home."""
        # Create a subdirectory path
        subdir = os.path.join(self.home_dir, "test_subdir")

        # Update spell to use subdirectory as first path (implementation uses first path)
        self.tool._spells["os-commands"]["paths"] = [subdir]

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(subdir.encode(), b""))
        mock_process.returncode = 0

        # Prevent reload from overwriting our test config
        original_load = self.tool._load_spells
        setattr(self.tool, "_load_spells", lambda: None)
        try:
            with patch(
                "asyncio.create_subprocess_exec", return_value=mock_process
            ) as mock_exec:
                result = await self.tool.execute({"spell_name": "os-commands"})

                assert len(result) == 1
                data = json.loads(result[0].text)
                assert data["status"] == "success"

                # Verify command was executed in subdirectory
                call_args = mock_exec.call_args
                # cwd is passed as a keyword argument
                assert call_args.kwargs["cwd"] == subdir
        finally:
            setattr(self.tool, "_load_spells", original_load)
