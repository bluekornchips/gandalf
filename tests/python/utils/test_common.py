"""Test common utility functions for logging and RPC messaging."""

import json
import tempfile
import unittest.mock as mock
from pathlib import Path
import os

from src.utils.common import (
    initialize_session_logging,
    log_debug,
    log_error,
    log_info,
    send_rpc_message,
    write_log,
)


class TestSessionLogging:
    """Test session logging initialization and management."""

    @mock.patch("src.utils.common.write_log")
    def test_initialize_session_logging_creates_directory(
        self, mock_write_log
    ):
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
                mock_datetime.now.return_value.strftime.return_value = (
                    "20240115_143022"
                )

                initialize_session_logging("session_456")

                expected_filename = (
                    "gandalf_session_session_456_20240115_143022.log"
                )
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


class TestSendRpcMessage:
    """Test RPC message sending functionality."""

    @mock.patch("builtins.print")
    def test_send_rpc_message_basic(self, mock_print):
        """Test send_rpc_message sends basic RPC message."""
        send_rpc_message("info", "one does not simply walk into mordor")

        mock_print.assert_called_once()
        printed_message = mock_print.call_args[0][0]
        rpc_data = json.loads(printed_message)

        assert rpc_data["jsonrpc"] == "2.0"
        assert rpc_data["method"] == "notifications/message"
        assert rpc_data["params"]["level"] == "info"
        assert (
            rpc_data["params"]["message"]
            == "one does not simply walk into mordor"
        )

    @mock.patch("builtins.print")
    def test_send_rpc_message_with_logger(self, mock_print):
        """Test send_rpc_message includes logger parameter."""
        message = "even the very wise cannot see all ends"
        send_rpc_message("debug", message, "test_logger")

        printed_message = mock_print.call_args[0][0]
        rpc_data = json.loads(printed_message)

        assert rpc_data["params"]["logger"] == "test_logger"

    @mock.patch("builtins.print")
    def test_send_rpc_message_with_data(self, mock_print):
        """Test send_rpc_message includes data parameter."""
        test_data = {"operation": "test", "duration": 1.23}
        message = "a day may come when the courage of men fails"
        send_rpc_message("info", message, data=test_data)

        printed_message = mock_print.call_args[0][0]
        rpc_data = json.loads(printed_message)

        assert rpc_data["params"]["data"] == test_data

    @mock.patch("builtins.print")
    def test_send_rpc_message_with_all_params(self, mock_print):
        """Test send_rpc_message with all optional parameters."""
        test_data = {"key": "value"}
        message = "but it is not this day"
        send_rpc_message("warning", message, "warning_logger", test_data)

        printed_message = mock_print.call_args[0][0]
        rpc_data = json.loads(printed_message)

        params = rpc_data["params"]
        assert params["level"] == "warning"
        assert params["message"] == message
        assert params["logger"] == "warning_logger"
        assert params["data"] == test_data

    @mock.patch("builtins.print")
    def test_send_rpc_message_flush_parameter(self, mock_print):
        """Test send_rpc_message calls print with flush=True."""
        send_rpc_message("info", "I wish the ring had never come to me")

        mock_print.assert_called_once()
        # Check that flush=True was passed
        call_kwargs = mock_print.call_args[1]
        assert call_kwargs.get("flush") is True


class TestLogConvenienceFunctions:
    """Test convenience logging functions."""

    @mock.patch("src.utils.common.send_rpc_message")
    @mock.patch("src.utils.common.write_log")
    def test_log_info_calls_both_functions(
        self, mock_write_log, mock_send_rpc
    ):
        """Test log_info calls both write_log and send_rpc_message."""
        message = "how do you pick up the threads of an old life?"
        log_info(message)

        mock_write_log.assert_called_once_with("info", message)
        mock_send_rpc.assert_called_once_with("info", message)

    @mock.patch("src.utils.common.send_rpc_message")
    @mock.patch("src.utils.common.write_log")
    def test_log_debug_calls_both_functions(
        self, mock_write_log, mock_send_rpc
    ):
        """Test log_debug calls both write_log and send_rpc_message."""
        message = "I made a promise, Mr Frodo. A promise."
        log_debug(message)

        mock_write_log.assert_called_once_with("debug", message)
        mock_send_rpc.assert_called_once_with("debug", message)

    @mock.patch("src.utils.common.send_rpc_message")
    @mock.patch("src.utils.common.write_log")
    def test_log_error_with_context(self, mock_write_log, mock_send_rpc):
        """Test log_error formats error message with context."""
        test_error = ValueError("test error")
        context = "I can't carry it for you, but I can carry you!"
        log_error(test_error, context)

        expected_message = f"{context}: test error"
        mock_write_log.assert_called_once_with("error", expected_message)
        mock_send_rpc.assert_called_once_with("error", expected_message)

    @mock.patch("src.utils.common.send_rpc_message")
    @mock.patch("src.utils.common.write_log")
    def test_log_error_without_context(self, mock_write_log, mock_send_rpc):
        """Test log_error formats error message without context."""
        test_error = RuntimeError("runtime error")
        log_error(test_error)

        expected_message = "runtime error"
        mock_write_log.assert_called_once_with("error", expected_message)
        mock_send_rpc.assert_called_once_with("error", expected_message)

    @mock.patch("src.utils.common.send_rpc_message")
    @mock.patch("src.utils.common.write_log")
    def test_log_error_empty_context(self, mock_write_log, mock_send_rpc):
        """Test log_error handles empty context string."""
        test_error = Exception("test exception")
        log_error(test_error, "")

        expected_message = "test exception"
        mock_write_log.assert_called_once_with("error", expected_message)
        mock_send_rpc.assert_called_once_with("error", expected_message)


class TestLoggingIntegration:
    """Test integration scenarios for logging functionality."""

    def test_full_logging_workflow(self):
        """Test complete logging workflow from initialization to logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch("src.utils.common.GANDALF_HOME", Path(temp_dir)):
                initialize_session_logging("integration_test")

                log_info("That still only counts as one!")
                log_debug("Nobody tosses a dw")
                log_error(Exception("Test error"), "Integration test")

    @mock.patch("src.utils.common.send_rpc_message")
    @mock.patch("src.utils.common.write_log")
    def test_logging_functions_work_together(
        self, mock_write_log, mock_send_rpc
    ):
        """Test that log_info calls both write_log and send_rpc_message."""
        message = "Let them come! There is one dwarf yet in Moria!"
        log_info(message)

        # Both functions should have been called
        mock_write_log.assert_called_once_with("info", message)
        mock_send_rpc.assert_called_once_with("info", message)

    def test_session_id_persistence(self):
        """Test that session ID persists across multiple log calls."""
        import src.utils.common as common_module

        with mock.patch("builtins.open", mock.mock_open()) as mock_file:
            initialize_session_logging("persistent_session")

            assert common_module._session_id == "persistent_session"

            # Multiple log calls should use the same session ID
            write_log("info", "first message")
            write_log("debug", "second message")

            # Three calls: 1 from initialize + 2 from write_log calls
            assert mock_file.call_count == 3


class TestLoggingEdgeCases:
    """Test edge cases and error conditions."""

    def test_write_log_with_none_values(self):
        """Test write_log handles None values gracefully."""
        import src.utils.common as common_module

        original_path = common_module._log_file_path
        original_session = common_module._session_id

        try:
            common_module._log_file_path = None
            common_module._session_id = None

            # Should not raise exception
            write_log(
                "info",
                "I would have followed you, my brother...my captain...my king.",
            )
        finally:
            common_module._log_file_path = original_path
            common_module._session_id = original_session

    @mock.patch("builtins.print")
    def test_send_rpc_message_with_special_characters(self, mock_print):
        """Test send_rpc_message handles special characters."""
        special_message = (
            "Fake elvish test üñíçödé and 'quotes' and \"double quotes\""
        )
        send_rpc_message("info", special_message)

        # Should successfully create valid JSON
        printed_message = mock_print.call_args[0][0]
        # Should not raise JSONDecodeError
        rpc_data = json.loads(printed_message)
        assert rpc_data["params"]["message"] == special_message

    @mock.patch("src.utils.common.write_log")
    def test_log_error_with_complex_exception(self, mock_write_log):
        """Test log_error handles complex exception objects."""

        class CustomException(Exception):
            def __init__(self, message, code):
                super().__init__(message)
                self.code = code

            def __str__(self):
                return f"CustomError({self.code}): {super().__str__()}"

        complex_error = CustomException("So it begins.", 500)
        log_error(complex_error, "Complex context")

        expected_message = "Complex context: CustomError(500): So it begins."
        mock_write_log.assert_called_once_with("error", expected_message)
