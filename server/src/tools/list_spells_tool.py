"""
Tool to list available spells without executing them.
"""

import json
from typing import Any, Dict, List

from src.tools.base_tool import BaseTool
from src.tools.spell_tool import SpellTool
from src.protocol.models import ToolResult
from src.utils.logger import log_error, log_info


class ListSpellsTool(BaseTool):
    """List all available spells."""

    @property
    def name(self) -> str:
        return "list_spells"

    @property
    def description(self) -> str:
        return "List available spells with descriptions and allowed paths"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, arguments: Dict[str, Any] | None) -> List[ToolResult]:
        log_info("ListSpells tool called")

        try:
            spell_tool = SpellTool()
            # Ensure spells are current
            spell_tool._load_spells()

            spells_summary = []
            for name, config in sorted(spell_tool._spells.items()):
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
        except Exception as e:
            error_msg = f"Unexpected error listing spells: {str(e)}"
            log_error(error_msg)
            return [ToolResult(text=f"Error: {error_msg}")]
