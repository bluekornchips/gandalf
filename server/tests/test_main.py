"""
Tests for main.py entry point functionality.

lotr-info: Tests the main entry point for the Gandalf MCP server using
Hobbiton and Rivendell as test project directories.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.main import main


class TestMain:
    """Tests for main entry point function."""

    def test_main_with_no_arguments(self):
        """Test main function with no command line arguments."""
        with patch("sys.argv", ["gandalf-server"]):
            with patch("src.main.GandalfMCP") as mock_gandalf:
                mock_server = Mock()
                mock_gandalf.return_value = mock_server

                main()

                mock_gandalf.assert_called_once_with(project_root=None)
                mock_server.run.assert_called_once()

    def test_main_with_valid_project_root(self, tmp_path):
        """Test main function with valid project root path."""
        hobbiton_path = tmp_path / "hobbiton"
        hobbiton_path.mkdir()

        with patch(
            "sys.argv", ["gandalf-server", "--project-root", str(hobbiton_path)]
        ):
            with patch("src.main.GandalfMCP") as mock_gandalf:
                mock_server = Mock()
                mock_gandalf.return_value = mock_server

                main()

                mock_gandalf.assert_called_once_with(project_root=hobbiton_path)
                mock_server.run.assert_called_once()

    def test_main_with_nonexistent_project_root(self, tmp_path, capsys):
        """Test main function with non-existent project root."""
        isengard_path = tmp_path / "isengard"

        with patch(
            "sys.argv", ["gandalf-server", "--project-root", str(isengard_path)]
        ):
            with patch("src.main.GandalfMCP") as mock_gandalf:
                mock_server = Mock()
                mock_gandalf.return_value = mock_server

                main()

                # Server should start successfully with nonexistent project root
                mock_gandalf.assert_called_once_with(project_root=isengard_path)
                mock_server.run.assert_called_once()

    def test_main_with_file_as_project_root(self, tmp_path, capsys):
        """Test main function with file instead of directory."""
        ring_file = tmp_path / "the_ring.txt"
        ring_file.write_text("One ring to rule them all")

        with patch("sys.argv", ["gandalf-server", "--project-root", str(ring_file)]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Error: Project root is not a directory" in captured.err
            assert str(ring_file) in captured.err

    def test_main_with_invalid_path_format(self, capsys):
        """Test main function with invalid path format."""
        invalid_path = "\x00invalid\x00path"

        with patch("sys.argv", ["gandalf-server", "--project-root", invalid_path]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Error: Invalid project root path" in captured.err

    def test_main_with_help_flag(self, capsys):
        """Test main function with help flag."""
        with patch("sys.argv", ["gandalf-server", "--help"]):
            main()

            captured = capsys.readouterr()
            assert "Gandalf MCP Server" in captured.out
            assert "--project-root" in captured.out

    def test_main_with_invalid_argument(self, capsys):
        """Test main function with invalid argument."""
        with patch("sys.argv", ["gandalf-server", "--invalid-arg"]):
            main()

            captured = capsys.readouterr()
            assert "unrecognized arguments" in captured.err

    def test_main_server_initialization_error(self, tmp_path, capsys):
        """Test main function when server fails to initialize."""
        rivendell_path = tmp_path / "rivendell"
        rivendell_path.mkdir()

        with patch(
            "sys.argv", ["gandalf-server", "--project-root", str(rivendell_path)]
        ):
            with patch("src.main.GandalfMCP") as mock_gandalf:
                mock_gandalf.side_effect = Exception("Server initialization failed")

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "Error: Failed to start server" in captured.err
                assert "Server initialization failed" in captured.err

    def test_main_server_runtime_error(self, tmp_path, capsys):
        """Test main function when server fails during runtime."""
        shire_path = tmp_path / "shire"
        shire_path.mkdir()

        with patch("sys.argv", ["gandalf-server", "--project-root", str(shire_path)]):
            with patch("src.main.GandalfMCP") as mock_gandalf:
                mock_server = Mock()
                mock_server.run.side_effect = Exception("Server runtime error")
                mock_gandalf.return_value = mock_server

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "Error: Failed to start server" in captured.err
                assert "Server runtime error" in captured.err

    def test_main_path_resolution(self, tmp_path):
        """Test that project root path is properly resolved."""
        moria_path = tmp_path / "moria"
        moria_path.mkdir()

        with patch("sys.argv", ["gandalf-server", "--project-root", str(moria_path)]):
            with patch("src.main.GandalfMCP") as mock_gandalf:
                mock_server = Mock()
                mock_gandalf.return_value = mock_server

                main()

                called_path = mock_gandalf.call_args[1]["project_root"]
                assert called_path.is_absolute()
                assert called_path.name == "moria"
                assert called_path == moria_path

    def test_main_empty_project_root_argument(self, capsys):
        """Test main function with empty project root argument."""
        with patch("sys.argv", ["gandalf-server", "--project-root", ""]):
            with patch("src.main.GandalfMCP") as mock_gandalf:
                mock_server = Mock()
                mock_gandalf.return_value = mock_server

                main()

                mock_gandalf.assert_called_once_with(project_root=None)
                mock_server.run.assert_called_once()

    def test_main_with_os_error_on_path_resolution(self, capsys):
        """Test main function when Path operations raise OSError."""
        with patch("sys.argv", ["gandalf-server", "--project-root", "/forbidden/path"]):
            with patch(
                "pathlib.Path.resolve", side_effect=OSError("Permission denied")
            ):
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "Error: Invalid project root path" in captured.err
                assert "Permission denied" in captured.err
