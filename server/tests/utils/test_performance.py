"""Test performance monitoring utilities."""

import time
import unittest.mock as mock

from src.utils.performance import (
    get_duration,
    log_operation_time,
    start_timer,
    timed_operation,
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
        with patch("src.utils.performance.time.perf_counter") as mock_time:
            mock_time.side_effect = [100.0, 105.5]  # 5.5 second difference

            start_time = start_timer()
            duration = get_duration(start_time)

            assert duration == 5.5

    def test_get_duration_zero_time(self):
        """Test get_duration with zero elapsed time."""
        with patch("src.utils.performance.time.perf_counter", return_value=100.0):
            start_time = start_timer()
            duration = get_duration(start_time)

            assert duration == 0.0

    def test_get_duration_negative_protection(self):
        """Test get_duration handles clock adjustments gracefully."""
        with patch("src.utils.performance.time.perf_counter") as mock_time:
            mock_time.side_effect = [100.0, 99.0]  # Clock went backwards

            start_time = start_timer()
            duration = get_duration(start_time)

            assert duration == -1.0  # Should return actual difference


class TestOperationLogging:
    """Test operation timing and logging functionality."""

    @patch("src.utils.performance.log_debug")
    @patch("src.utils.performance.log_info")
    def test_log_operation_time_debug_level(self, mock_log_info, mock_log_debug):
        """Test log_operation_time with debug level."""
        with patch("src.utils.performance.time.perf_counter") as mock_time:
            mock_time.side_effect = [100.0, 102.5]  # 2.5 second operation

            start_time = start_timer()
            log_operation_time("test_operation", start_time, "debug")

            mock_log_debug.assert_called_once_with(
                "Performance: test_operation completed in 2.500s"
            )
            mock_log_info.assert_not_called()

    @patch("src.utils.performance.log_debug")
    @patch("src.utils.performance.log_info")
    def test_log_operation_time_info_level(self, mock_log_info, mock_log_debug):
        """Test log_operation_time with info level."""
        with patch("src.utils.performance.time.perf_counter") as mock_time:
            mock_time.side_effect = [100.0, 100.123]  # 0.123 second operation

            start_time = start_timer()
            log_operation_time("fast_operation", start_time, "info")

            mock_log_info.assert_called_once_with(
                "Performance: fast_operation completed in 0.123s"
            )
            mock_log_debug.assert_not_called()

    @patch("src.utils.performance.log_debug")
    @patch("src.utils.performance.log_info")
    def test_log_operation_time_default_info(self, mock_log_info, mock_log_debug):
        """Test log_operation_time defaults to info level."""
        with patch("src.utils.performance.time.perf_counter") as mock_time:
            mock_time.side_effect = [100.0, 101.0]

            start_time = start_timer()
            log_operation_time("default_operation", start_time)

            mock_log_info.assert_called_once()
            mock_log_debug.assert_not_called()

    @patch("src.utils.performance.log_info")
    def test_log_operation_time_precision(self, mock_log_info):
        """Test log_operation_time formats duration to 3 decimal places."""
        with patch("src.utils.performance.time.perf_counter") as mock_time:
            mock_time.side_effect = [100.0, 100.123456789]

            start_time = start_timer()
            log_operation_time("precise_operation", start_time)

            # Format to 3 decimal places
            mock_log_info.assert_called_once_with(
                "Performance: precise_operation completed in 0.123s"
            )

    @patch("src.utils.performance.log_info")
    def test_log_operation_time_long_duration(self, mock_log_info):
        """Test log_operation_time with longer duration."""
        with patch("src.utils.performance.time.perf_counter") as mock_time:
            mock_time.side_effect = [100.0, 165.789]  # 65.789 seconds

            start_time = start_timer()
            log_operation_time("long_operation", start_time)

            mock_log_info.assert_called_once_with(
                "Performance: long_operation completed in 65.789s"
            )


class TestTimeOperationContextManager:
    """Test time_operation context manager functionality."""

    @patch("src.utils.performance.log_operation_time")
    def test_timed_operation_basic(self, mock_log_operation):
        """Test timed_operation context manager basic functionality."""
        with patch("src.utils.performance.time.perf_counter", return_value=100.0):
            with timed_operation("test_context") as start_time:
                assert start_time == 100.0

            mock_log_operation.assert_called_once_with("test_context", 100.0, "info")

    @patch("src.utils.performance.log_operation_time")
    def test_timed_operation_log_level(self, mock_log_operation):
        """Test timed_operation with custom log level."""
        with patch("src.utils.performance.time.perf_counter", return_value=200.0):
            with timed_operation("info_context", "info") as start_time:
                assert start_time == 200.0

            mock_log_operation.assert_called_once_with("info_context", 200.0, "info")

    @patch("src.utils.performance.log_operation_time")
    def test_timed_operation_exception_handling(self, mock_log_operation):
        """Test that timed_operation handles exceptions gracefully."""
        with patch("src.utils.performance.time.perf_counter", return_value=300.0):
            try:
                with timed_operation("exception_context"):
                    raise ValueError("Test exception")
            except ValueError:
                pass  # Expected

            # Still log the operation time
            mock_log_operation.assert_called_once_with(
                "exception_context", 300.0, "info"
            )

    @patch("src.utils.performance.log_operation_time")
    def test_timed_operation_yields_start_time(self, mock_log_operation):
        """Test that timed_operation yields the start time correctly."""
        expected_start = 150.5
        with patch(
            "src.utils.performance.time.perf_counter",
            return_value=expected_start,
        ):
            with timed_operation("yield_test") as yielded_time:
                assert yielded_time == expected_start
                # Can use yielded time for manual duration calculations
                assert isinstance(yielded_time, float)

    @patch("src.utils.performance.log_operation_time")
    def test_timed_operation_nested(self, mock_log_operation):
        """Test nested timed_operation contexts."""
        with patch("src.utils.performance.time.perf_counter") as mock_time:
            mock_time.side_effect = [
                100.0,  # Outer start
                110.0,  # Inner start
                120.0,  # Inner end
                130.0,  # Outer end
            ]  # Different times for nesting

            with timed_operation("outer_context"):
                with timed_operation("inner_context"):
                    pass

            # Log both operations
            assert mock_log_operation.call_count == 2
            mock_log_operation.assert_any_call("inner_context", 110.0, "info")
            mock_log_operation.assert_any_call("outer_context", 100.0, "info")

    @patch("src.utils.performance.log_operation_time")
    def test_timed_operation_realistic_usage(self, mock_log_operation):
        """Test timed_operation in a realistic usage pattern."""
        with patch("src.utils.performance.time.perf_counter", return_value=500.0):
            # Simulate the pattern shown in docstring
            with timed_operation("file_listing"):
                # Simulate file listing operation
                pass

            mock_log_operation.assert_called_once_with("file_listing", 500.0, "info")

    def test_timed_operation_empty_name(self):
        """Test timed_operation with empty operation name."""
        with patch("src.utils.performance.log_operation_time") as mock_log:
            with patch("src.utils.performance.time.perf_counter", return_value=100.0):
                with timed_operation(""):
                    pass

                mock_log.assert_called_once_with("", 100.0, "info")


class TestPerformanceIntegration:
    """Test integration scenarios and real-world usage patterns."""

    def test_manual_timing_workflow(self):
        """Test manual timing workflow used in the codebase."""
        with patch("src.utils.performance.time.perf_counter") as mock_time:
            mock_time.side_effect = [100.0, 103.456]

            # Simulate the pattern used in file_tools.py
            start_time = start_timer()
            # Simulate some work
            duration = get_duration(start_time)

            assert abs(duration - 3.456) < 0.0001

    @patch("src.utils.performance.log_operation_time")
    def test_context_manager_workflow(self, mock_log_operation):
        """Test context manager workflow for operation timing."""
        with patch("src.utils.performance.time.perf_counter", return_value=500.0):
            # Simulate the pattern shown in docstring
            with timed_operation("file_listing"):
                # Simulate file listing operation
                pass

            mock_log_operation.assert_called_once_with("file_listing", 500.0, "info")

    def test_performance_tracking_precision(self):
        """Test performance tracking maintains proper precision."""
        # Test with very small durations
        with patch("src.utils.performance.time.perf_counter") as mock_time:
            mock_time.side_effect = [100.0, 100.001]  # 1ms operation

            start_time = start_timer()
            duration = get_duration(start_time)

            assert abs(duration - 0.001) < 0.0001

    @patch("src.utils.performance.log_info")
    def test_real_world_operation_names(self, mock_log_info):
        """Test performance logging with real-world operation names."""
        test_operations = [
            "gandalf_conversation_recall",
            "frodo_file_search",
            "aragorn_context_analysis",
            "legolas_git_activity_scan",
            "gimli_database_query",
        ]

        with patch("src.utils.performance.time.perf_counter") as mock_time:
            mock_time.side_effect = [
                100.0,
                101.234,
                200.0,
                200.567,
                300.0,
                302.890,
                400.0,
                400.123,
                500.0,
                501.456,
            ]

            for operation in test_operations:
                start_time = start_timer()
                log_operation_time(operation, start_time)

            assert mock_log_info.call_count == len(test_operations)


class TestPerformanceEdgeCases:
    """Test edge cases and error conditions."""

    def test_very_long_operation_name(self):
        """Test with very long operation names."""
        long_name = "a" * 200

        with patch("src.utils.performance.time.perf_counter") as mock_time:
            mock_time.side_effect = [100.0, 101.0]

            with patch("src.utils.performance.log_info") as mock_log:
                start_time = start_timer()
                log_operation_time(long_name, start_time)

                # Handle long names without error
                mock_log.assert_called_once()

    def test_special_characters_in_operation_name(self):
        """Test operation names with special characters."""
        special_names = [
            "operation-with-dashes",
            "operation_with_underscores",
            "operation.with.dots",
            "operation with spaces",
            "operation/with/slashes",
        ]

        with patch("src.utils.performance.time.perf_counter") as mock_time:
            mock_time.side_effect = [100.0, 101.0] * len(special_names)

            with patch("src.utils.performance.log_info") as mock_log:
                for name in special_names:
                    start_time = start_timer()
                    log_operation_time(name, start_time)

                # All work without error
                assert mock_log.call_count == len(special_names)

    def test_invalid_log_level_defaults_to_info(self):
        """Test invalid log level defaults to info."""
        with patch("src.utils.performance.time.perf_counter") as mock_time:
            mock_time.side_effect = [100.0, 101.0]

            with patch("src.utils.performance.log_info") as mock_info:
                with patch("src.utils.performance.log_debug") as mock_debug:
                    start_time = start_timer()
                    log_operation_time("test", start_time, "invalid_level")

                    # Default to info
                    mock_info.assert_called_once()
                    mock_debug.assert_not_called()

    def test_time_operation_empty_operation_name(self):
        """Test time_operation with empty operation name."""
        with patch("src.utils.performance.log_operation_time") as mock_log:
            with patch("src.utils.performance.time.perf_counter", return_value=100.0):
                with timed_operation(""):
                    pass

                mock_log.assert_called_once_with("", 100.0, "info")

    def test_zero_start_time(self):
        """Test functions with zero start time."""
        duration = get_duration(0.0)
        assert duration >= 0  # Handle zero start time gracefully

        with patch("src.utils.performance.log_info") as mock_log:
            log_operation_time("zero_start", 0.0)
            mock_log.assert_called_once()
