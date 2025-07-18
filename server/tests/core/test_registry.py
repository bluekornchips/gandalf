"""
Tests for registry functionality.

Tests the simple registry reader for agentic tool installations.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.config.constants.agentic import (
    AGENTIC_TOOL_CLAUDE_CODE,
    AGENTIC_TOOL_CURSOR,
)
from src.core.registry import (
    find_claude_conversations,
    find_cursor_conversations,
    get_agentic_tool_path,
    get_all_conversations,
    get_registered_agentic_tools,
    get_registry_path,
    read_registry,
)


class TestRegistry(unittest.TestCase):
    """Test registry functionality for agentic tools."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_registry_data = {
            AGENTIC_TOOL_CURSOR: "/Users/frodo/Library/Application Support/Cursor",
            AGENTIC_TOOL_CLAUDE_CODE: "/Users/frodo/.claude",
        }

    def test_get_registry_path_default(self):
        """Test getting registry path returns GANDALF_HOME/registry.json."""
        result = get_registry_path()

        # Should return the GANDALF_HOME constant path with registry.json appended
        self.assertTrue(str(result).endswith("registry.json"))
        self.assertTrue("gandalf" in str(result).lower())

    def test_get_registry_path_custom(self):
        """Test getting registry path is consistent."""
        result1 = get_registry_path()
        result2 = get_registry_path()

        # Should return the same path consistently
        self.assertEqual(result1, result2)
        self.assertTrue(str(result1).endswith("registry.json"))

    @patch("src.core.registry.Path.exists")
    def test_read_registry_file_not_found(self, mock_exists):
        """Test reading registry when file doesn't exist."""
        mock_exists.return_value = False

        result = read_registry()

        self.assertEqual(result, {})

    @patch("src.core.registry.open")
    @patch("src.core.registry.get_registry_path")
    def test_read_registry_success(self, mock_get_path, mock_open):
        """Test successful registry reading."""
        mock_registry_path = Mock()
        mock_registry_path.exists.return_value = True
        mock_get_path.return_value = mock_registry_path

        # Create a proper context manager mock
        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_open.return_value = mock_file

        # Mock json.load to return test data
        with patch("src.core.registry.json.load") as mock_json_load:
            mock_json_load.return_value = self.test_registry_data

            result = read_registry()

            self.assertEqual(result, self.test_registry_data)

    @patch("src.core.registry.read_registry")
    def test_get_agentic_tool_path(self, mock_read):
        """Test getting agentic tool path from registry."""
        mock_read.return_value = {
            AGENTIC_TOOL_CURSOR: "/Users/gandalf/Library/Application Support/Cursor"
        }

        result = get_agentic_tool_path(AGENTIC_TOOL_CURSOR)

        self.assertEqual(result, "/Users/gandalf/Library/Application Support/Cursor")

    @patch("src.core.registry.read_registry")
    def test_get_agentic_tool_path_not_found(self, mock_read):
        """Test getting agentic tool path when tool not in registry."""
        mock_read.return_value = {AGENTIC_TOOL_CURSOR: "/Users/aragorn/.cursor"}

        result = get_agentic_tool_path(AGENTIC_TOOL_CLAUDE_CODE)

        self.assertIsNone(result)

    @patch("src.core.registry.read_registry")
    def test_get_registered_agentic_tools(self, mock_read):
        """Test getting list of registered agentic tools."""
        mock_read.return_value = {
            AGENTIC_TOOL_CURSOR: "/Users/legolas/.cursor",
            AGENTIC_TOOL_CLAUDE_CODE: "/Users/gimli/.claude",
        }

        result = get_registered_agentic_tools()

        self.assertEqual(set(result), {AGENTIC_TOOL_CURSOR, AGENTIC_TOOL_CLAUDE_CODE})

    @patch("src.core.registry.read_registry")
    def test_zero_tools_registered(self, mock_read):
        """Test behavior when no agentic tools are registered."""
        mock_read.return_value = {}

        result = get_registered_agentic_tools()

        self.assertEqual(result, [])
        self.assertIsNone(get_agentic_tool_path(AGENTIC_TOOL_CURSOR))
        self.assertIsNone(get_agentic_tool_path(AGENTIC_TOOL_CLAUDE_CODE))

    @patch("src.core.registry.read_registry")
    def test_single_tool_registered_cursor(self, mock_read):
        """Test behavior when only Cursor tool is registered."""
        mock_read.return_value = {
            AGENTIC_TOOL_CURSOR: "/Users/bilbo/Library/Application Support/Cursor"
        }

        result = get_registered_agentic_tools()

        self.assertEqual(result, [AGENTIC_TOOL_CURSOR])
        self.assertEqual(
            get_agentic_tool_path(AGENTIC_TOOL_CURSOR),
            "/Users/bilbo/Library/Application Support/Cursor",
        )
        self.assertIsNone(get_agentic_tool_path(AGENTIC_TOOL_CLAUDE_CODE))

    @patch("src.core.registry.read_registry")
    def test_single_tool_registered_claude_code(self, mock_read):
        """Test behavior when only Claude Code tool is registered."""
        mock_read.return_value = {AGENTIC_TOOL_CLAUDE_CODE: "/Users/boromir/.claude"}

        result = get_registered_agentic_tools()

        self.assertEqual(result, [AGENTIC_TOOL_CLAUDE_CODE])
        self.assertEqual(
            get_agentic_tool_path(AGENTIC_TOOL_CLAUDE_CODE),
            "/Users/boromir/.claude",
        )
        self.assertIsNone(get_agentic_tool_path(AGENTIC_TOOL_CURSOR))

    @patch("src.core.registry.read_registry")
    def test_many_tools_registered(self, mock_read):
        """Test behavior when multiple agentic tools are registered."""
        mock_read.return_value = {
            AGENTIC_TOOL_CURSOR: "/Users/aragorn/.cursor",
            AGENTIC_TOOL_CLAUDE_CODE: "/Users/legolas/.claude",
        }

        result = get_registered_agentic_tools()

        self.assertIn(AGENTIC_TOOL_CURSOR, result)
        self.assertIn(AGENTIC_TOOL_CLAUDE_CODE, result)
        self.assertEqual(len(result), 2)
        self.assertEqual(
            get_agentic_tool_path(AGENTIC_TOOL_CURSOR),
            "/Users/aragorn/.cursor",
        )
        self.assertEqual(
            get_agentic_tool_path(AGENTIC_TOOL_CLAUDE_CODE),
            "/Users/legolas/.claude",
        )

    @patch("src.core.registry.find_claude_conversations")
    @patch("src.core.registry.find_cursor_conversations")
    @patch("src.core.registry.read_registry")
    def test_get_all_conversations_zero_tools(
        self, mock_read, mock_cursor, mock_claude
    ):
        """Test getting all conversations when no tools are registered."""
        mock_read.return_value = {}

        result = get_all_conversations()

        self.assertEqual(result, {})
        mock_cursor.assert_not_called()
        mock_claude.assert_not_called()

    @patch("src.core.registry.find_claude_conversations")
    @patch("src.core.registry.find_cursor_conversations")
    @patch("src.core.registry.read_registry")
    def test_get_all_conversations_cursor_only(
        self, mock_read, mock_cursor, mock_claude
    ):
        """Test getting all conversations when only Cursor is registered."""
        mock_read.return_value = {
            AGENTIC_TOOL_CURSOR: "/Users/gollum/Library/Application Support/Cursor"
        }
        mock_cursor.return_value = ["/path/to/rivendell/conversations.vscdb"]
        mock_claude.return_value = []

        result = get_all_conversations()

        self.assertEqual(
            result,
            {AGENTIC_TOOL_CURSOR: ["/path/to/rivendell/conversations.vscdb"]},
        )
        mock_cursor.assert_called_once_with(
            "/Users/gollum/Library/Application Support/Cursor"
        )
        mock_claude.assert_not_called()

    @patch("src.core.registry.find_claude_conversations")
    @patch("src.core.registry.find_cursor_conversations")
    @patch("src.core.registry.read_registry")
    def test_get_all_conversations_claude_only(
        self, mock_read, mock_cursor, mock_claude
    ):
        """Test getting all conversations when only Claude Code is registered."""
        mock_read.return_value = {AGENTIC_TOOL_CLAUDE_CODE: "/Users/elrond/.claude"}
        mock_cursor.return_value = []
        mock_claude.return_value = ["/path/to/lothlórien/session.json"]

        result = get_all_conversations()

        self.assertEqual(
            result,
            {AGENTIC_TOOL_CLAUDE_CODE: ["/path/to/lothlórien/session.json"]},
        )
        mock_cursor.assert_not_called()
        mock_claude.assert_called_once_with("/Users/elrond/.claude")

    @patch("src.core.registry.find_claude_conversations")
    @patch("src.core.registry.find_cursor_conversations")
    @patch("src.core.registry.read_registry")
    def test_get_all_conversations_many_tools(
        self, mock_read, mock_cursor, mock_claude
    ):
        """Test getting all conversations when multiple tools are registered."""
        mock_read.return_value = {
            AGENTIC_TOOL_CURSOR: "/Users/théoden/.cursor",
            AGENTIC_TOOL_CLAUDE_CODE: "/Users/galadriel/.claude",
        }
        mock_cursor.return_value = ["/path/to/edoras/conversations.vscdb"]
        mock_claude.return_value = ["/path/to/caras_galadhon/wisdom.json"]

        result = get_all_conversations()

        expected = {
            AGENTIC_TOOL_CURSOR: ["/path/to/edoras/conversations.vscdb"],
            AGENTIC_TOOL_CLAUDE_CODE: ["/path/to/caras_galadhon/wisdom.json"],
        }
        self.assertEqual(result, expected)
        mock_cursor.assert_called_once_with("/Users/théoden/.cursor")
        mock_claude.assert_called_once_with("/Users/galadriel/.claude")

    @patch("src.core.registry.find_claude_conversations")
    @patch("src.core.registry.find_cursor_conversations")
    @patch("src.core.registry.read_registry")
    def test_get_all_conversations_partial_results(
        self, mock_read, mock_cursor, mock_claude
    ):
        """Test getting all conversations when some tools have no conversations."""
        mock_read.return_value = {
            AGENTIC_TOOL_CURSOR: "/Users/faramir/.cursor",
            AGENTIC_TOOL_CLAUDE_CODE: "/Users/denethor/.claude",
        }
        # Cursor has no conversations, Claude Code has some
        mock_cursor.return_value = []
        mock_claude.return_value = ["/path/to/minas_tirith/steward_logs.json"]

        result = get_all_conversations()

        # Only tools with conversations should be in the result
        self.assertEqual(
            result,
            {AGENTIC_TOOL_CLAUDE_CODE: ["/path/to/minas_tirith/steward_logs.json"]},
        )
        mock_cursor.assert_called_once_with("/Users/faramir/.cursor")
        mock_claude.assert_called_once_with("/Users/denethor/.claude")

    def test_find_cursor_conversations(self):
        """Test finding Cursor conversations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cursor_path = Path(temp_dir) / "Cursor"
            # Registry expects: Path(cursor_path).parent / CURSOR_WORKSPACE_STORAGE_PATH
            # where CURSOR_WORKSPACE_STORAGE_PATH = "Application Support/Cursor/User/workspaceStorage"
            workspace_storage = (
                cursor_path.parent
                / "Application Support"
                / "Cursor"
                / "User"
                / "workspaceStorage"
            )
            workspace_storage.mkdir(parents=True)

            # Create some mock database files
            workspace1 = workspace_storage / "workspace1_hash"
            workspace1.mkdir()
            (workspace1 / "conversations.vscdb").touch()
            (workspace1 / "other.db").touch()

            workspace2 = workspace_storage / "workspace2_hash"
            workspace2.mkdir()
            (workspace2 / "conversations.vscdb").touch()

            result = find_cursor_conversations(str(cursor_path))

            # Should find conversations in both workspaces
            self.assertEqual(len(result), 3)  # 2 vscdb + 1 db file
            for conversation_path in result:
                self.assertTrue(
                    conversation_path.endswith(".vscdb")
                    or conversation_path.endswith(".db")
                )

    def test_find_claude_conversations(self):
        """Test finding Claude Code conversations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            claude_path = Path(temp_dir)

            # Create some mock conversation files
            (claude_path / "session1.json").touch()
            (claude_path / "session2.json").touch()
            (claude_path / "config.toml").touch()  # Should not be included

            result = find_claude_conversations(str(claude_path))

            # Should find JSON files only
            self.assertEqual(len(result), 2)
            for conversation_path in result:
                self.assertTrue(conversation_path.endswith(".json"))

    @patch("src.core.registry.find_claude_conversations")
    @patch("src.core.registry.find_cursor_conversations")
    @patch("src.core.registry.read_registry")
    def test_get_all_conversations_integration(
        self, mock_read, mock_cursor, mock_claude
    ):
        """Test full integration scenario with multiple tools and conversations."""
        mock_read.return_value = {
            AGENTIC_TOOL_CURSOR: "/Users/samwise/.cursor",
            AGENTIC_TOOL_CLAUDE_CODE: "/Users/frodo/.claude",
        }
        mock_cursor.return_value = ["/path/to/bag_end/garden_conversations.vscdb"]
        mock_claude.return_value = ["/path/to/bag_end/ring_bearer_logs.json"]

        result = get_all_conversations()

        expected = {
            AGENTIC_TOOL_CURSOR: ["/path/to/bag_end/garden_conversations.vscdb"],
            AGENTIC_TOOL_CLAUDE_CODE: ["/path/to/bag_end/ring_bearer_logs.json"],
        }
        self.assertEqual(result, expected)
