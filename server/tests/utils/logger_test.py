"""Test suite for logger utility functions."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.utils.logger import write_log, log_info, log_error


class TestLogger:
    """Test suite for logger functions."""

    def test_write_log_creates_log_file(self) -> None:
        """Test that write_log creates a log file with correct content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("src.utils.logger.GANDALF_HOME", temp_dir):
                write_log("info", "Test message")

                log_file = Path(temp_dir) / "logs" / "info.log"
                assert log_file.exists()

                with open(log_file, "r") as f:
                    content = f.read().strip()
                    log_entry = json.loads(content)

                    assert log_entry["level"] == "info"
                    assert log_entry["message"] == "Test message"
                    assert "timestamp" in log_entry

    def test_write_log_with_data(self) -> None:
        """Test that write_log includes data field when provided."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("src.utils.logger.GANDALF_HOME", temp_dir):
                test_data = {"user_id": 123, "action": "login"}
                write_log("info", "User action", test_data)

                log_file = Path(temp_dir) / "logs" / "info.log"
                with open(log_file, "r") as f:
                    content = f.read().strip()
                    log_entry = json.loads(content)
                    assert log_entry["data"] == test_data

    def test_write_log_no_gandalf_home(self) -> None:
        """Test that write_log handles missing GANDALF_HOME gracefully."""
        with patch("src.utils.logger.GANDALF_HOME", ""):
            write_log("info", "Test message")

    def test_log_info(self) -> None:
        """Test that log_info creates an info log file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("src.utils.logger.GANDALF_HOME", temp_dir):
                log_info("Info message")
                log_file = Path(temp_dir) / "logs" / "info.log"
                assert log_file.exists()

    def test_log_error(self) -> None:
        """Test that log_error creates an error log file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("src.utils.logger.GANDALF_HOME", temp_dir):
                log_error("Error message")
                log_file = Path(temp_dir) / "logs" / "error.log"
                assert log_file.exists()
