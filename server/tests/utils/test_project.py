"""Test project utilities."""

import unittest.mock as mock
from pathlib import Path

import pytest

from src.utils.project import (
    ProjectContext,
    get_project_names,
    get_sanitized_project_name,
    _extract_project_names,
)

patch = mock.patch


class TestProjectContext:
    """Test ProjectContext dataclass and methods."""

    def test_from_path_no_sanitization_needed(self):
        """Test ProjectContext creation with clean project name."""
        project_path = Path("/path/to/fellowship-of-the-ring")

        with patch(
            "src.utils.project.AccessValidator.sanitize_project_name"
        ) as mock_sanitize:
            mock_sanitize.return_value = "fellowship-of-the-ring"

            context = ProjectContext.from_path(project_path)

            assert context.root == project_path
            assert context.raw_name == "fellowship-of-the-ring"
            assert context.sanitized_name == "fellowship-of-the-ring"
            assert context.was_sanitized is False
            mock_sanitize.assert_called_once_with("fellowship-of-the-ring")

    def test_from_path_with_sanitization(self):
        """Test ProjectContext creation with project name requiring sanitization."""
        project_path = Path("/path/to/the-one-ring!!!")

        with patch(
            "src.utils.project.AccessValidator.sanitize_project_name"
        ) as mock_sanitize:
            mock_sanitize.return_value = "the-one-ring"

            context = ProjectContext.from_path(project_path)

            assert context.root == project_path
            assert context.raw_name == "the-one-ring!!!"
            assert context.sanitized_name == "the-one-ring"
            assert context.was_sanitized is True
            mock_sanitize.assert_called_once_with("the-one-ring!!!")

    def test_get_transparency_fields_not_sanitized(self):
        """Test transparency fields when no sanitization occurred."""
        context = ProjectContext(
            root=Path("/path/to/moria"),
            raw_name="moria",
            sanitized_name="moria",
            was_sanitized=False,
        )

        fields = context.get_transparency_fields()

        assert fields == {"sanitized": False}

    def test_get_transparency_fields_sanitized(self):
        """Test transparency fields when sanitization occurred."""
        context = ProjectContext(
            root=Path("/path/to/isengard"),
            raw_name="isengard<script>",
            sanitized_name="isengard",
            was_sanitized=True,
        )

        fields = context.get_transparency_fields()

        expected = {
            "sanitized": True,
            "raw_project_name": "isengard<script>",
        }
        assert fields == expected

    def test_dataclass_attributes(self):
        """Test that ProjectContext has all expected attributes."""
        context = ProjectContext(
            root=Path("/path/to/rohan"),
            raw_name="rohan-riders",
            sanitized_name="rohan-riders",
            was_sanitized=False,
        )

        assert hasattr(context, "root")
        assert hasattr(context, "raw_name")
        assert hasattr(context, "sanitized_name")
        assert hasattr(context, "was_sanitized")
        assert isinstance(context.root, Path)
        assert isinstance(context.raw_name, str)
        assert isinstance(context.sanitized_name, str)
        assert isinstance(context.was_sanitized, bool)


class TestExtractProjectNamesHelper:
    """Test the _extract_project_names helper function."""

    def test_extract_project_names_basic(self):
        project_path = Path("/path/to/hobbiton")

        with patch(
            "src.utils.project.AccessValidator.sanitize_project_name"
        ) as mock_sanitize:
            mock_sanitize.return_value = "hobbiton"

            raw, sanitized, was_sanitized = _extract_project_names(project_path)

            assert raw == "hobbiton"
            assert sanitized == "hobbiton"
            assert was_sanitized is False
            mock_sanitize.assert_called_once_with("hobbiton")

    def test_extract_project_names_with_sanitization(self):
        project_path = Path("/path/to/bag-end$$$")

        with patch(
            "src.utils.project.AccessValidator.sanitize_project_name"
        ) as mock_sanitize:
            mock_sanitize.return_value = "bag-end"

            raw, sanitized, was_sanitized = _extract_project_names(project_path)

            assert raw == "bag-end$$$"
            assert sanitized == "bag-end"
            assert was_sanitized is True
            mock_sanitize.assert_called_once_with("bag-end$$$")

    def test_extract_project_names_type_error(self):
        with pytest.raises(TypeError, match="Expected Path object"):
            _extract_project_names("not-a-path")

    def test_extract_project_names_with_os_error(self):
        project_path = Path("/path/to/mordor")

        with patch(
            "src.utils.project.AccessValidator.sanitize_project_name"
        ) as mock_sanitize:
            mock_sanitize.side_effect = OSError("Path operation failed")

            with pytest.raises(ValueError, match="Failed to extract project names"):
                _extract_project_names(project_path)

    def test_extract_project_names_with_attribute_error(self):
        project_path = Path("/path/to/weathertop")

        # Mock the AccessValidator to raise AttributeError
        with patch(
            "src.utils.project.AccessValidator.sanitize_project_name"
        ) as mock_sanitize:
            mock_sanitize.side_effect = AttributeError("No name attribute")

            with pytest.raises(ValueError, match="Failed to extract project names"):
                _extract_project_names(project_path)

    def test_extract_project_names_consistency(self):
        project_path = Path("/path/to/rivendell")

        with patch(
            "src.utils.project.AccessValidator.sanitize_project_name"
        ) as mock_sanitize:
            mock_sanitize.return_value = "rivendell-safe"

            # Call multiple times to ensure consistency
            result1 = _extract_project_names(project_path)
            result2 = _extract_project_names(project_path)

            assert result1 == result2
            assert result1 == ("rivendell", "rivendell-safe", True)


class TestProjectUtilityFunctions:
    """Test standalone project utility functions."""

    def test_get_project_names_no_sanitization(self):
        """Test getting project names when no sanitization is needed."""
        project_path = Path("/path/to/gondor")

        with patch(
            "src.utils.project.AccessValidator.sanitize_project_name"
        ) as mock_sanitize:
            mock_sanitize.return_value = "gondor"

            raw_name, sanitized_name, was_sanitized = get_project_names(project_path)

            assert raw_name == "gondor"
            assert sanitized_name == "gondor"
            assert was_sanitized is False
            mock_sanitize.assert_called_once_with("gondor")

    def test_get_project_names_with_sanitization(self):
        """Test getting project names when sanitization is required."""
        project_path = Path("/path/to/bag-end$$$")

        with patch(
            "src.utils.project.AccessValidator.sanitize_project_name"
        ) as mock_sanitize:
            mock_sanitize.return_value = "bag-end"

            raw_name, sanitized_name, was_sanitized = get_project_names(project_path)

            assert raw_name == "bag-end$$$"
            assert sanitized_name == "bag-end"
            assert was_sanitized is True
            mock_sanitize.assert_called_once_with("bag-end$$$")

    def test_get_sanitized_project_name(self):
        """Test getting only the sanitized project name."""
        project_path = Path("/path/to/rivendell")

        with patch(
            "src.utils.project.AccessValidator.sanitize_project_name"
        ) as mock_sanitize:
            mock_sanitize.return_value = "rivendell-clean"

            result = get_sanitized_project_name(project_path)

            assert result == "rivendell-clean"
            mock_sanitize.assert_called_once_with("rivendell")

    def test_get_project_names_empty_name(self):
        """Test project names with empty directory name."""
        project_path = Path("/path/to/")

        with patch(
            "src.utils.project.AccessValidator.sanitize_project_name"
        ) as mock_sanitize:
            mock_sanitize.return_value = "unnamed"

            raw_name, sanitized_name, was_sanitized = get_project_names(project_path)

            assert raw_name == "to"  # Path("/path/to/").name returns "to"
            assert sanitized_name == "unnamed"
            assert was_sanitized is True
            mock_sanitize.assert_called_once_with("to")

    def test_get_project_names_complex_path(self):
        """Test project names with complex path structure."""
        project_path = Path("/very/deep/path/to/the-shire")

        with patch(
            "src.utils.project.AccessValidator.sanitize_project_name"
        ) as mock_sanitize:
            mock_sanitize.return_value = "the-shire"

            raw_name, sanitized_name, was_sanitized = get_project_names(project_path)

            assert raw_name == "the-shire"
            assert sanitized_name == "the-shire"
            assert was_sanitized is False


class TestProjectContextIntegration:
    """Test ProjectContext integration with security validation."""

    def test_project_context_handles_dangerous_names(self):
        """Test that ProjectContext properly handles dangerous project names."""
        dangerous_names = [
            "passwd",  # Will be the last component
            "script_tag",  # Simplified name
            "project_rm",  # Simplified name
            "project_null",  # Simplified name
        ]

        for dangerous_name in dangerous_names:
            project_path = Path(f"/path/to/{dangerous_name}")

            with patch(
                "src.utils.project.AccessValidator.sanitize_project_name"
            ) as mock_sanitize:
                mock_sanitize.return_value = "safe-project-name"

                context = ProjectContext.from_path(project_path)

                assert context.raw_name == dangerous_name
                assert context.sanitized_name == "safe-project-name"
                assert context.was_sanitized is True
                mock_sanitize.assert_called_once_with(dangerous_name)

    def test_project_context_transparency_workflow(self):
        """Test complete transparency workflow for sanitized projects."""
        project_path = Path("/path/to/minas-tirith<>")

        with patch(
            "src.utils.project.AccessValidator.sanitize_project_name"
        ) as mock_sanitize:
            mock_sanitize.return_value = "minas-tirith"

            # Create context
            context = ProjectContext.from_path(project_path)

            # Get transparency fields
            transparency = context.get_transparency_fields()

            assert context.was_sanitized is True
            assert transparency["sanitized"] is True
            assert transparency["raw_project_name"] == "minas-tirith<>"
            assert context.sanitized_name == "minas-tirith"

    def test_project_context_with_pathlib_edge_cases(self):
        """Test ProjectContext with various Path edge cases."""
        edge_cases = [
            Path("."),
            Path(".."),
            Path("/"),
            Path("~/projects/middle-earth"),
        ]

        for path_case in edge_cases:
            with patch(
                "src.utils.project.AccessValidator.sanitize_project_name"
            ) as mock_sanitize:
                mock_sanitize.return_value = "normalized-name"

                ProjectContext.from_path(path_case)

                assert mock_sanitize.call_count == 1
                mock_sanitize.assert_called_with(path_case.name)


class TestProjectSecurityIntegration:
    """Test project utilities integration with security validation."""

    def test_all_functions_use_security_validator(self):
        """Test that all project functions properly integrate with AccessValidator."""

        with patch(
            "src.utils.project.AccessValidator.sanitize_project_name"
        ) as mock_sanitize:
            mock_sanitize.return_value = "orthanc-clean"

            ProjectContext.from_path(Path("/path/to/orthanc"))
            assert mock_sanitize.call_count == 1

            for call in mock_sanitize.call_args_list:
                assert call[0][0] == "orthanc"

    def test_security_validator_sanitization_consistency(self):
        """Test project utilities handle AccessValidator responses consistently."""
        # Test with different sanitization scenarios
        sanitization_scenarios = [
            ("mount-doom", "mount-doom", False),  # No change needed
            ("mount-doom!!!", "mount-doom", True),  # Sanitization needed
            ("", "unnamed-project", True),  # Empty name
            ("../../../etc", "safe-project", True),  # Dangerous path
        ]

        for (
            raw_name,
            sanitized_name,
            should_be_sanitized,
        ) in sanitization_scenarios:
            test_path = Path(f"/path/to/{raw_name}")

            with patch(
                "src.utils.project.AccessValidator.sanitize_project_name"
            ) as mock_sanitize:
                mock_sanitize.return_value = sanitized_name

                # Test ProjectContext
                context = ProjectContext.from_path(test_path)
                assert context.was_sanitized == should_be_sanitized

                # Test utility functions
                _, _, was_sanitized = get_project_names(test_path)
                assert was_sanitized == should_be_sanitized

                result = get_sanitized_project_name(test_path)
                assert result == sanitized_name


class TestEnhancedErrorHandling:
    """Test enhanced error handling in refactored code."""

    def test_helper_function_type_validation(self):
        invalid_inputs = [None, 123, "string", [], {}]

        for invalid_input in invalid_inputs:
            with pytest.raises(TypeError, match="Expected Path object"):
                _extract_project_names(invalid_input)

    def test_utility_functions_preserve_type_errors(self):
        with pytest.raises(TypeError, match="Expected Path object"):
            get_project_names("not-a-path")

        with pytest.raises(TypeError, match="Expected Path object"):
            get_sanitized_project_name(123)

    def test_helper_function_error_message_quality(self):
        try:
            _extract_project_names("invalid")
        except TypeError as e:
            assert "Expected Path object" in str(e)
            assert "str" in str(e)

    def test_project_context_error_handling_preserves_type_errors(self):
        with pytest.raises(TypeError, match="Expected Path object"):
            ProjectContext.from_path(None)

        with pytest.raises(TypeError, match="Expected Path object"):
            ProjectContext.from_path("string-path")

    def test_value_error_handling_with_valid_types(self):
        project_path = Path("/path/to/fangorn")

        with patch(
            "src.utils.project.AccessValidator.sanitize_project_name"
        ) as mock_sanitize:
            mock_sanitize.side_effect = OSError("Sanitization failed")

            with pytest.raises(ValueError, match="Failed to extract project names"):
                _extract_project_names(project_path)

            with pytest.raises(ValueError, match="Failed to get project names"):
                get_project_names(project_path)

            with pytest.raises(
                ValueError, match="Failed to get sanitized project name"
            ):
                get_sanitized_project_name(project_path)

            with pytest.raises(ValueError, match="Failed to create ProjectContext"):
                ProjectContext.from_path(project_path)


class TestProjectErrorHandling:
    """Test error handling in project utilities."""

    def test_project_context_with_security_validator_exception(self):
        """Test ProjectContext when AccessValidator raises an exception."""
        project_path = Path("/path/to/weathertop")

        with patch(
            "src.utils.project.AccessValidator.sanitize_project_name"
        ) as mock_sanitize:
            mock_sanitize.side_effect = Exception("Validation failed")

            with pytest.raises(Exception):
                ProjectContext.from_path(project_path)

    def test_utility_functions_with_security_validator_exception(self):
        """Test utility functions when AccessValidator raises an exception."""
        project_path = Path("/path/to/helms-deep")

        with patch(
            "src.utils.project.AccessValidator.sanitize_project_name"
        ) as mock_sanitize:
            mock_sanitize.side_effect = Exception("Validation failed")

            with pytest.raises(Exception):
                get_project_names(project_path)

            with pytest.raises(Exception):
                get_sanitized_project_name(project_path)

    def test_project_context_with_invalid_path_type(self):
        """Test ProjectContext with invalid path types."""
        invalid_paths = [None, 123, [], {}]

        for invalid_path in invalid_paths:
            with pytest.raises((TypeError, AttributeError)):
                ProjectContext.from_path(invalid_path)
