"""Tests for ListSpellsTool."""

import json
from unittest.mock import patch

import pytest

from src.tools.list_spells_tool import ListSpellsTool
from src.tools.spell_tool import SpellTool


class TestListSpellsTool:
    """Test suite for ListSpellsTool."""

    def setup_method(self) -> None:
        self.tool = ListSpellsTool()

    def test_metadata(self) -> None:
        """Tool exposes name/description/schema."""
        assert self.tool.name == "list_spells"
        assert "list" in self.tool.description.lower()
        schema = self.tool.input_schema
        assert schema["type"] == "object"
        assert schema["properties"] == {}
        assert schema["required"] == []

    @pytest.mark.asyncio
    async def test_lists_spells(self) -> None:
        """Lists spells with name/description/paths."""

        def fake_load(self: SpellTool) -> None:
            self._spells = {
                "demo": {
                    "name": "demo",
                    "description": "Demo spell",
                    "paths": ["/tmp"],
                    "command": "echo demo",
                }
            }

        with patch("src.tools.list_spells_tool.SpellTool._load_spells", fake_load):
            result = await self.tool.execute({})

        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert len(data["spells"]) == 1
        assert data["spells"][0]["name"] == "demo"
        assert data["spells"][0]["description"] == "Demo spell"
        assert data["spells"][0]["paths"] == ["/tmp"]

    @pytest.mark.asyncio
    async def test_lists_spells_empty(self) -> None:
        """Gracefully handles no spells."""

        def fake_load(self: SpellTool) -> None:
            self._spells = {}

        with patch("src.tools.list_spells_tool.SpellTool._load_spells", fake_load):
            result = await self.tool.execute({})

        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert data["spells"] == []
