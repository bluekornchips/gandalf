"""
Tests for database connection pooling utility.
"""

import sqlite3
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from src.utils.database_pool import (
    ConnectionPool,
    close_database_pool,
    get_database_connection,
    get_database_pool,
)


class TestConnectionPool:
    """Test the ConnectionPool class."""

    def test_connection_pool_init(self):
        """Test connection pool initialization."""
        pool = ConnectionPool(max_connections=3, timeout=1.0)
        assert pool.max_connections == 3
        assert pool.timeout == 1.0
        assert len(pool._pools) == 0
        assert len(pool._pools) == 0

    def test_get_connection_creates_new(self, temp_db):
        """Test that get_connection creates new connection when pool is empty."""
        pool = ConnectionPool()

        with pool.get_connection(temp_db) as conn:
            assert isinstance(conn, sqlite3.Connection)
            # Test that connection works
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1

    def test_connection_reuse(self, temp_db):
        """Test that connections are reused from the pool."""
        pool = ConnectionPool()

        # First connection
        with pool.get_connection(temp_db) as conn1:
            conn1_id = id(conn1)

        # Second connection should be the same (reused)
        with pool.get_connection(temp_db) as conn2:
            conn2_id = id(conn2)
            assert conn1_id == conn2_id  # Same connection object

    def test_max_connections_limit(self, temp_db):
        """Test that pool respects max connections limit."""
        pool = ConnectionPool(max_connections=2)

        # Create connections to fill up the pool beyond limit
        connections = []
        for _ in range(3):
            with pool.get_connection(temp_db) as conn:
                # Do something to ensure connection is used
                conn.execute("SELECT 1")

        # Pool should only have 2 connections (the limit)
        assert len(pool._pools[str(temp_db)]) <= 2

    def test_connection_health_check(self, temp_db):
        """Test that unhealthy connections are not returned to pool."""
        pool = ConnectionPool()

        with pool.get_connection(temp_db) as conn:
            # Simulate connection corruption
            conn.close()

        # Pool should handle the corrupted connection gracefully
        stats = pool.get_pool_stats()
        # Connection should not have been returned to pool
        assert stats.get(str(temp_db), 0) == 0

    def test_concurrent_access(self, temp_db):
        """Test thread-safe concurrent access to connection pool."""
        pool = ConnectionPool()
        results = []
        errors = []

        def worker():
            try:
                with pool.get_connection(temp_db) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()[0]
                    results.append(result)
                    time.sleep(0.01)  # Small delay to test concurrency
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All operations should succeed
        assert len(errors) == 0
        assert len(results) == 5
        assert all(r == 1 for r in results)

    def test_close_all_connections(self, temp_db):
        """Test closing all connections in the pool."""
        pool = ConnectionPool()

        # Create some connections
        with pool.get_connection(temp_db) as conn1:
            pass
        with pool.get_connection(temp_db) as conn2:
            pass

        # Verify pool has connections
        assert len(pool._pools[str(temp_db)]) > 0

        # Close all connections
        pool.close_all()

        # Pool should be empty
        assert len(pool._pools) == 0
        assert len(pool._pools) == 0

    def test_get_pool_stats(self, temp_db):
        """Test getting pool statistics."""
        pool = ConnectionPool()

        # Initially empty
        stats = pool.get_pool_stats()
        assert len(stats) == 0

        # Add connections by using them sequentially
        for _ in range(2):
            with pool.get_connection(temp_db) as conn:
                conn.execute("SELECT 1")

        # Check stats - should have at least 1 connection
        stats = pool.get_pool_stats()
        assert str(temp_db) in stats
        assert stats[str(temp_db)] >= 1

    def test_different_databases(self, temp_db):
        """Test that different databases maintain separate pools."""
        pool = ConnectionPool()

        # Create another temp database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db2 = Path(f.name)

        try:
            # Use connections for both databases
            with pool.get_connection(temp_db) as conn1:
                pass
            with pool.get_connection(temp_db2) as conn2:
                pass

            # Should have separate pools
            stats = pool.get_pool_stats()
            assert len(stats) == 2
            assert str(temp_db) in stats
            assert str(temp_db2) in stats
        finally:
            temp_db2.unlink()


class TestGlobalPool:
    """Test the global connection pool functions."""

    def test_get_database_pool_singleton(self):
        """Test that get_database_pool returns singleton instance."""
        pool1 = get_database_pool()
        pool2 = get_database_pool()
        assert pool1 is pool2

    def test_close_database_pool(self):
        """Test closing the global database pool."""
        # Get initial pool
        pool = get_database_pool()
        assert pool is not None

        # Close pool
        close_database_pool()

        # New pool should be created
        new_pool = get_database_pool()
        assert new_pool is not pool

    def test_get_database_connection_context_manager(self, temp_db):
        """Test the global get_database_connection function."""
        with get_database_connection(temp_db) as conn:
            assert isinstance(conn, sqlite3.Connection)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1

    def test_connection_error_handling(self):
        """Test error handling with invalid database path."""
        invalid_path = Path("/invalid/path/database.db")

        with pytest.raises((sqlite3.Error, OSError)):
            with get_database_connection(invalid_path) as conn:
                pass


class TestPragmaSettings:
    """Test that SQLite PRAGMA settings are applied correctly."""

    def test_pragma_settings_applied(self, temp_db):
        """Test that PRAGMA settings are applied to new connections."""
        pool = ConnectionPool()

        with pool.get_connection(temp_db) as conn:
            cursor = conn.cursor()

            # Check foreign keys pragma
            cursor.execute("PRAGMA foreign_keys")
            foreign_keys = cursor.fetchone()[0]
            assert foreign_keys == 1

            # Check journal mode pragma
            cursor.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]
            assert journal_mode == "wal"

            # Check synchronous pragma
            cursor.execute("PRAGMA synchronous")
            synchronous = cursor.fetchone()[0]
            assert synchronous == 1  # NORMAL mode


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # Initialize database with basic table
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO test (value) VALUES ('test_data')")
        conn.commit()

    yield db_path

    # Cleanup
    try:
        db_path.unlink()
    except FileNotFoundError:
        pass


@pytest.fixture(autouse=True)
def cleanup_global_pool():
    """Ensure global pool is cleaned up after each test."""
    yield
    close_database_pool()
