"""
Base tool class for all Gandalf tools.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from src.protocol.types import ToolDefinition, ToolResult


class BaseTool(ABC):
    """Base class for all tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def execute(self, arguments: Dict[str, Any] | None) -> List[ToolResult]:
        pass

    def get_tool_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name, description=self.description, input_schema=self.input_schema
        )
