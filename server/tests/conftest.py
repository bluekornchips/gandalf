"""
Test configuration and utilities for database connection management.
"""

import sqlite3
import tempfile
import weakref
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

from src.utils.common import is_ci_environment


class DatabaseConnectionManager:
    """Manages database connections to prevent leaks in tests."""

    def __init__(self):
        self._connections: list[weakref.ref] = []

    @contextmanager
    def managed_connection(
        self, db_path: Path
    ) -> Generator[sqlite3.Connection, None, None]:
        """Create a managed database connection that will be properly closed."""
        with sqlite3.connect(str(db_path)) as conn:
            self._connections.append(weakref.ref(conn))
            yield conn

    def close_all_connections(self) -> None:
        """Close all tracked connections."""
        for conn_ref in self._connections:
            conn = conn_ref()
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        self._connections.clear()


def execute_sql(db_path: Path, sql: str, params: tuple | None = None) -> list:
    """Execute SQL and return results."""
    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor.fetchall()
    finally:
        if conn:
            conn.close()


@pytest.fixture
def db_manager():
    """Provide a database connection manager for tests."""
    manager = DatabaseConnectionManager()
    yield manager
    manager.close_all_connections()


@pytest.fixture
def mock_query_class():
    """Provide a mock query class for testing."""
    with patch("src.tool_calls.claude_code.query.ClaudeCodeQuery") as mock:
        yield mock


def create_test_database(
    db_path: Path, schema_sql: str | None = None, data: dict | None = None
) -> None:
    """Create a test database with optional schema and data."""
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        try:
            if schema_sql:
                cursor.executescript(schema_sql)

            if data:
                for table, rows in data.items():
                    if rows:
                        placeholders = ", ".join(["?" for _ in rows[0]])
                        cursor.executemany(
                            f"INSERT INTO {table} VALUES ({placeholders})", rows
                        )

            conn.commit()
        finally:
            cursor.close()


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = Path(temp_dir)
        # Create some basic project structure
        (project_root / "src").mkdir()
        (project_root / "tests").mkdir()
        (project_root / "README.md").write_text("# Test Project")
        yield project_root


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # Initialize database with basic table
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
            cursor.execute("INSERT INTO test (value) VALUES ('test_data')")
            conn.commit()
        finally:
            cursor.close()

    yield db_path

    # Cleanup
    try:
        db_path.unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def clean_database_pool():
    """Provide a clean database pool for tests that need isolation."""
    from src.utils.database_pool import close_database_pool

    # Clean up before this specific test that requested isolation
    close_database_pool()

    yield

    # Clean up after this specific test
    close_database_pool()


@pytest.fixture(autouse=True)
def cleanup_connections():
    """Auto-cleanup database connections after each test to prevent ResourceWarnings."""
    yield
    from src.utils.database_pool import close_all_connections

    close_all_connections()


# Sample request structures for testing
@pytest.fixture
def sample_requests():
    """Provide sample request structures for testing."""
    return {
        "cursor_recall": {
            "jsonrpc": "2.0",
            "id": "test-123",
            "method": "tools/call",
            "params": {
                "name": "mcp_gandalf_recall_conversations",
                "arguments": {
                    "tools": ["cursor"],
                    "days_lookback": 7,
                    "limit": 50,
                    "fast_mode": True,
                },
            },
        },
        "project_info": {
            "jsonrpc": "2.0",
            "id": "test-456",
            "method": "tools/call",
            "params": {
                "name": "mcp_gandalf_get_project_info",
                "arguments": {"include_stats": True},
            },
        },
    }


@pytest.fixture
def ci_environment():
    """Provide CI environment information for tests."""
    return is_ci_environment()


# Skip marker for CI-sensitive tests
skip_in_ci = pytest.mark.skipif(
    is_ci_environment(), reason="Test not suitable for CI environment"
)

# Modify behavior in CI environments
ci_timeout_multiplier = 3 if is_ci_environment() else 1


@pytest.fixture
def adjusted_timeout():
    """Provide timeout values adjusted for CI environments."""
    return lambda base_timeout: base_timeout * ci_timeout_multiplier
