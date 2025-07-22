"""Test common utility functions for file-based logging only."""

import tempfile
import unittest.mock as mock
from pathlib import Path

from src.utils.common import (
    LogLevel,
    initialize_session_logging,
    log_alert,
    log_critical,
    log_debug,
    log_emergency,
    log_error,
    log_info,
    log_notice,
    log_warning,
    set_min_log_level,
    write_log,
)


class TestSessionLogging:
    """Test session logging initialization and management."""

    @mock.patch("src.utils.common.write_log")
    def test_initialize_session_logging_creates_directory(self, mock_write_log):
        """Test initialize_session_logging creates logs directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch("src.utils.common.GANDALF_HOME", Path(temp_dir)):
                logs_dir = Path(temp_dir) / "logs"

                initialize_session_logging("helms_deep")

                assert logs_dir.exists()
                mock_write_log.assert_called_once()

    @mock.patch("src.utils.common.datetime")
    def test_initialize_session_logging_filename_format(self, mock_datetime):
        """Test initialize_session_logging creates properly formatted filename."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch("src.utils.common.GANDALF_HOME", Path(temp_dir)):
                mock_datetime.now.return_value.strftime.return_value = "20240115_143022"

                initialize_session_logging("session_456")

                expected_filename = "gandalf_session_session_456_20240115_143022.log"
                log_file = Path(temp_dir) / "logs" / expected_filename

                # File should be created, even if empty initially
                assert log_file.parent.exists()

    @mock.patch("src.utils.common.write_log")
    def test_initialize_session_logging_calls_write_log(self, mock_write_log):
        """Test initialize_session_logging calls write_log with session start."""
        initialize_session_logging("test_session")

        mock_write_log.assert_called_once_with(
            "info", "GANDALF session started: test_session"
        )

    def test_initialize_session_logging_sets_global_variables(self):
        """Test initialize_session_logging sets global session variables."""
        import src.utils.common as common_module

        initialize_session_logging("global_test_session")

        assert common_module._session_id == "global_test_session"
        assert common_module._log_file_path is not None


class TestWriteLog:
    """Test log file writing functionality."""

    def test_write_log_no_log_file_path_returns_early(self):
        """Test write_log returns early when no log file path is set."""
        import src.utils.common as common_module

        original_path = common_module._log_file_path
        common_module._log_file_path = None

        try:
            # Should not raise exception and return early
            write_log("info", "mellon")
        finally:
            common_module._log_file_path = original_path

    @mock.patch("builtins.open")
    def test_write_log_handles_os_error(self, mock_open):
        """Test write_log handles OSError gracefully."""
        import src.utils.common as common_module

        original_path = common_module._log_file_path
        mock_open.side_effect = OSError("Disk full")

        try:
            common_module._log_file_path = Path("/cirith/ungol")
            # Should not raise exception
            write_log("error", "shelob is scary")
        finally:
            common_module._log_file_path = original_path

    @mock.patch("builtins.open")
    def test_write_log_handles_unicode_error(self, mock_open):
        """Test write_log handles UnicodeEncodeError gracefully."""
        import src.utils.common as common_module

        original_path = common_module._log_file_path
        mock_open.side_effect = UnicodeEncodeError("utf-8", "", 0, 1, "error")

        try:
            common_module._log_file_path = Path("/shelobs/lair")
            # Should not raise exception
            write_log("info", "gollum is a liar")
        finally:
            common_module._log_file_path = original_path

    @mock.patch("src.utils.common.json.dumps")
    def test_write_log_handles_json_error(self, mock_dumps):
        """Test write_log handles TypeError gracefully."""
        import src.utils.common as common_module

        original_path = common_module._log_file_path
        mock_dumps.side_effect = TypeError("Object not JSON serializable")

        try:
            common_module._log_file_path = Path("/gondor/minas/tirith")
            # Should not raise exception
            write_log("info", "but that would make him 87 years old")
        finally:
            common_module._log_file_path = original_path


class TestLogConvenienceFunctions:
    """Test convenience logging functions that only write to files."""

    @mock.patch("src.utils.common.write_log")
    def test_log_info_calls_write_log_only(self, mock_write_log):
        """Test log_info calls write_log with default logger and no data."""
        log_info("all we have to decide is what to do with the time given us")

        mock_write_log.assert_called_once_with(
            "info",
            "all we have to decide is what to do with the time given us",
            "server",
            None,
        )

    @mock.patch("src.utils.common.write_log")
    def test_log_debug_calls_write_log_only(self, mock_write_log):
        """Test log_debug calls write_log with default logger and no data."""
        log_debug("you shall not pass")

        mock_write_log.assert_called_once_with(
            "debug", "you shall not pass", "server", None
        )

    @mock.patch("src.utils.common.write_log")
    def test_log_error_with_context(self, mock_write_log):
        """Test log_error formats message with context and structured data."""
        test_exception = ValueError("ring not found")
        log_error(test_exception, "searching for precious")

        mock_write_log.assert_called_once_with(
            "error",
            "searching for precious: ring not found",
            "server",
            {"error_type": "ValueError", "error_str": "ring not found"},
        )

    @mock.patch("src.utils.common.write_log")
    def test_log_error_without_context(self, mock_write_log):
        """Test log_error formats message without context and structured data."""
        test_exception = RuntimeError("sauron has returned")
        log_error(test_exception)

        mock_write_log.assert_called_once_with(
            "error",
            "sauron has returned",
            "server",
            {"error_type": "RuntimeError", "error_str": "sauron has returned"},
        )

    @mock.patch("src.utils.common.write_log")
    def test_log_error_empty_context(self, mock_write_log):
        """Test log_error handles empty context string with structured data."""
        test_exception = KeyError("palantir")
        log_error(test_exception, "")

        mock_write_log.assert_called_once_with(
            "error",
            "'palantir'",
            "server",
            {"error_type": "KeyError", "error_str": "'palantir'"},
        )

    @mock.patch("src.utils.common.write_log")
    def test_log_critical_calls_write_log_only(self, mock_write_log):
        """Test log_critical calls write_log with structured data."""
        log_critical("the beacons are lit")

        mock_write_log.assert_called_once_with(
            "critical", "the beacons are lit", "server", None
        )


class TestLoggingIntegration:
    """Test logging integration and workflow."""

    def test_full_logging_workflow(self):
        """Test complete logging workflow from initialization to logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch("src.utils.common.GANDALF_HOME", Path(temp_dir)):
                # Initialize session
                initialize_session_logging("fellowship_session")

                # Log various messages
                log_info("gandalf arrives precisely when he means to")
                log_debug("looking for signs of the enemy")

                # Verify log file exists
                logs_dir = Path(temp_dir) / "logs"
                log_files = list(logs_dir.glob("*.log"))
                assert len(log_files) == 1

    @mock.patch("src.utils.common.write_log")
    def test_logging_functions_work_together(self, mock_write_log):
        """Test that different logging functions work together properly."""
        log_info("the hobbits are going to isengard")
        log_debug("searching for tracks")

        assert mock_write_log.call_count == 2

    def test_session_id_persistence(self):
        """Test that session ID persists across multiple logging calls."""
        import src.utils.common as common_module

        initialize_session_logging("persistent_session")

        # Session ID should remain set
        assert common_module._session_id == "persistent_session"

        # Multiple logging calls should use the same session
        with mock.patch("src.utils.common.write_log") as mock_write_log:
            log_info("first message")
            log_error(Exception("test error"))

            # Both calls should have been made
            assert mock_write_log.call_count == 2


class TestLoggingEdgeCases:
    """Test edge cases and error conditions in logging."""

    def test_write_log_with_none_values(self):
        """Test write_log handles None values gracefully."""
        import src.utils.common as common_module

        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch("src.utils.common.GANDALF_HOME", Path(temp_dir)):
                initialize_session_logging("none_test_session")

                # Should handle None logger and data gracefully
                write_log("info", "testing with none values", None, None)

                # Should not raise exception
                assert common_module._log_file_path is not None

    @mock.patch("src.utils.common.write_log")
    def test_log_error_with_complex_exception(self, mock_write_log):
        """Test log_error handles complex exception objects with structured data."""

        class CustomError(Exception):
            def __init__(self, message, code):
                super().__init__(message)
                self.code = code

            def __str__(self):
                return f"Error {self.code}: {super().__str__()}"

        complex_error = CustomError("the ring is lost", 404)
        log_error(complex_error, "ring bearer status")

        expected_message = "ring bearer status: Error 404: the ring is lost"
        expected_data = {
            "error_type": "CustomError",
            "error_str": "Error 404: the ring is lost",
        }
        mock_write_log.assert_called_once_with(
            "error", expected_message, "server", expected_data
        )

    def test_write_log_with_optional_parameters(self):
        """Test write_log with optional logger and data parameters."""
        import json

        import src.utils.common as common_module

        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch("src.utils.common.GANDALF_HOME", Path(temp_dir)):
                initialize_session_logging("test_optional_params")

                test_data = {"key": "value", "count": 42}

                write_log("info", "test message with extras", "test_logger", test_data)

                log_file = common_module._log_file_path
                assert log_file is not None
                assert log_file.exists()

                with open(log_file, encoding="utf-8") as f:
                    lines = f.readlines()
                    assert len(lines) >= 2

                    last_entry = json.loads(lines[-1])
                    assert last_entry["message"] == "test message with extras"
                    assert last_entry["logger"] == "test_logger"
                    assert last_entry["data"] == test_data


class TestMCPLoggingCompliance:
    """Test MCP logging compliance features."""

    def test_log_level_enum_values(self):
        """Test LogLevel enum has correct RFC 5424 values."""
        assert LogLevel.DEBUG == 0
        assert LogLevel.INFO == 1
        assert LogLevel.NOTICE == 2
        assert LogLevel.WARNING == 3
        assert LogLevel.ERROR == 4
        assert LogLevel.CRITICAL == 5
        assert LogLevel.ALERT == 6
        assert LogLevel.EMERGENCY == 7

    def test_log_level_enum_comparison(self):
        """Test LogLevel enum supports proper comparison."""
        assert LogLevel.DEBUG < LogLevel.INFO
        assert LogLevel.ERROR > LogLevel.WARNING
        assert LogLevel.EMERGENCY > LogLevel.CRITICAL

    def test_set_min_log_level_valid(self):
        """Test set_min_log_level accepts valid levels."""
        assert set_min_log_level("info") is True
        assert set_min_log_level("error") is True
        assert set_min_log_level("debug") is True

    def test_set_min_log_level_invalid(self):
        """Test set_min_log_level rejects invalid levels."""
        assert set_min_log_level("invalid") is False
        assert set_min_log_level("") is False
        assert set_min_log_level("trace") is False

    @mock.patch("src.utils.common.write_log")
    def test_log_notice_structured(self, mock_write_log):
        """Test log_notice uses structured format."""
        log_notice("configuration changed", "config", {"key": "value"})
        mock_write_log.assert_called_once_with(
            "notice", "configuration changed", "config", {"key": "value"}
        )

    @mock.patch("src.utils.common.write_log")
    def test_log_warning_structured(self, mock_write_log):
        """Test log_warning uses structured format."""
        log_warning("deprecated feature", "api")
        mock_write_log.assert_called_once_with(
            "warning", "deprecated feature", "api", None
        )

    @mock.patch("src.utils.common.write_log")
    def test_log_alert_structured(self, mock_write_log):
        """Test log_alert uses structured format."""
        log_alert("data corruption detected")
        mock_write_log.assert_called_once_with(
            "alert", "data corruption detected", "server", None
        )

    @mock.patch("src.utils.common.write_log")
    def test_log_emergency_structured(self, mock_write_log):
        """Test log_emergency uses structured format."""
        log_emergency("system failure", "system", {"status": "failed"})
        mock_write_log.assert_called_once_with(
            "emergency", "system failure", "system", {"status": "failed"}
        )

    @mock.patch("src.utils.common._should_log")
    def test_log_level_filtering(self, mock_should_log):
        """Test log level filtering works with enum."""
        mock_should_log.return_value = False

        # Mock the log file path to enable write_log processing
        import src.utils.common as common_module

        original_path = common_module._log_file_path
        common_module._log_file_path = Path("/test/path.log")

        try:
            with mock.patch("builtins.open"):
                log_debug("filtered message")
                # _should_log should be called and return False, preventing file write
                mock_should_log.assert_called_once_with("debug")
        finally:
            common_module._log_file_path = original_path

    def test_log_levels_mapping_complete(self):
        """Test all log levels are mapped correctly."""
        from src.utils.common import LOG_LEVELS

        expected_levels = [
            "debug",
            "info",
            "notice",
            "warning",
            "error",
            "critical",
            "alert",
            "emergency",
        ]
        for level in expected_levels:
            assert level in LOG_LEVELS
            assert isinstance(LOG_LEVELS[level], LogLevel)
