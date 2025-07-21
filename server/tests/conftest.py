"""
Test configuration and utilities for database connection management.
"""

import sqlite3
import weakref
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List
from unittest.mock import patch

import pytest


class DatabaseConnectionManager:
    """Manages database connections to prevent leaks in tests."""

    def __init__(self):
        self._connections: List[weakref.ref] = []

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


@pytest.fixture
def db_manager():
    """Provide a database connection manager for tests."""
    manager = DatabaseConnectionManager()
    yield manager
    manager.close_all_connections()


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database file."""
    db_path = tmp_path / "test.db"
    yield db_path


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory for testing."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    yield project_dir


@pytest.fixture
def mock_query_class():
    """Provide a mock query class for testing."""
    with patch("src.tool_calls.claude_code.query.ClaudeCodeQuery") as mock:
        yield mock


def create_test_database(
    db_path: Path, schema_sql: str = None, data: dict = None
) -> None:
    """Create a test database with optional schema and data."""
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()

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
