"""
Tests for src.utils.cache.

Comprehensive test coverage for all functions and edge cases.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.utils.cache import get_cache_directory


class TestCache:
    """Test cache functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("src.utils.cache.CACHE_ROOT_DIR")
    @patch("src.utils.cache.CONVERSATION_CACHE_DIR")
    @patch("src.utils.cache.FILE_CACHE_DIR")
    @patch("src.utils.cache.GIT_CACHE_DIR")
    def test_get_cache_directory(
        self, mock_git_cache, mock_file_cache, mock_conv_cache, mock_root_cache
    ):
        """Test get_cache_directory function creates all cache directories."""
        # Set up mock cache directories
        mock_root_cache.mkdir = Mock()
        mock_conv_cache.mkdir = Mock()
        mock_file_cache.mkdir = Mock()
        mock_git_cache.mkdir = Mock()

        # Call the function
        result = get_cache_directory()

        # Verify all directories are created with correct parameters
        mock_root_cache.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_conv_cache.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file_cache.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_git_cache.mkdir.assert_called_once_with(parents=True, exist_ok=True)

        # Verify the function returns the root cache directory
        assert result == mock_root_cache

    @patch("src.utils.cache.CACHE_ROOT_DIR")
    @patch("src.utils.cache.CONVERSATION_CACHE_DIR")
    @patch("src.utils.cache.FILE_CACHE_DIR")
    @patch("src.utils.cache.GIT_CACHE_DIR")
    def test_get_cache_directory_edge_cases(
        self, mock_git_cache, mock_file_cache, mock_conv_cache, mock_root_cache
    ):
        """Test get_cache_directory edge cases."""
        # Test when directories already exist (mkdir with exist_ok=True should handle this)
        mock_root_cache.mkdir = Mock()
        mock_conv_cache.mkdir = Mock()
        mock_file_cache.mkdir = Mock()
        mock_git_cache.mkdir = Mock()

        # Call twice to simulate directories already existing
        get_cache_directory()
        get_cache_directory()

        # Should be called twice since exist_ok=True
        assert mock_root_cache.mkdir.call_count == 2
        assert mock_conv_cache.mkdir.call_count == 2
        assert mock_file_cache.mkdir.call_count == 2
        assert mock_git_cache.mkdir.call_count == 2

    @patch("src.utils.cache.CACHE_ROOT_DIR")
    @patch("src.utils.cache.CONVERSATION_CACHE_DIR")
    @patch("src.utils.cache.FILE_CACHE_DIR")
    @patch("src.utils.cache.GIT_CACHE_DIR")
    def test_get_cache_directory_permission_error(
        self, mock_git_cache, mock_file_cache, mock_conv_cache, mock_root_cache
    ):
        """Test get_cache_directory handles permission errors gracefully."""
        # Simulate permission error on one of the directories
        mock_root_cache.mkdir.side_effect = PermissionError("Permission denied")

        # Should raise the permission error
        with pytest.raises(PermissionError):
            get_cache_directory()


class TestIntegrationScenarios:
    """Test integration scenarios and complex workflows."""

    def test_integration_workflow(self):
        """Test complete integration workflow."""
        # Test that get_cache_directory can be called multiple times safely
        result1 = get_cache_directory()
        result2 = get_cache_directory()

        # Should return the same directory both times
        assert result1 == result2
        assert isinstance(result1, Path)

    def test_error_recovery(self):
        """Test error recovery scenarios."""
        # Test that the function works normally after being imported
        result = get_cache_directory()
        assert isinstance(result, Path)
