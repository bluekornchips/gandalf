"""
Tests for file tools functionality.

Tests file operations, project analysis, and file system interaction
with comprehensive coverage of file tools functionality.
"""

import tempfile
from pathlib import Path

from src.tool_calls.file_tools import (
    handle_list_project_files,
)
from src.tool_calls.project_operations import (
    handle_get_project_info,
)


class TestHandleGetProjectInfo:
    """Test handle_get_project_info function."""

    def test_handle_get_project_info_basic(self):
        """Test basic project info handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            arguments = {"include_stats": True}

            result = handle_get_project_info(arguments, project_root)

            assert "content" in result
            assert result["content"][0]["type"] == "text"
            # Should contain basic project info
            assert "project_name" in result["content"][0]["text"]

    def test_handle_get_project_info_without_stats(self):
        """Test project info without stats."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            arguments = {"include_stats": False}

            result = handle_get_project_info(arguments, project_root)

            assert "content" in result
            # Should not contain file stats when disabled
            content_text = result["content"][0]["text"]
            assert "file_stats" not in content_text

    def test_handle_get_project_info_default_args(self):
        """Test project info with default arguments."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            arguments = {}

            result = handle_get_project_info(arguments, project_root)

            assert "content" in result
            assert result["content"][0]["type"] == "text"
            # Should include stats by default
            assert "project_name" in result["content"][0]["text"]

    def test_handle_get_project_info_invalid_path(self):
        """Test error handling for invalid project path."""
        project_root = Path("/nonexistent/path")
        arguments = {"include_stats": True}

        result = handle_get_project_info(arguments, project_root)

        assert result["isError"] is True
        assert "Project root does not exist" in result["error"]

    def test_handle_get_project_info_invalid_include_stats(self):
        """Test error handling for invalid include_stats parameter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            arguments = {"include_stats": "invalid"}

            result = handle_get_project_info(arguments, project_root)

            assert result["isError"] is True
            assert "include_stats must be a boolean" in result["error"]


class TestHandleListProjectFiles:
    """Test handle_list_project_files function."""

    def test_handle_list_project_files_basic(self):
        """Test basic project files listing."""
        arguments = {"max_files": 100}

        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Create test files
            (project_root / "file1.py").write_text("print('hello')")
            (project_root / "file2.js").write_text("console.log('world')")

            result = handle_list_project_files(arguments, project_root)

            assert "content" in result
            assert result["content"][0]["type"] == "text"

    def test_handle_list_project_files_with_filters(self):
        """Test project files listing with filters."""
        arguments = {
            "max_files": 50,
            "file_types": [".py", ".js"],
            "use_relevance_scoring": False,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Create test files
            (project_root / "file1.py").write_text("print('hello')")
            (project_root / "file2.js").write_text("console.log('world')")

            result = handle_list_project_files(arguments, project_root)

            assert "content" in result

    def test_handle_list_project_files_default_args(self):
        """Test project files listing with default arguments."""
        arguments = {}

        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Create test files
            (project_root / "file1.py").write_text("print('hello')")

            result = handle_list_project_files(arguments, project_root)

            assert "content" in result
