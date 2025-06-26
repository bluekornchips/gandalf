import signal
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "test_project"
        project_path.mkdir()

        # Initialize as git repo for proper project detection
        subprocess.run(
            ["git", "init"], cwd=project_path, capture_output=True, check=True
        )

        # Create a simple test file
        test_file = project_path / "test.py"
        test_file.write_text("# Test file\nprint('hello world')\n")

        yield project_path


@pytest.fixture
def patch_signals():
    """Patch signal.signal for safe signal simulation in tests."""
    registered = {}

    def fake_signal(sig, handler):
        registered[sig] = handler
        return handler

    with patch.object(signal, "signal", side_effect=fake_signal):
        yield registered


@pytest.fixture
def mock_signal_handler():
    """Mock signal handler for testing."""
    with patch("signal.signal") as mock_signal:
        yield mock_signal
