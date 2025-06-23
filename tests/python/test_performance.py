"""Test performance monitoring utilities."""

import time
import unittest.mock as mock

from src.utils.performance import (
    get_duration,
    log_operation_time,
    start_timer,
    time_operation,
)

patch = mock.patch


class TestPerformanceTimers:
    """Test basic timer functionality."""

    def test_start_timer_returns_float(self):
        """Test start_timer returns a float timestamp."""
        result = start_timer()
        assert isinstance(result, float)
        assert result > 0

    def test_start_timer_progression(self):
        """Test start_timer returns increasing values."""
        first_time = start_timer()
        time.sleep(0.001)  # Small delay
        second_time = start_timer()
        assert second_time > first_time

    def test_get_duration_calculation(self):
        """Test get_duration calculates time difference correctly."""
        with patch("src.utils.performance.time.time") as mock_time:
            mock_time.side_effect = [100.0, 105.5]  # 5.5 second difference

            start_time = start_timer()
            duration = get_duration(start_time)

            assert duration == 5.5

    def test_get_duration_zero_time(self):
        """Test get_duration with zero elapsed time."""
        with patch("src.utils.performance.time.time", return_value=100.0):
            start_time = start_timer()
            duration = get_duration(start_time)

            assert duration == 0.0

    def test_get_duration_negative_protection(self):
        """Test get_duration handles clock adjustments gracefully."""
        with patch("src.utils.performance.time.time") as mock_time:
            mock_time.side_effect = [100.0, 99.0]  # Clock went backwards

            start_time = start_timer()
            duration = get_duration(start_time)

            assert duration == -1.0  # Should return actual difference


class TestOperationLogging:
    """Test operation timing and logging functionality."""

    @patch("src.utils.performance.log_debug")
    @patch("src.utils.performance.log_info")
    def test_log_operation_time_debug_level(
        self, mock_log_info, mock_log_debug
    ):
        """Test log_operation_time with debug level."""
        with patch("src.utils.performance.time.time") as mock_time:
            mock_time.side_effect = [100.0, 102.5]  # 2.5 second operation

            start_time = start_timer()
            log_operation_time("test_operation", start_time, "debug")

            mock_log_debug.assert_called_once_with(
                "Performance: test_operation completed in 2.500s"
            )
            mock_log_info.assert_not_called()

    @patch("src.utils.performance.log_debug")
    @patch("src.utils.performance.log_info")
    def test_log_operation_time_info_level(
        self, mock_log_info, mock_log_debug
    ):
        """Test log_operation_time with info level."""
        with patch("src.utils.performance.time.time") as mock_time:
            mock_time.side_effect = [100.0, 100.123]  # 0.123 second operation

            start_time = start_timer()
            log_operation_time("fast_operation", start_time, "info")

            mock_log_info.assert_called_once_with(
                "Performance: fast_operation completed in 0.123s"
            )
            mock_log_debug.assert_not_called()

    @patch("src.utils.performance.log_debug")
    @patch("src.utils.performance.log_info")
    def test_log_operation_time_default_debug(
        self, mock_log_info, mock_log_debug
    ):
        """Test log_operation_time defaults to debug level."""
        with patch("src.utils.performance.time.time") as mock_time:
            mock_time.side_effect = [100.0, 101.0]

            start_time = start_timer()
            log_operation_time("default_operation", start_time)

            mock_log_debug.assert_called_once()
            mock_log_info.assert_not_called()

    @patch("src.utils.performance.log_debug")
    def test_log_operation_time_precision(self, mock_log_debug):
        """Test log_operation_time formats duration to 3 decimal places."""
        with patch("src.utils.performance.time.time") as mock_time:
            mock_time.side_effect = [100.0, 100.123456789]

            start_time = start_timer()
            log_operation_time("precise_operation", start_time)

            # Should format to 3 decimal places
            mock_log_debug.assert_called_once_with(
                "Performance: precise_operation completed in 0.123s"
            )

    @patch("src.utils.performance.log_debug")
    def test_log_operation_time_long_duration(self, mock_log_debug):
        """Test log_operation_time with longer duration."""
        with patch("src.utils.performance.time.time") as mock_time:
            mock_time.side_effect = [100.0, 165.789]  # 65.789 seconds

            start_time = start_timer()
            log_operation_time("long_operation", start_time)

            mock_log_debug.assert_called_once_with(
                "Performance: long_operation completed in 65.789s"
            )


class TestTimeOperationContextManager:
    """Test time_operation context manager functionality."""

    @patch("src.utils.performance.log_operation_time")
    def test_time_operation_basic_usage(self, mock_log_operation):
        """Test time_operation context manager basic functionality."""
        with patch("src.utils.performance.time.time", return_value=100.0):
            with time_operation("test_context") as start_time:
                assert start_time == 100.0

            mock_log_operation.assert_called_once_with(
                "test_context", 100.0, "debug"
            )

    @patch("src.utils.performance.log_operation_time")
    def test_time_operation_with_log_level(self, mock_log_operation):
        """Test time_operation with custom log level."""
        with patch("src.utils.performance.time.time", return_value=200.0):
            with time_operation("info_context", "info") as start_time:
                assert start_time == 200.0

            mock_log_operation.assert_called_once_with(
                "info_context", 200.0, "info"
            )

    @patch("src.utils.performance.log_operation_time")
    def test_time_operation_exception_handling(self, mock_log_operation):
        """Test time_operation logs timing even when exception occurs."""
        with patch("src.utils.performance.time.time", return_value=300.0):
            try:
                with time_operation("exception_context"):
                    raise ValueError("Test exception")
            except ValueError:
                pass  # Expected exception

            # Should still log the operation time
            mock_log_operation.assert_called_once_with(
                "exception_context", 300.0, "debug"
            )

    @patch("src.utils.performance.log_operation_time")
    def test_time_operation_yields_start_time(self, mock_log_operation):
        """Test time_operation yields the start time for manual calculations."""
        expected_start = 150.5

        with patch(
            "src.utils.performance.time.time", return_value=expected_start
        ):
            with time_operation("yield_test") as yielded_time:
                assert yielded_time == expected_start
                # Can use yielded time for manual duration calculations
                assert isinstance(yielded_time, float)

    @patch("src.utils.performance.log_operation_time")
    def test_time_operation_nested_contexts(self, mock_log_operation):
        """Test time_operation can be nested."""
        with patch("src.utils.performance.time.time") as mock_time:
            mock_time.side_effect = [
                100.0,
                200.0,
            ]  # Different times for nesting

            with time_operation("outer_context"):
                with time_operation("inner_context"):
                    pass

            # Should log both operations
            assert mock_log_operation.call_count == 2
            mock_log_operation.assert_any_call("inner_context", 200.0, "debug")
            mock_log_operation.assert_any_call("outer_context", 100.0, "debug")


class TestPerformanceIntegration:
    """Test integration scenarios and real-world usage patterns."""

    def test_manual_timing_workflow(self):
        """Test manual timing workflow used in the codebase."""
        with patch("src.utils.performance.time.time") as mock_time:
            mock_time.side_effect = [100.0, 103.456]

            # Simulate the pattern used in file_tools.py
            start_time = start_timer()
            # Simulate some work
            duration = get_duration(start_time)

            assert abs(duration - 3.456) < 0.0001

    @patch("src.utils.performance.log_operation_time")
    def test_context_manager_workflow(self, mock_log_operation):
        """Test context manager workflow for operation timing."""
        with patch("src.utils.performance.time.time", return_value=500.0):
            # Simulate the pattern shown in docstring
            with time_operation("file_listing"):
                # Simulate file listing operation
                pass

            mock_log_operation.assert_called_once_with(
                "file_listing", 500.0, "debug"
            )

    def test_performance_tracking_precision(self):
        """Test performance tracking maintains proper precision."""
        # Test with very small durations
        with patch("src.utils.performance.time.time") as mock_time:
            mock_time.side_effect = [100.0, 100.001]  # 1ms operation

            start_time = start_timer()
            duration = get_duration(start_time)

            assert abs(duration - 0.001) < 0.0001
            assert duration > 0  # Should detect even very small durations

    @patch("src.utils.performance.log_debug")
    def test_real_world_operation_names(self, mock_log_debug):
        """Test with operation names used in actual codebase."""
        operations = [
            "list_project_files",
            "fast_conversation_extraction",
            "cursor_conversation_query",
            "file_listing",
        ]

        with patch("src.utils.performance.time.time") as mock_time:
            mock_time.side_effect = [100.0, 101.0] * len(operations)

            for operation in operations:
                start_time = start_timer()
                log_operation_time(operation, start_time)

        # Should have logged all operations
        assert mock_log_debug.call_count == len(operations)

        # Check that operation names are preserved in log messages
        for call_args in mock_log_debug.call_args_list:
            message = call_args[0][0]
            assert any(op in message for op in operations)


class TestPerformanceEdgeCases:
    """Test edge cases and error conditions."""

    def test_very_long_operation_name(self):
        """Test with very long operation names."""
        long_name = "a" * 200

        with patch("src.utils.performance.time.time") as mock_time:
            mock_time.side_effect = [100.0, 101.0]

            with patch("src.utils.performance.log_debug") as mock_log:
                start_time = start_timer()
                log_operation_time(long_name, start_time)

                # Should handle long names without error
                mock_log.assert_called_once()
                logged_message = mock_log.call_args[0][0]
                assert long_name in logged_message

    def test_special_characters_in_operation_name(self):
        """Test operation names with special characters."""
        special_names = [
            "operation-with-dashes",
            "operation_with_underscores",
            "operation.with.dots",
            "operation with spaces",
            "operation/with/slashes",
        ]

        with patch("src.utils.performance.time.time") as mock_time:
            mock_time.side_effect = [100.0, 101.0] * len(special_names)

            with patch("src.utils.performance.log_debug") as mock_log:
                for name in special_names:
                    start_time = start_timer()
                    log_operation_time(name, start_time)

                # All should work without error
                assert mock_log.call_count == len(special_names)

    def test_invalid_log_level_defaults_to_debug(self):
        """Test invalid log level defaults to debug."""
        with patch("src.utils.performance.time.time") as mock_time:
            mock_time.side_effect = [100.0, 101.0]

            with patch("src.utils.performance.log_debug") as mock_debug:
                with patch("src.utils.performance.log_info") as mock_info:
                    start_time = start_timer()
                    log_operation_time("test", start_time, "invalid_level")

                    # Should default to debug
                    mock_debug.assert_called_once()
                    mock_info.assert_not_called()

    def test_time_operation_empty_operation_name(self):
        """Test time_operation with empty operation name."""
        with patch("src.utils.performance.log_operation_time") as mock_log:
            with patch("src.utils.performance.time.time", return_value=100.0):
                with time_operation(""):
                    pass

                mock_log.assert_called_once_with("", 100.0, "debug")

    def test_zero_start_time(self):
        """Test functions with zero start time."""
        duration = get_duration(0.0)
        assert duration >= 0  # Should handle zero start time gracefully

        with patch("src.utils.performance.log_debug") as mock_log:
            log_operation_time("zero_start", 0.0)
            mock_log.assert_called_once()
