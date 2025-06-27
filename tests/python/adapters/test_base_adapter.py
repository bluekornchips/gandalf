"""
Tests for base adapter interface.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from src.adapters.base import IDEAdapter


class MockIDEAdapter(IDEAdapter):
    """Mock implementation of IDEAdapter for testing."""

    def __init__(self, project_root=None, ide_name="mock-ide"):
        super().__init__(project_root)
        self._ide_name = ide_name
        self._detected = True
        self._workspace_folders = []
        self._conversation_tools = {}
        self._conversation_handlers = {}
        self._config_paths = {}
        self._has_databases = True

    @property
    def ide_name(self) -> str:
        return self._ide_name

    def detect_ide(self) -> bool:
        return self._detected

    def get_workspace_folders(self):
        return self._workspace_folders

    def resolve_project_root(self, explicit_root=None):
        if explicit_root:
            return Path(explicit_root)
        return self.project_root or Path.cwd()

    def get_conversation_tools(self):
        return self._conversation_tools

    def get_conversation_handlers(self):
        return self._conversation_handlers

    def get_configuration_paths(self):
        """Mock implementation of get_configuration_paths."""
        return getattr(self, "_config_paths", {})

    def detect_conversation_databases(self):
        """Mock implementation of detect_conversation_databases."""
        return getattr(self, "_has_databases", True)


class TestIDEAdapterInterface:
    """Test the IDEAdapter abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that IDEAdapter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            IDEAdapter()

    def test_mock_adapter_instantiation(self):
        """Test that mock adapter can be instantiated."""
        adapter = MockIDEAdapter()
        assert isinstance(adapter, IDEAdapter)
        assert adapter.ide_name == "mock-ide"

    def test_adapter_with_project_root(self):
        """Test adapter initialization with project root."""
        project_root = Path("/loth/lorien")
        adapter = MockIDEAdapter(project_root=project_root)
        assert adapter.project_root == project_root

    def test_adapter_without_project_root(self):
        """Test adapter initialization without project root."""
        adapter = MockIDEAdapter()
        assert adapter.project_root is None

    def test_detected_ide_property(self):
        """Test the _detected_ide property initialization."""
        adapter = MockIDEAdapter()
        assert adapter._detected_ide is None


class TestIDEAdapterAbstractMethods:
    """Test that all abstract methods are properly defined."""

    def test_ide_name_is_abstract(self):
        """Test that ide_name property is abstract."""
        # This is tested by the fact that MockIDEAdapter must implement it
        adapter = MockIDEAdapter(ide_name="helms-deep")
        assert adapter.ide_name == "helms-deep"

    def test_detect_ide_is_abstract(self):
        """Test that detect_ide method is abstract."""
        adapter = MockIDEAdapter()
        adapter._detected = False
        assert not adapter.detect_ide()

        adapter._detected = True
        assert adapter.detect_ide()

    def test_get_workspace_folders_is_abstract(self):
        """Test that get_workspace_folders method is abstract."""
        adapter = MockIDEAdapter()
        test_folders = [Path("/road/to/helms/deep"), Path("/khazad/dum")]
        adapter._workspace_folders = test_folders
        assert adapter.get_workspace_folders() == test_folders

    def test_resolve_project_root_is_abstract(self):
        """Test that resolve_project_root method is abstract."""
        adapter = MockIDEAdapter()

        # Test with explicit root
        explicit_root = "/road/to/helms/deep"
        result = adapter.resolve_project_root(explicit_root)
        assert result == Path(explicit_root)

        # Test without explicit root, with project_root set
        project_root = Path("/fangorne/forest")
        adapter.project_root = project_root
        result = adapter.resolve_project_root()
        assert result == project_root

    def test_get_conversation_tools_is_abstract(self):
        """Test that get_conversation_tools method is abstract."""
        adapter = MockIDEAdapter()
        test_tools = {"tool1": {"name": "tool1"}, "tool2": {"name": "tool2"}}
        adapter._conversation_tools = test_tools
        assert adapter.get_conversation_tools() == test_tools

    def test_get_conversation_handlers_is_abstract(self):
        """Test that get_conversation_handlers method is abstract."""
        adapter = MockIDEAdapter()
        test_handlers = {"handler1": Mock(), "handler2": Mock()}
        adapter._conversation_handlers = test_handlers
        assert adapter.get_conversation_handlers() == test_handlers

    def test_get_configuration_paths_is_abstract(self):
        """Test that get_configuration_paths method is abstract."""
        adapter = MockIDEAdapter()
        test_paths = {"config": Path("/config"), "data": Path("/data")}
        adapter._config_paths = test_paths
        assert adapter.get_configuration_paths() == test_paths


class TestIDEAdapterConcreteMethod:
    """Test concrete methods provided by IDEAdapter."""

    def test_supports_conversations_with_tools(self):
        """Test supports_conversations returns True when tools are available."""
        adapter = MockIDEAdapter()
        adapter._conversation_tools = {"tool1": {"name": "tool1"}}
        assert adapter.supports_conversations() is True

    def test_supports_conversations_without_tools(self):
        """Test supports_conversations returns False when no tools available."""
        adapter = MockIDEAdapter()
        adapter._conversation_tools = {}
        assert adapter.supports_conversations() is False

    def test_get_environment_info_complete(self):
        """Test get_environment_info with complete data."""
        project_root = Path("/fangorne/forest")
        adapter = MockIDEAdapter(
            project_root=project_root, ide_name="helms-deep"
        )
        adapter._detected = True
        adapter._workspace_folders = [
            Path("/road/to/helms/deep"),
            Path("/khazad/dum"),
        ]
        adapter._conversation_tools = {"tool1": {"name": "tool1"}}

        env_info = adapter.get_environment_info()

        expected = {
            "ide_name": "helms-deep",
            "detected": True,
            "project_root": str(project_root),
            "workspace_folders": ["/road/to/helms/deep", "/khazad/dum"],
            "supports_conversations": True,
        }

        assert env_info == expected

    def test_get_environment_info_minimal(self):
        """Test get_environment_info with minimal data."""
        adapter = MockIDEAdapter()
        adapter._detected = False
        adapter._workspace_folders = []
        adapter._conversation_tools = {}

        env_info = adapter.get_environment_info()

        expected = {
            "ide_name": "mock-ide",
            "detected": False,
            "project_root": None,
            "workspace_folders": [],
            "supports_conversations": False,
        }

        assert env_info == expected

    def test_get_environment_info_with_none_project_root(self):
        """Test get_environment_info when project_root is None."""
        adapter = MockIDEAdapter(project_root=None)
        env_info = adapter.get_environment_info()
        assert env_info["project_root"] is None


class TestIDEAdapterInheritance:
    """Test inheritance behavior of IDEAdapter."""

    def test_subclass_must_implement_all_abstract_methods(self):
        """Test that subclass must implement all abstract methods."""

        class IncompleteAdapter(IDEAdapter):
            """Incomplete adapter missing some abstract methods."""

            @property
            def ide_name(self):
                return "incomplete"

            def detect_ide(self):
                return True

            # Missing other abstract methods

        with pytest.raises(TypeError):
            IncompleteAdapter()

    def test_multiple_inheritance_compatibility(self):
        """Test that adapter works with multiple inheritance."""

        class MixinClass:
            def extra_method(self):
                return "extra"

        class MultiInheritanceAdapter(MockIDEAdapter, MixinClass):
            pass

        adapter = MultiInheritanceAdapter()
        assert adapter.ide_name == "mock-ide"
        assert adapter.extra_method() == "extra"


class TestIDEAdapterEdgeCases:
    """Test edge cases and error conditions."""

    def test_adapter_with_invalid_project_root_type(self):
        """Test adapter behavior with invalid project root type."""
        # The adapter should handle this gracefully
        adapter = MockIDEAdapter(project_root="string_path")
        assert adapter.project_root == "string_path"

    def test_workspace_folders_empty_list(self):
        """Test workspace folders with empty list."""
        adapter = MockIDEAdapter()
        adapter._workspace_folders = []
        assert adapter.get_workspace_folders() == []

    def test_conversation_tools_empty_dict(self):
        """Test conversation tools with empty dict."""
        adapter = MockIDEAdapter()
        adapter._conversation_tools = {}
        assert adapter.get_conversation_tools() == {}
        assert not adapter.supports_conversations()

    def test_configuration_paths_empty_dict(self):
        """Test configuration paths with empty dict."""
        adapter = MockIDEAdapter()
        adapter._config_paths = {}
        assert adapter.get_configuration_paths() == {}
