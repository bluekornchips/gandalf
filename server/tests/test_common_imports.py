"""
Comprehensive test suite for common_imports.py module.

Tests the import consolidation strategy and ensures all common imports
are accessible and work correctly across the codebase.
"""

import sys
from pathlib import Path
from unittest import mock

import pytest


class TestCommonImportsAvailability:
    """Test that all imports defined in common_imports are accessible."""

    def test_standard_library_imports(self):
        """Test standard library imports are available."""
        from src.common_imports import Any, Optional, Path, json, os, sys, time

        # Verify these are the actual modules/types
        assert json.__name__ == "json"
        assert os.__name__ == "os"
        assert sys.__name__ == "sys"
        assert time.__name__ == "time"
        assert Path.__name__ == "Path"  # Path class from pathlib
        assert "Any" in str(Any)
        assert "Union" in str(Optional) or "Optional" in str(Optional)

    def test_core_constants_imports(self):
        """Test core constants are available."""
        from src.common_imports import (
            DATABASE_OPERATION_TIMEOUT,
            DATABASE_SCANNER_TIMEOUT,
            GANDALF_HOME,
            MCP_CACHE_TTL,
            MCP_PROTOCOL_VERSION,
            PRIORITY_NEUTRAL_SCORE,
            SERVER_CAPABILITIES,
            SERVER_INFO,
        )

        # Verify these are the expected types
        assert isinstance(DATABASE_OPERATION_TIMEOUT, int | float)
        assert isinstance(DATABASE_SCANNER_TIMEOUT, int | float)
        assert isinstance(GANDALF_HOME, str | Path)
        assert isinstance(MCP_CACHE_TTL, int | float)
        assert isinstance(MCP_PROTOCOL_VERSION, str)
        assert isinstance(PRIORITY_NEUTRAL_SCORE, int | float)
        assert isinstance(SERVER_CAPABILITIES, dict)
        assert isinstance(SERVER_INFO, dict)

    def test_conversation_config_imports(self):
        """Test conversation configuration constants are available."""
        from src.common_imports import (
            CONVERSATION_DEFAULT_LIMIT,
            CONVERSATION_DEFAULT_LOOKBACK_DAYS,
            CONVERSATION_MAX_LIMIT,
            CONVERSATION_MAX_LOOKBACK_DAYS,
            CONVERSATION_TEXT_EXTRACTION_LIMIT,
            TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS,
        )

        # Verify these are integers
        assert isinstance(CONVERSATION_DEFAULT_LIMIT, int)
        assert isinstance(CONVERSATION_DEFAULT_LOOKBACK_DAYS, int)
        assert isinstance(CONVERSATION_MAX_LIMIT, int)
        assert isinstance(CONVERSATION_MAX_LOOKBACK_DAYS, int)
        assert isinstance(CONVERSATION_TEXT_EXTRACTION_LIMIT, int)
        assert isinstance(TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS, int)

    def test_enum_imports(self):
        """Test enum imports are available."""
        from src.common_imports import ErrorCodes

        # Verify ErrorCodes is an enum
        assert hasattr(ErrorCodes, "__members__")
        assert len(ErrorCodes.__members__) > 0

    def test_utility_function_imports(self):
        """Test utility functions are available and callable."""
        from src.common_imports import (
            format_json_response,
            initialize_session_logging,
            log_debug,
            log_error,
            log_info,
        )

        # Verify these are callable functions
        assert callable(format_json_response)
        assert callable(initialize_session_logging)
        assert callable(log_debug)
        assert callable(log_error)
        assert callable(log_info)

    def test_access_control_imports(self):
        """Test access control imports are available."""
        from src.common_imports import AccessValidator, create_mcp_tool_result

        # Verify AccessValidator is a class and create_mcp_tool_result is callable
        assert isinstance(AccessValidator, type)
        assert callable(create_mcp_tool_result)

    def test_performance_imports(self):
        """Test performance utility imports are available."""
        from src.common_imports import get_duration, log_operation_time, start_timer

        # Verify these are callable functions
        assert callable(get_duration)
        assert callable(log_operation_time)
        assert callable(start_timer)

    def test_jsonrpc_imports(self):
        """Test JSON-RPC utility imports are available."""
        from src.common_imports import create_error_response, create_success_response

        # Verify these are callable functions
        assert callable(create_error_response)
        assert callable(create_success_response)


class TestCommonImportsModuleStructure:
    """Test the module structure and __all__ export."""

    def test_all_exports_defined(self):
        """Test that __all__ includes all expected exports."""
        import src.common_imports as common_imports

        expected_exports = {
            # Standard library
            "json",
            "os",
            "sys",
            "time",
            "Path",
            "Any",
            "Optional",
            # Core constants
            "DATABASE_OPERATION_TIMEOUT",
            "DATABASE_SCANNER_TIMEOUT",
            "GANDALF_HOME",
            "MCP_CACHE_TTL",
            "MCP_PROTOCOL_VERSION",
            "PRIORITY_NEUTRAL_SCORE",
            "SERVER_CAPABILITIES",
            "SERVER_INFO",
            # Conversation config
            "CONVERSATION_DEFAULT_LIMIT",
            "CONVERSATION_DEFAULT_LOOKBACK_DAYS",
            "CONVERSATION_MAX_LIMIT",
            "CONVERSATION_MAX_LOOKBACK_DAYS",
            "CONVERSATION_TEXT_EXTRACTION_LIMIT",
            "TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS",
            # Enums
            "ErrorCodes",
            # Common utilities
            "format_json_response",
            "initialize_session_logging",
            "log_debug",
            "log_error",
            "log_info",
            # Access control
            "AccessValidator",
            "create_mcp_tool_result",
            # Performance
            "get_duration",
            "log_operation_time",
            "start_timer",
            # JSON-RPC
            "create_error_response",
            "create_success_response",
        }

        actual_exports = set(common_imports.__all__)
        assert actual_exports == expected_exports

    def test_all_exports_accessible(self):
        """Test that all items in __all__ are actually accessible."""
        import src.common_imports as common_imports

        for export_name in common_imports.__all__:
            assert hasattr(common_imports, export_name), f"{export_name} not accessible"

    def test_star_import_works(self):
        """Test that star import brings in expected symbols."""
        # This needs to be done in a subprocess to avoid polluting current namespace
        import subprocess

        test_code = """
from src.common_imports import *
# Test a few key imports work
assert 'json' in globals()
assert 'Path' in globals()
assert 'log_info' in globals()
assert 'AccessValidator' in globals()
print("Star import test passed")
"""

        result = subprocess.run(
            [sys.executable, "-c", test_code],
            cwd=".",  # We're already in the server directory
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Star import failed: {result.stderr}"
        assert "Star import test passed" in result.stdout


class TestImportConsolidationIntegration:
    """Test that import consolidation works correctly in updated files."""

    def test_project_operations_uses_common_imports(self):
        """Test that project_operations.py successfully uses common imports."""
        # Import the module to ensure it loads without errors
        from src.tool_calls.project_operations import (
            handle_get_project_info,
            handle_get_server_version,
        )

        # Verify functions are callable
        assert callable(handle_get_project_info)
        assert callable(handle_get_server_version)

    def test_conversation_filtering_uses_common_imports(self):
        """Test that conversation_filtering.py successfully uses common imports."""
        from src.core.conversation_filtering import (
            ConversationFilter,
            apply_conversation_filtering,
        )

        # Verify classes and functions are accessible
        assert isinstance(ConversationFilter, type)
        assert callable(apply_conversation_filtering)

    def test_context_optimization_uses_common_imports(self):
        """Test that context_optimization.py successfully uses common imports."""
        from src.tool_calls.context_optimization import (
            calculate_response_size,
            optimize_context_keywords,
        )

        # Verify functions are callable
        assert callable(optimize_context_keywords)
        assert callable(calculate_response_size)

    def test_updated_files_import_consistency(self):
        """Test that updated files maintain import consistency."""
        # Files that have been updated to use common imports
        updated_files = [
            "src.tool_calls.project_operations",
            "src.core.conversation_filtering",
            "src.tool_calls.context_optimization",
        ]

        for module_name in updated_files:
            # Import the module
            module = __import__(module_name, fromlist=[""])

            # Verify the module loaded successfully
            assert module is not None
            assert hasattr(module, "__file__")


class TestCommonImportsFunctionality:
    """Test that imported utilities work as expected."""

    def test_logging_functions_work(self):
        """Test that logging functions from common imports work."""
        from src.common_imports import log_debug, log_error, log_info

        # These should not raise exceptions when called
        with mock.patch("src.utils.common.write_log") as mock_write:
            log_info("Test info message")
            log_debug("Test debug message")
            log_error(Exception("Test error"), "test_context")

            # Verify write_log was called
            assert mock_write.call_count >= 3

    def test_performance_functions_work(self):
        """Test that performance functions from common imports work."""
        from src.common_imports import get_duration, log_operation_time, start_timer

        # Test timer functions
        start_time = start_timer()
        assert isinstance(start_time, float)
        assert start_time > 0

        duration = get_duration(start_time)
        assert isinstance(duration, float)
        assert duration >= 0

        # Test operation logging
        with mock.patch("src.utils.common.write_log") as mock_write:
            log_operation_time("test_operation", start_time)
            mock_write.assert_called()

    def test_json_functions_work(self):
        """Test that JSON functions from common imports work."""
        from src.common_imports import format_json_response

        test_data = {"test": "data", "number": 42}
        result = format_json_response(test_data)

        assert isinstance(result, str)
        assert "test" in result
        assert "data" in result
        assert "42" in result

    def test_access_validator_works(self):
        """Test that AccessValidator from common imports works."""
        from src.common_imports import AccessValidator

        # Test basic validation functionality
        validator = AccessValidator()

        # Test string validation (should not raise for reasonable input)
        try:
            validator.validate_string(
                "test_string", field_name="test_field", required=True, max_length=100
            )
        except Exception as e:
            pytest.fail(f"AccessValidator.validate_string failed: {e}")

    def test_path_operations_work(self):
        """Test that Path operations from common imports work."""
        from src.common_imports import Path

        # Test basic Path functionality
        test_path = Path("/tmp/test")
        assert isinstance(test_path, Path)
        assert str(test_path) == "/tmp/test"


class TestImportConsolidationBenefits:
    """Test that import consolidation provides expected benefits."""

    def test_import_line_reduction(self):
        """Test that updated files have fewer import lines than before consolidation."""
        # This is a meta-test checking the files have streamlined imports
        updated_files = [
            "src/tool_calls/project_operations.py",
            "src/core/conversation_filtering.py",
            "src/tool_calls/context_optimization.py",
        ]

        for file_path in updated_files:
            with open(file_path) as f:
                content = f.read()

            # Check that common_imports is used
            assert "from src.common_imports import" in content

            # Count import lines (rough heuristic)
            import_lines = [
                line
                for line in content.split("\n")
                if line.strip().startswith(("import ", "from "))
            ]

            # Should have reasonable number of import lines (not excessive)
            assert len(import_lines) < 20, (
                f"{file_path} has too many import lines: {len(import_lines)}"
            )

    def test_no_duplicate_imports_in_common_module(self):
        """Test that common_imports.py itself doesn't have duplicate imports."""
        with open("src/common_imports.py") as f:
            content = f.read()

        import_lines = [
            line.strip()
            for line in content.split("\n")
            if line.strip().startswith(("import ", "from "))
        ]

        # Check for duplicate import statements
        unique_imports = set(import_lines)
        assert len(unique_imports) == len(import_lines), (
            "Duplicate import statements found"
        )

    def test_import_consolidation_consistency(self):
        """Test that the same utility is imported consistently across files."""
        # Files using common imports should import consistently
        from src.core.conversation_filtering import log_info as filter_log_info
        from src.tool_calls.context_optimization import log_info as opt_log_info
        from src.tool_calls.project_operations import log_info as proj_log_info

        # Should be the same function object
        assert proj_log_info is filter_log_info
        assert filter_log_info is opt_log_info


if __name__ == "__main__":
    pytest.main([__file__])
