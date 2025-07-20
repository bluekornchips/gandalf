"""
Test configuration and utilities for database connection management.
"""

import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest


@contextmanager
def safe_cursor(conn: sqlite3.Connection) -> Generator[sqlite3.Cursor, None, None]:
    """Context manager for safe cursor operations with automatic cleanup."""
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        cursor.close()


@contextmanager
def execute_sql(
    conn: sqlite3.Connection, sql: str, params: tuple | None = None
) -> Generator[sqlite3.Cursor, None, None]:
    """Context manager for safe SQL execution with automatic cursor cleanup."""
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        yield cursor
    finally:
        try:
            cursor.close()
        except (sqlite3.Error, OSError):
            pass


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
        with safe_cursor(conn) as cursor:
            cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
            cursor.execute("INSERT INTO test (value) VALUES ('test_data')")
        conn.commit()

    yield db_path

    # Cleanup
    try:
        db_path.unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def mock_query_class():
    """Mock query class for testing handlers."""
    with patch("src.tool_calls.claude_code.query.ClaudeCodeQuery") as mock:
        yield mock


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
