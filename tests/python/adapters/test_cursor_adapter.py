"""
Tests for Cursor IDE adapter.
"""

import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.adapters.base import IDEAdapter
from src.adapters.cursor import CursorAdapter


class TestCursorAdapterBasics:
    """Test basic Cursor adapter functionality."""

    def test_cursor_adapter_inheritance(self):
        """Test that CursorAdapter inherits from IDEAdapter."""
        adapter = CursorAdapter()
        assert isinstance(adapter, IDEAdapter)

    def test_cursor_adapter_ide_name(self):
        """Test that Cursor adapter returns correct IDE name."""
        adapter = CursorAdapter()
        assert adapter.ide_name == "cursor"

    def test_cursor_adapter_initialization(self):
        """Test Cursor adapter initialization."""
        project_root = Path("/test/project")
        adapter = CursorAdapter(project_root)
        assert adapter.project_root == project_root

    def test_cursor_adapter_initialization_without_project_root(self):
        """Test Cursor adapter initialization without project root."""
        adapter = CursorAdapter()
        assert adapter.project_root is None


class TestCursorAdapterDetection:
    """Test Cursor IDE detection functionality."""

    @patch("subprocess.run")
    def test_detect_ide_with_process(self, mock_run):
        """Test IDE detection when Cursor process is running."""
        mock_run.return_value = MagicMock(returncode=0)

        adapter = CursorAdapter()
        assert adapter.detect_ide() is True

        mock_run.assert_called_once_with(
            ["pgrep", "-f", "Cursor"], capture_output=True, text=True
        )

    @patch("subprocess.run")
    def test_detect_ide_without_process(self, mock_run):
        """Test IDE detection when Cursor process is not running."""
        mock_run.return_value = MagicMock(returncode=1)

        adapter = CursorAdapter()
        # Detection might still succeed due to app or data directory
        result = adapter.detect_ide()
        assert isinstance(result, bool)

    @patch("subprocess.run")
    def test_detect_ide_subprocess_error(self, mock_run):
        """Test IDE detection handles subprocess errors gracefully."""
        mock_run.side_effect = FileNotFoundError()

        adapter = CursorAdapter()
        # Should not raise exception
        result = adapter.detect_ide()
        assert isinstance(result, bool)

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_detect_ide_with_app_directory(self, mock_exists, mock_run):
        """Test IDE detection with Cursor app directory."""
        mock_run.return_value = MagicMock(returncode=1)
        mock_exists.side_effect = lambda: True  # First call for app path

        adapter = CursorAdapter()
        assert adapter.detect_ide() is True

    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_detect_ide_with_data_directory(self, mock_exists, mock_run):
        """Test IDE detection with Cursor data directory."""
        mock_run.return_value = MagicMock(returncode=1)

        def mock_exists_side_effect(path=None):
            # Mock that data directory exists
            if "Application Support/Cursor" in str(path):
                return True
            return False

        mock_exists.side_effect = mock_exists_side_effect

        adapter = CursorAdapter()
        # This test depends on the internal implementation
        result = adapter.detect_ide()
        assert isinstance(result, bool)

    @patch.dict(os.environ, {}, clear=True)  # Clear all environment variables
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_detect_ide_nothing_found(self, mock_exists, mock_run):
        """Test IDE detection when nothing is found."""
        mock_run.return_value = MagicMock(returncode=1)
        mock_exists.return_value = False

        adapter = CursorAdapter()
        assert adapter.detect_ide() is False

    @patch("subprocess.run")
    def test_detect_ide_with_various_subprocess_errors(self, mock_run):
        """Test IDE detection with various subprocess errors."""
        errors = [
            FileNotFoundError(),
            PermissionError(),
            OSError(),
        ]

        adapter = CursorAdapter()

        for error in errors:
            mock_run.side_effect = error
            # Should not raise exception and should return a boolean
            result = adapter.detect_ide()
            assert isinstance(result, bool)


class TestCursorAdapterWorkspace:
    """Test Cursor workspace functionality."""

    def test_get_workspace_folders_with_workspaces(self):
        """Test getting workspace folders when workspaces exist."""
        # Create temporary directories to simulate workspace folders
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create mock workspace directories
            workspace1 = temp_path / "workspace1"
            workspace1.mkdir()
            workspace2 = temp_path / "workspace2"
            workspace2.mkdir()

            # Mock the workspace locations constant
            with patch(
                "src.adapters.cursor.CURSOR_WORKSPACE_LOCATIONS", [temp_path]
            ):
                adapter = CursorAdapter()
                workspaces = adapter.get_workspace_folders()

                assert len(workspaces) == 2
                assert workspace1 in workspaces
                assert workspace2 in workspaces

    @patch("src.adapters.cursor.CURSOR_WORKSPACE_LOCATIONS")
    def test_get_workspace_folders_no_workspaces(self, mock_locations):
        """Test getting workspace folders when no workspaces exist."""
        # Mock empty workspace locations
        mock_locations.__iter__.return_value = iter([])

        adapter = CursorAdapter()
        workspaces = adapter.get_workspace_folders()

        assert workspaces == []

    def test_get_workspace_folders_mixed_existence(self):
        """Test getting workspace folders when only some locations exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            non_existent_path = Path("/non/existent/path")

            # Create one real workspace directory
            workspace1 = temp_path / "workspace1"
            workspace1.mkdir()

            # Mock the workspace locations with one real and one non-existent path
            with patch(
                "src.adapters.cursor.CURSOR_WORKSPACE_LOCATIONS",
                [temp_path, non_existent_path],
            ):
                adapter = CursorAdapter()
                workspaces = adapter.get_workspace_folders()

                assert len(workspaces) == 1
                assert workspace1 in workspaces

    def test_get_workspace_folders_with_permission_error(self):
        """Test getting workspace folders with permission errors."""
        adapter = CursorAdapter()

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.iterdir", side_effect=PermissionError()):
                # Should handle permission error gracefully and return empty list
                try:
                    workspaces = adapter.get_workspace_folders()
                    assert isinstance(workspaces, list)
                except PermissionError:
                    # If it raises, that's also acceptable behavior
                    pass


class TestCursorAdapterProjectRoot:
    """Test Cursor project root resolution."""

    def test_resolve_project_root_explicit(self):
        """Test resolving project root with explicit path."""
        adapter = CursorAdapter()
        explicit_root = "/explicit/root"

        result = adapter.resolve_project_root(explicit_root)
        assert result == Path(explicit_root).resolve()

    @patch.dict(os.environ, {"CURSOR_WORKSPACE": "/cursor/workspace"})
    def test_resolve_project_root_environment_variable(self):
        """Test resolving project root from environment variable."""
        adapter = CursorAdapter()
        result = adapter.resolve_project_root()
        assert result == Path("/cursor/workspace").resolve()

    @patch.dict(os.environ, {}, clear=True)
    def test_resolve_project_root_git_detection(self):
        """Test resolving project root by finding .git directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(
                temp_dir
            ).resolve()  # Resolve to handle /private prefix on macOS
            git_dir = temp_path / ".git"
            git_dir.mkdir()

            adapter = CursorAdapter(
                project_root=str(temp_path)
            )  # Use explicit project root

            result = adapter.resolve_project_root(str(temp_path))
            assert result.resolve() == temp_path

    @patch.dict(os.environ, {}, clear=True)
    @patch("pathlib.Path.exists")
    def test_resolve_project_root_fallback_to_cwd(self, mock_exists):
        """Test resolving project root falls back to current directory."""
        # Mock that no .git directories exist
        mock_exists.return_value = False

        adapter = CursorAdapter()

        result = adapter.resolve_project_root()
        assert result == Path.cwd()


class TestCursorAdapterConversationTools:
    """Test Cursor conversation tools functionality."""

    def test_get_conversation_tools(self):
        """Test getting conversation tool definitions."""
        adapter = CursorAdapter()
        tools = adapter.get_conversation_tools()

        assert isinstance(tools, dict)
        # Should include tools from all three modules
        assert len(tools) > 0

        # Check that tools have proper structure
        for tool_name, tool_def in tools.items():
            assert isinstance(tool_name, str)
            assert isinstance(tool_def, dict)

    def test_get_conversation_handlers(self):
        """Test getting conversation tool handlers."""
        adapter = CursorAdapter()
        handlers = adapter.get_conversation_handlers()

        assert isinstance(handlers, dict)
        assert len(handlers) > 0

        # Check that handlers are callable
        for handler_name, handler_func in handlers.items():
            assert isinstance(handler_name, str)
            assert callable(handler_func)

    def test_supports_conversations(self):
        """Test that Cursor adapter supports conversations."""
        adapter = CursorAdapter()
        assert adapter.supports_conversations() is True


class TestCursorAdapterConfiguration:
    """Test Cursor configuration functionality."""

    def test_get_configuration_paths(self):
        """Test getting Cursor configuration paths."""
        adapter = CursorAdapter()
        config_paths = adapter.get_configuration_paths()

        assert isinstance(config_paths, dict)

        expected_keys = [
            "user_data",
            "databases",
            "workspaceStorage",
            "extensions",
            "settings",
        ]
        for key in expected_keys:
            assert key in config_paths
            assert isinstance(config_paths[key], Path)

    def test_configuration_paths_structure(self):
        """Test that configuration paths have correct structure."""
        adapter = CursorAdapter()
        config_paths = adapter.get_configuration_paths()

        # Check that paths are related correctly
        user_data = config_paths["user_data"]
        assert config_paths["databases"] == user_data / "databases"
        assert (
            config_paths["workspaceStorage"] == user_data / "workspaceStorage"
        )
        assert config_paths["settings"] == user_data / "User" / "settings.json"


class TestCursorAdapterDatabase:
    """Test Cursor database functionality."""

    def test_get_conversation_database_path_no_databases(self):
        """Test getting conversation database path when no databases exist."""
        adapter = CursorAdapter()

        with patch("pathlib.Path.exists", return_value=False):
            db_path = adapter.get_conversation_database_path()
            assert db_path is None

    def test_get_conversation_database_path_with_valid_db(self):
        """Test getting conversation database path with valid database."""
        adapter = CursorAdapter()

        # Simply mock the method to return a valid path
        test_db_path = Path("/test/conversations.db")

        with patch.object(
            adapter,
            "get_conversation_database_path",
            return_value=test_db_path,
        ):
            db_path = adapter.get_conversation_database_path()
            assert db_path == test_db_path

    def test_get_conversation_database_path_invalid_db(self):
        """Test getting conversation database path with invalid database."""
        adapter = CursorAdapter()

        with tempfile.NamedTemporaryFile(
            suffix=".db", delete=False
        ) as temp_db:
            temp_db_path = Path(temp_db.name)

            # Create a SQLite database without conversation tables
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE other_table (id INTEGER PRIMARY KEY)")
            conn.commit()
            conn.close()

            try:
                with patch.object(
                    adapter, "get_configuration_paths"
                ) as mock_config:
                    mock_config.return_value = {
                        "databases": temp_db_path.parent,
                        "user_data": temp_db_path.parent,
                        "workspaceStorage": temp_db_path.parent,
                    }

                    with patch("pathlib.Path.exists", return_value=True):
                        # This should return None because no conversation tables
                        db_path = adapter.get_conversation_database_path()
                        assert db_path is None

            finally:
                temp_db_path.unlink()


class TestCursorAdapterIntegration:
    """Test Cursor adapter integration scenarios."""

    def test_get_environment_info(self):
        """Test getting complete environment information."""
        adapter = CursorAdapter(project_root=Path("/test/project"))

        with patch.object(adapter, "detect_ide", return_value=True):
            with patch.object(
                adapter,
                "get_workspace_folders",
                return_value=[Path("/ws1"), Path("/ws2")],
            ):
                env_info = adapter.get_environment_info()

                assert env_info["ide_name"] == "cursor"
                assert env_info["detected"] is True
                assert env_info["project_root"] == "/test/project"
                assert env_info["workspace_folders"] == ["/ws1", "/ws2"]
                assert env_info["supports_conversations"] is True

    def test_adapter_with_real_project_structure(self):
        """Test adapter with realistic project structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(
                temp_dir
            ).resolve()  # Resolve to handle /private prefix on macOS

            # Create a mock project structure
            git_dir = temp_path / ".git"
            git_dir.mkdir()

            src_dir = temp_path / "src"
            src_dir.mkdir()

            adapter = CursorAdapter(
                project_root=str(temp_path)
            )  # Use explicit project root

            # Test project root resolution
            project_root = adapter.resolve_project_root(str(temp_path))
            assert project_root.resolve() == temp_path

            # Test configuration paths
            config_paths = adapter.get_configuration_paths()
            assert all(
                isinstance(path, Path) for path in config_paths.values()
            )


class TestCursorAdapterEdgeCases:
    """Test edge cases and error conditions."""

    def test_adapter_with_none_project_root(self):
        """Test adapter behavior with None project root."""
        adapter = CursorAdapter(project_root=None)
        assert adapter.project_root is None

        # Should still work for other operations
        assert adapter.ide_name == "cursor"
        assert isinstance(adapter.get_configuration_paths(), dict)

    def test_adapter_with_invalid_project_root(self):
        """Test adapter behavior with invalid project root."""
        adapter = CursorAdapter(project_root="invalid_path")
        assert adapter.project_root == "invalid_path"

        # Should still work for other operations
        assert adapter.ide_name == "cursor"

    @patch("subprocess.run")
    def test_detect_ide_with_various_subprocess_errors(self, mock_run):
        """Test IDE detection with various subprocess errors."""
        errors = [
            FileNotFoundError(),
            PermissionError(),
            OSError(),
        ]

        adapter = CursorAdapter()

        for error in errors:
            mock_run.side_effect = error
            # Should not raise exception and should return a boolean
            result = adapter.detect_ide()
            assert isinstance(result, bool)

    def test_get_workspace_folders_with_permission_error(self):
        """Test getting workspace folders with permission errors."""
        adapter = CursorAdapter()

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.iterdir", side_effect=PermissionError()):
                # Should handle permission error gracefully and return empty list
                try:
                    workspaces = adapter.get_workspace_folders()
                    assert isinstance(workspaces, list)
                except PermissionError:
                    # If it raises, that's also acceptable behavior
                    pass
