"""
Comprehensive tests for file_tools module.

Tests cover all functionality including file listing, relevance scoring,
validation, security checks, and error handling.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from src.tool_calls.file_tools import (
    FILE_TOOL_DEFINITIONS,
    FILE_TOOL_HANDLERS,
    TOOL_LIST_PROJECT_FILES,
    _validate_cache_security,
    handle_list_project_files,
    validate_max_files,
)


class TestValidateMaxFiles:
    """Test the validate_max_files function."""

    def test_valid_max_files(self):
        """Test valid max_files values."""
        valid, error = validate_max_files(100)
        assert valid is True
        assert error == ""

        valid, error = validate_max_files(1)
        assert valid is True
        assert error == ""

        valid, error = validate_max_files(10000)
        assert valid is True
        assert error == ""

    def test_invalid_max_files_too_small(self):
        """Test max_files values that are too small."""
        valid, error = validate_max_files(0)
        assert valid is False
        assert "must be at least 1" in error

        valid, error = validate_max_files(-1)
        assert valid is False
        assert "must be at least 1" in error

    def test_invalid_max_files_too_large(self):
        """Test max_files values that are too large."""
        valid, error = validate_max_files(10001)
        assert valid is False
        assert "cannot exceed 10000" in error

        valid, error = validate_max_files(50000)
        assert valid is False
        assert "cannot exceed 10000" in error


class TestValidateCacheSecurity:
    """Test the _validate_cache_security function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_root = self.temp_dir / "test_project"
        self.project_root.mkdir()

        # Create some test files
        (self.project_root / "file1.py").write_text("test content")
        (self.project_root / "file2.js").write_text("test content")
        (self.project_root / "subdir").mkdir()
        (self.project_root / "subdir" / "file3.md").write_text("test content")

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_valid_cache_security(self):
        """Test cache security validation with valid files."""
        scored_files = [
            (str(self.project_root / "file1.py"), 0.8),
            (str(self.project_root / "file2.js"), 0.6),
            (str(self.project_root / "subdir" / "file3.md"), 0.4),
        ]

        result = _validate_cache_security(self.project_root, scored_files)
        assert result is True

    def test_invalid_cache_security_outside_project(self):
        """Test cache security validation with files outside project root."""
        outside_file = self.temp_dir / "outside_file.txt"
        outside_file.write_text("outside content")

        scored_files = [
            (str(self.project_root / "file1.py"), 0.8),
            (str(outside_file), 0.6),  # This should fail security check
        ]

        result = _validate_cache_security(self.project_root, scored_files)
        assert result is False

    def test_invalid_cache_security_invalid_paths(self):
        """Test cache security validation with invalid file paths."""
        scored_files = [
            (str(self.project_root / "file1.py"), 0.8),
            ("invalid/path/that/does/not/exist", 0.6),
        ]

        # This should handle the invalid path gracefully
        result = _validate_cache_security(self.project_root, scored_files)
        # The function should return False for invalid paths
        assert result is False

    def test_cache_security_with_empty_list(self):
        """Test cache security validation with empty file list."""
        result = _validate_cache_security(self.project_root, [])
        assert result is True

    def test_cache_security_with_project_root_error(self):
        """Test cache security validation when project root resolution fails."""
        # Use a non-existent project root
        non_existent_root = Path("/non/existent/path")
        scored_files = [("some_file.py", 0.8)]

        result = _validate_cache_security(non_existent_root, scored_files)
        assert result is False


class TestHandleListProjectFiles:
    """Test the handle_list_project_files function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_root = self.temp_dir / "test_project"
        self.project_root.mkdir()

        # Create a variety of test files
        (self.project_root / "main.py").write_text("# Main Python file")
        (self.project_root / "script.js").write_text("// JavaScript file")
        (self.project_root / "README.md").write_text("# README")
        (self.project_root / "config.json").write_text('{"key": "value"}')

        # Create subdirectory with files
        subdir = self.project_root / "src"
        subdir.mkdir()
        (subdir / "utils.py").write_text("# Utilities")
        (subdir / "helper.js").write_text("// Helper functions")

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _check_success_response(self, result):
        """Helper to check if response is successful."""
        return "content" in result and not result.get("isError", False)

    def _check_error_response(self, result):
        """Helper to check if response is an error."""
        return result.get("isError", False) is True

    def _get_response_text(self, result):
        """Helper to extract text from response."""
        if "content" in result and result["content"]:
            return result["content"][0]["text"]
        return ""

    def test_basic_file_listing_without_scoring(self):
        """Test basic file listing without relevance scoring."""
        arguments = {
            "use_relevance_scoring": False,
            "max_files": 100,
        }

        with patch("src.tool_calls.file_tools.get_files_list") as mock_get_files:
            mock_get_files.return_value = [
                str(self.project_root / "main.py"),
                str(self.project_root / "script.js"),
                str(self.project_root / "README.md"),
            ]

            result = handle_list_project_files(arguments, self.project_root)

            assert self._check_success_response(result)
            content = self._get_response_text(result)
            assert "FILES (3 total):" in content
            assert "main.py" in content
            assert "script.js" in content
            assert "README.md" in content

    def test_file_listing_with_relevance_scoring(self):
        """Test file listing with relevance scoring enabled."""
        arguments = {
            "use_relevance_scoring": True,
            "max_files": 100,
        }

        mock_scored_files = [
            (str(self.project_root / "main.py"), 0.9),
            (str(self.project_root / "script.js"), 0.7),
            (str(self.project_root / "README.md"), 0.3),
        ]

        with patch(
            "src.tool_calls.file_tools.get_files_with_scores"
        ) as mock_get_scored:
            with patch(
                "src.tool_calls.file_tools._validate_cache_security"
            ) as mock_validate:
                mock_get_scored.return_value = mock_scored_files
                mock_validate.return_value = True

                result = handle_list_project_files(arguments, self.project_root)

                assert self._check_success_response(result)
                content = self._get_response_text(result)
                assert "HIGH PRIORITY FILES:" in content
                assert "MEDIUM PRIORITY FILES:" in content
                assert "LOW PRIORITY FILES:" in content
                assert "TOP FILES BY RELEVANCE:" in content
                assert "SUMMARY:" in content

    def test_file_type_filtering_without_scoring(self):
        """Test file type filtering without relevance scoring."""
        arguments = {
            "file_types": [".py"],
            "use_relevance_scoring": False,
            "max_files": 100,
        }

        with patch("src.tool_calls.file_tools.get_files_list") as mock_get_files:
            mock_get_files.return_value = [
                str(self.project_root / "main.py"),
                str(self.project_root / "script.js"),
                str(self.project_root / "src" / "utils.py"),
            ]

            result = handle_list_project_files(arguments, self.project_root)

            assert self._check_success_response(result)
            content = self._get_response_text(result)
            assert "main.py" in content
            assert "utils.py" in content
            assert "script.js" not in content

    def test_file_type_filtering_with_scoring(self):
        """Test file type filtering with relevance scoring."""
        arguments = {
            "file_types": [".py"],
            "use_relevance_scoring": True,
            "max_files": 100,
        }

        mock_scored_files = [
            (str(self.project_root / "main.py"), 0.9),
            (str(self.project_root / "script.js"), 0.7),
            (str(self.project_root / "src" / "utils.py"), 0.6),
        ]

        with patch(
            "src.tool_calls.file_tools.get_files_with_scores"
        ) as mock_get_scored:
            with patch(
                "src.tool_calls.file_tools._validate_cache_security"
            ) as mock_validate:
                mock_get_scored.return_value = mock_scored_files
                mock_validate.return_value = True

                result = handle_list_project_files(arguments, self.project_root)

                assert self._check_success_response(result)
                content = self._get_response_text(result)
                assert "main.py" in content
                assert "utils.py" in content
                assert "script.js" not in content

    def test_file_type_filtering_extension_variants(self):
        """Test file type filtering with different extension formats."""
        arguments = {
            "file_types": ["py", ".js"],  # Mixed formats
            "use_relevance_scoring": False,
            "max_files": 100,
        }

        with patch("src.tool_calls.file_tools.get_files_list") as mock_get_files:
            mock_get_files.return_value = [
                str(self.project_root / "main.py"),
                str(self.project_root / "script.js"),
                str(self.project_root / "README.md"),
            ]

            result = handle_list_project_files(arguments, self.project_root)

            assert self._check_success_response(result)
            content = self._get_response_text(result)
            assert "main.py" in content
            assert "script.js" in content
            assert "README.md" not in content

    def test_max_files_limiting(self):
        """Test max_files parameter limiting results."""
        arguments = {
            "use_relevance_scoring": False,
            "max_files": 2,
        }

        with patch("src.tool_calls.file_tools.get_files_list") as mock_get_files:
            mock_get_files.return_value = [
                str(self.project_root / "main.py"),
                str(self.project_root / "script.js"),
                str(self.project_root / "README.md"),
                str(self.project_root / "config.json"),
            ]

            result = handle_list_project_files(arguments, self.project_root)

            assert self._check_success_response(result)
            content = self._get_response_text(result)
            assert "FILES (2 total):" in content

    def test_cache_security_failure_triggers_refresh(self):
        """Test that cache security failure triggers cache refresh."""
        arguments = {
            "use_relevance_scoring": True,
            "max_files": 100,
        }

        mock_scored_files = [
            (str(self.project_root / "main.py"), 0.9),
        ]

        with patch(
            "src.tool_calls.file_tools.get_files_with_scores"
        ) as mock_get_scored:
            with patch(
                "src.tool_calls.file_tools._validate_cache_security"
            ) as mock_validate:
                with patch("src.tool_calls.file_tools.clear_file_scores") as mock_clear:
                    # First call returns False (security failure), second call returns True
                    mock_validate.side_effect = [False, True]
                    mock_get_scored.return_value = mock_scored_files

                    result = handle_list_project_files(arguments, self.project_root)

                    assert self._check_success_response(result)
                    # Verify that clear_file_scores was called
                    mock_clear.assert_called_once_with(self.project_root)
                    # Verify that get_files_with_scores was called twice (initial + refresh)
                    assert mock_get_scored.call_count == 2

    def test_invalid_file_types_parameter(self):
        """Test validation of file_types parameter."""
        arguments = {
            "file_types": "invalid",  # Should be a list
            "use_relevance_scoring": False,
        }

        result = handle_list_project_files(arguments, self.project_root)

        assert self._check_error_response(result)
        content = self._get_response_text(result)
        assert "file_types must be an array" in content

    def test_invalid_use_relevance_scoring_parameter(self):
        """Test validation of use_relevance_scoring parameter."""
        arguments = {
            "use_relevance_scoring": "invalid",  # Should be boolean
        }

        result = handle_list_project_files(arguments, self.project_root)

        assert self._check_error_response(result)
        content = self._get_response_text(result)
        assert "use_relevance_scoring must be a boolean" in content

    def test_invalid_max_files_parameter_type(self):
        """Test validation of max_files parameter type."""
        arguments = {
            "max_files": "invalid",  # Should be integer
        }

        result = handle_list_project_files(arguments, self.project_root)

        assert self._check_error_response(result)
        content = self._get_response_text(result)
        assert "max_files must be a positive integer" in content

    def test_invalid_max_files_parameter_value(self):
        """Test validation of max_files parameter value."""
        arguments = {
            "max_files": 0,  # Should be positive
        }

        result = handle_list_project_files(arguments, self.project_root)

        assert self._check_error_response(result)
        content = self._get_response_text(result)
        assert "max_files must be a positive integer" in content

    def test_max_files_exceeds_limit(self):
        """Test max_files parameter exceeding limit."""
        arguments = {
            "max_files": 20000,  # Exceeds MAX_FILES_LIMIT
        }

        result = handle_list_project_files(arguments, self.project_root)

        assert self._check_error_response(result)
        content = self._get_response_text(result)
        assert "cannot exceed 10000" in content

    def test_invalid_project_root_path(self):
        """Test validation of project_root path."""
        arguments = {
            "use_relevance_scoring": False,
        }

        with patch(
            "src.utils.access_control.AccessValidator.validate_path"
        ) as mock_validate:
            mock_validate.return_value = (False, "Invalid path")

            result = handle_list_project_files(arguments, self.project_root)

            assert self._check_error_response(result)
            content = self._get_response_text(result)
            assert "Invalid path" in content

    def test_nonexistent_project_root(self):
        """Test with non-existent project root."""
        arguments = {
            "use_relevance_scoring": False,
        }

        non_existent_root = Path("/non/existent/path")

        result = handle_list_project_files(arguments, non_existent_root)

        assert self._check_error_response(result)
        content = self._get_response_text(result)
        assert "Invalid project root directory" in content

    def test_project_root_not_directory(self):
        """Test with project root that is not a directory."""
        arguments = {
            "use_relevance_scoring": False,
        }

        # Create a file instead of directory
        file_path = self.temp_dir / "not_a_directory.txt"
        file_path.write_text("content")

        result = handle_list_project_files(arguments, file_path)

        assert self._check_error_response(result)
        content = self._get_response_text(result)
        assert "Invalid project root directory" in content

    def test_path_error_handling_in_filtering(self):
        """Test handling of path errors during file type filtering."""
        arguments = {
            "file_types": [".py"],
            "use_relevance_scoring": False,
        }

        # Mock get_files_list to return a path that will cause an error
        with patch("src.tool_calls.file_tools.get_files_list") as mock_get_files:
            mock_get_files.return_value = [
                str(self.project_root / "main.py"),
                "invalid\x00path",  # This should cause a path error
            ]

            result = handle_list_project_files(arguments, self.project_root)

            # Should handle the error gracefully and continue with valid files
            assert self._check_success_response(result)
            content = self._get_response_text(result)
            assert "main.py" in content

    def test_path_error_handling_in_scoring_filtering(self):
        """Test handling of path errors during file type filtering with scoring."""
        arguments = {
            "file_types": [".py"],
            "use_relevance_scoring": True,
        }

        mock_scored_files = [
            (str(self.project_root / "main.py"), 0.9),
            ("invalid\x00path", 0.7),  # This should cause a path error
        ]

        with patch(
            "src.tool_calls.file_tools.get_files_with_scores"
        ) as mock_get_scored:
            with patch(
                "src.tool_calls.file_tools._validate_cache_security"
            ) as mock_validate:
                mock_get_scored.return_value = mock_scored_files
                mock_validate.return_value = True

                result = handle_list_project_files(arguments, self.project_root)

                # Should handle the error gracefully and continue with valid files
                assert self._check_success_response(result)
                content = self._get_response_text(result)
                assert "main.py" in content

    def test_general_exception_handling(self):
        """Test general exception handling in handle_list_project_files."""
        arguments = {
            "use_relevance_scoring": False,
        }

        with patch("src.tool_calls.file_tools.get_files_list") as mock_get_files:
            mock_get_files.side_effect = OSError("Simulated OS error")

            result = handle_list_project_files(arguments, self.project_root)

            assert self._check_error_response(result)
            content = self._get_response_text(result)
            assert "Error listing files: Simulated OS error" in content

    def test_default_arguments(self):
        """Test handle_list_project_files with default arguments."""
        arguments = {}  # Empty arguments should use defaults

        with patch("src.tool_calls.file_tools.get_files_list") as mock_get_files:
            mock_get_files.return_value = [
                str(self.project_root / "main.py"),
            ]

            result = handle_list_project_files(arguments, self.project_root)

            assert self._check_success_response(result)
            content = self._get_response_text(result)
            assert "FILES (1 total):" in content

    def test_priority_level_display_limits(self):
        """Test that priority level display limits are respected."""
        arguments = {
            "use_relevance_scoring": True,
            "max_files": 1000,
        }

        # Create many files with different priority levels
        high_priority_files = [
            (f"high_{i}.py", 0.9) for i in range(60)
        ]  # More than HIGH_PRIORITY_DISPLAY_LIMIT
        medium_priority_files = [
            (f"medium_{i}.py", 0.7) for i in range(20)
        ]  # More than MEDIUM_PRIORITY_DISPLAY_LIMIT
        low_priority_files = [
            (f"low_{i}.py", 0.3) for i in range(15)
        ]  # More than LOW_PRIORITY_DISPLAY_LIMIT

        mock_scored_files = (
            high_priority_files + medium_priority_files + low_priority_files
        )

        with patch(
            "src.tool_calls.file_tools.get_files_with_scores"
        ) as mock_get_scored:
            with patch(
                "src.tool_calls.file_tools._validate_cache_security"
            ) as mock_validate:
                mock_get_scored.return_value = mock_scored_files
                mock_validate.return_value = True

                result = handle_list_project_files(arguments, self.project_root)

                assert self._check_success_response(result)
                content = self._get_response_text(result)

                # Count how many files are shown in each section
                high_section = content.split("HIGH PRIORITY FILES:")[1].split(
                    "\nMEDIUM PRIORITY FILES:"
                )[0]
                high_count = len(
                    [
                        line
                        for line in high_section.split("\n")
                        if line.strip().startswith("  ")
                    ]
                )

                # Should respect the HIGH_PRIORITY_DISPLAY_LIMIT (50)
                assert high_count <= 50

    def test_none_use_relevance_scoring(self):
        """Test with None value for use_relevance_scoring."""
        arguments = {
            "use_relevance_scoring": None,
        }

        with patch("src.tool_calls.file_tools.get_files_list") as mock_get_files:
            mock_get_files.return_value = []

            result = handle_list_project_files(arguments, self.project_root)

            # None should be acceptable and default to False behavior
            assert self._check_success_response(result)
            content = self._get_response_text(result)
            assert "FILES (0 total):" in content

    def test_invalid_use_relevance_scoring_type(self):
        """Test with invalid type for use_relevance_scoring."""
        arguments = {
            "use_relevance_scoring": "invalid",  # Should be boolean or None
        }

        result = handle_list_project_files(arguments, self.project_root)

        assert self._check_error_response(result)
        content = self._get_response_text(result)
        assert "use_relevance_scoring must be a boolean" in content


class TestToolDefinitionsAndHandlers:
    """Test tool definitions and handlers are properly configured."""

    def test_tool_definitions_structure(self):
        """Test that tool definitions have correct structure."""
        assert len(FILE_TOOL_DEFINITIONS) == 1
        tool_def = TOOL_LIST_PROJECT_FILES

        assert tool_def["name"] == "list_project_files"
        assert "description" in tool_def
        assert "inputSchema" in tool_def
        assert "annotations" in tool_def

        # Check input schema structure
        schema = tool_def["inputSchema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "file_types" in schema["properties"]
        assert "max_files" in schema["properties"]
        assert "use_relevance_scoring" in schema["properties"]

    def test_tool_handlers_mapping(self):
        """Test that tool handlers are properly mapped."""
        assert len(FILE_TOOL_HANDLERS) == 1
        assert "list_project_files" in FILE_TOOL_HANDLERS
        assert FILE_TOOL_HANDLERS["list_project_files"] == handle_list_project_files

    def test_tool_definition_constants(self):
        """Test that tool definition constants are properly set."""
        tool_def = TOOL_LIST_PROJECT_FILES

        # Check that limits are properly defined
        file_types_schema = tool_def["inputSchema"]["properties"]["file_types"]
        assert file_types_schema["maxItems"] == 20  # MAX_FILE_TYPES

        max_files_schema = tool_def["inputSchema"]["properties"]["max_files"]
        assert max_files_schema["maximum"] == 10000  # MAX_FILES_LIMIT
        assert max_files_schema["minimum"] == 1
        assert max_files_schema["default"] == 1000

    def test_tool_annotations(self):
        """Test that tool annotations are properly set."""
        annotations = TOOL_LIST_PROJECT_FILES["annotations"]

        assert annotations["title"] == "List Project Files"
        assert annotations["readOnlyHint"] is True
        assert annotations["destructiveHint"] is False
        assert annotations["idempotentHint"] is True
        assert annotations["openWorldHint"] is False


class TestEdgeCasesAndBoundaryConditions:
    """Test edge cases and boundary conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_root = self.temp_dir / "test_project"
        self.project_root.mkdir()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _check_success_response(self, result):
        """Helper to check if response is successful."""
        return "content" in result and not result.get("isError", False)

    def _check_error_response(self, result):
        """Helper to check if response is an error."""
        return result.get("isError", False) is True

    def _get_response_text(self, result):
        """Helper to extract text from response."""
        if "content" in result and result["content"]:
            return result["content"][0]["text"]
        return ""

    def test_empty_project_directory(self):
        """Test with empty project directory."""
        arguments = {
            "use_relevance_scoring": False,
        }

        with patch("src.tool_calls.file_tools.get_files_list") as mock_get_files:
            mock_get_files.return_value = []

            result = handle_list_project_files(arguments, self.project_root)

            assert self._check_success_response(result)
            content = self._get_response_text(result)
            assert "FILES (0 total):" in content

    def test_empty_scored_files(self):
        """Test with empty scored files list."""
        arguments = {
            "use_relevance_scoring": True,
        }

        with patch(
            "src.tool_calls.file_tools.get_files_with_scores"
        ) as mock_get_scored:
            with patch(
                "src.tool_calls.file_tools._validate_cache_security"
            ) as mock_validate:
                mock_get_scored.return_value = []
                mock_validate.return_value = True

                result = handle_list_project_files(arguments, self.project_root)

                assert self._check_success_response(result)
                content = self._get_response_text(result)
                assert "SUMMARY: 0 total files" in content

    def test_boundary_max_files_values(self):
        """Test boundary values for max_files."""
        # Test exactly at the limit
        arguments = {
            "max_files": 10000,  # Exactly at MAX_FILES_LIMIT
            "use_relevance_scoring": False,
        }

        with patch("src.tool_calls.file_tools.get_files_list") as mock_get_files:
            mock_get_files.return_value = ["file.py"]

            result = handle_list_project_files(arguments, self.project_root)
            assert self._check_success_response(result)

        # Test just over the limit
        arguments["max_files"] = 10001
        result = handle_list_project_files(arguments, self.project_root)
        assert self._check_error_response(result)
