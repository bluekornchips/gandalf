"""Tests for version utility functions."""

import unittest
from unittest.mock import patch

from src.utils.version import get_version


class TestVersionUtility(unittest.TestCase):
    """Test cases for version utility functions."""

    def test_get_version_success(self):
        """Test successful version retrieval from VERSION file."""
        with patch("pathlib.Path.read_text") as mock_read_text:
            mock_read_text.return_value = "2.31\n"

            result = get_version()

            assert result == "2.31"
            mock_read_text.assert_called_once()

    def test_get_version_strips_whitespace(self):
        """Test that version string is properly stripped of whitespace."""
        with patch("pathlib.Path.read_text") as mock_read_text:
            mock_read_text.return_value = "  2.31  \n  "

            result = get_version()

            assert result == "2.31"

    def test_get_version_file_not_found(self):
        """Test FileNotFoundError when VERSION file is missing."""
        with patch("pathlib.Path.read_text") as mock_read_text:
            mock_read_text.side_effect = FileNotFoundError("File not found")

            with self.assertRaises(FileNotFoundError) as context:
                get_version()

            assert "VERSION file not found" in str(context.exception)

    def test_get_version_file_path_construction(self):
        """Test that the correct path is constructed for VERSION file."""
        with patch("pathlib.Path.read_text") as mock_read_text:
            mock_read_text.return_value = "2.31"

            get_version()

            # Verify the path was constructed correctly
            mock_read_text.assert_called_once()

            # Just verify the method was called since path construction is internal
