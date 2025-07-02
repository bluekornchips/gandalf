"""Test main module functionality."""

import argparse
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.main import main


class TestMainFunction:
    """Test main function behavior."""

    @patch("src.main.GandalfMCP")
    @patch("src.main.Path")
    @patch("src.main.argparse.ArgumentParser")
    def test_main_with_project_root(self, mock_parser_class, mock_path, mock_server):
        """Test main function with explicit project root."""
        # Set up mocks
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser

        mock_args = Mock()
        mock_args.project_root = "/path/to/project"
        mock_parser.parse_args.return_value = mock_args

        mock_path_instance = Mock()
        mock_path.return_value.resolve.return_value = mock_path_instance

        mock_server_instance = Mock()
        mock_server.return_value = mock_server_instance

        # Call the main function
        main()

        # Verify server was created with correct project root
        mock_server.assert_called_once_with(project_root=str(mock_path_instance))
        mock_server_instance.run.assert_called_once()

    @patch("src.main.GandalfMCP")
    @patch("src.main.argparse.ArgumentParser")
    def test_main_without_project_root(self, mock_parser_class, mock_server):
        """Test main function without explicit project root."""
        # Set up mocks
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser

        mock_args = Mock()
        mock_args.project_root = None
        mock_parser.parse_args.return_value = mock_args

        mock_server_instance = Mock()
        mock_server.return_value = mock_server_instance

        # Call the main function
        main()

        # Verify server was created with None project root
        mock_server.assert_called_once_with(project_root=None)
        mock_server_instance.run.assert_called_once()


class TestArgumentParsing:
    """Test command line argument parsing."""

    @patch("sys.argv", ["gandalf", "--project-root", "/test/path"])
    @patch("src.main.GandalfMCP")
    def test_argument_parsing_integration(self, mock_server):
        """Test that command line arguments are parsed correctly."""
        mock_server_instance = Mock()
        mock_server.return_value = mock_server_instance

        # Call the main function
        main()

        # Verify server was created with the parsed project root
        mock_server.assert_called_once()
        call_args = mock_server.call_args
        assert call_args[1]["project_root"] is not None
        assert "/test/path" in call_args[1]["project_root"]


class TestModuleExecution:
    """Test module execution and structure."""

    def test_module_structure(self):
        """Test basic module structure."""
        import src.main

        assert hasattr(src.main, "main")
        assert hasattr(src.main, "argparse")

    def test_main_function_callable(self):
        """Test that main function is callable."""
        assert callable(main)
