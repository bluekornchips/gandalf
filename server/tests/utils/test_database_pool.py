"""
Tests for database connection pooling utility.
"""

import gc
import sqlite3
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

import pytest
from src.utils.database_pool import (
    ConnectionPool,
    DatabaseService,
    close_database_pool,
    get_database_connection,
    get_database_pool,
)
from conftest import execute_sql, safe_cursor


class TestConnectionPool:
    """Test the ConnectionPool class."""

    def test_connection_pool_init(self):
        """Test connection pool initialization."""
        pool = ConnectionPool(max_connections=3, timeout=1.0)
        assert pool.max_connections == 3
        assert pool.timeout == 1.0
        assert len(pool._pools) == 0

    def test_get_connection_creates_new(self, temp_db):
        """Test that get_connection creates new connection when pool is empty."""
        pool = ConnectionPool()

        with pool.get_connection(temp_db) as conn:
            assert isinstance(conn, sqlite3.Connection)
            with execute_sql(conn, "SELECT 1") as cursor:
                assert cursor.fetchone()[0] == 1

        # Clean up pool connections
        pool.close_all()

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

        pool.close_all()

    def test_max_connections_limit(self, temp_db):
        """Test that pool respects max connections limit."""
        pool = ConnectionPool(max_connections=2)

        # Create connections to fill up the pool beyond limit
        for _ in range(3):
            with pool.get_connection(temp_db) as conn:
                # Do something to ensure connection is used
                with execute_sql(conn, "SELECT 1") as cursor:
                    cursor.fetchone()

        # Pool should only have 2 connections (the limit)
        assert len(pool._pools[str(temp_db)]) <= 2

        # Explicitly close all connections in the pool to prevent leaks
        pool.close_all()
        gc.collect()

    @patch.object(ConnectionPool, "_is_connection_healthy", return_value=False)
    def test_connection_health_check(self, mock_health_check, temp_db):
        """Test that unhealthy connections are not returned to pool."""
        pool = ConnectionPool()

        # Use connection normally, but mock health check to return False
        with pool.get_connection(temp_db) as conn:
            with execute_sql(conn, "SELECT 1") as cursor:
                cursor.fetchone()

        # Pool should handle the "unhealthy" connection gracefully
        stats = pool.get_pool_stats()
        # Connection should not have been returned to pool due to failed health check
        assert stats.get(str(temp_db), 0) == 0

        mock_health_check.assert_called_once()

    def test_concurrent_access(self, temp_db):
        """Test thread-safe concurrent access to connection pool."""
        pool = ConnectionPool()
        results = []
        errors = []
        barrier = threading.Barrier(5)

        def worker():
            try:
                barrier.wait()

                with pool.get_connection(temp_db) as conn:
                    with execute_sql(conn, "SELECT 1") as cursor:
                        result = cursor.fetchone()[0]
                        results.append(result)
            except (sqlite3.Error, OSError, RuntimeError) as e:
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

        # Clean up pool connections
        pool.close_all()

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

    def test_get_pool_stats(self, temp_db):
        """Test getting pool statistics."""
        pool = ConnectionPool()

        # Initially empty
        stats = pool.get_pool_stats()
        assert len(stats) == 0

        # Add connections by using them sequentially
        for _ in range(2):
            with pool.get_connection(temp_db) as conn:
                with execute_sql(conn, "SELECT 1") as cursor:
                    cursor.fetchone()

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

            # Clean up pool connections
            pool.close_all()
        finally:
            temp_db2.unlink()


class TestDatabaseService:
    """Test the DatabaseService class."""

    def test_database_service_init(self):
        """Test DatabaseService initialization."""
        service = DatabaseService()
        assert not service.is_initialized()
        assert service.get_pool_stats() == {}

    def test_database_service_initialize(self):
        """Test DatabaseService initialization."""
        service = DatabaseService()
        service.initialize(max_connections=3, timeout=1.5)

        assert service.is_initialized()
        assert service._pool is not None
        assert service._pool.max_connections == 3
        assert service._pool.timeout == 1.5

    def test_database_service_initialize_idempotent(self):
        """Test that initialize can be called multiple times safely."""
        service = DatabaseService()
        service.initialize(max_connections=2)

        pool1 = service._pool
        assert pool1 is not None  # Ensure pool was created

        # Second initialize should not create new pool
        service.initialize(max_connections=5)
        pool2 = service._pool

        assert pool1 is pool2
        assert pool1.max_connections == 2  # Original settings preserved

    def test_database_service_get_connection_not_initialized(self):
        """Test that get_connection raises error when not initialized."""
        service = DatabaseService()

        with pytest.raises(RuntimeError, match="DatabaseService not initialized"):
            with service.get_connection(Path("test.db")):
                pass

    def test_database_service_get_connection_success(self, temp_db):
        """Test successful database connection through service."""
        service = DatabaseService()
        service.initialize()

        with service.get_connection(temp_db) as conn:
            assert isinstance(conn, sqlite3.Connection)
            with execute_sql(conn, "SELECT 1") as cursor:
                assert cursor.fetchone()[0] == 1

    def test_database_service_connection_reuse(self, temp_db):
        """Test that service reuses connections."""
        service = DatabaseService()
        service.initialize()

        # First connection
        with service.get_connection(temp_db) as conn1:
            conn1_id = id(conn1)

        # Second connection should be reused
        with service.get_connection(temp_db) as conn2:
            conn2_id = id(conn2)
            assert conn1_id == conn2_id

    def test_database_service_get_pool_stats(self, temp_db):
        """Test getting pool statistics from service."""
        service = DatabaseService()
        service.initialize()

        # Initially empty
        stats = service.get_pool_stats()
        assert len(stats) == 0

        # Use connection
        with service.get_connection(temp_db) as conn:
            with execute_sql(conn, "SELECT 1") as cursor:
                cursor.fetchone()

        # Should have stats
        stats = service.get_pool_stats()
        assert str(temp_db) in stats

    def test_database_service_shutdown(self, temp_db):
        """Test service shutdown closes all connections."""
        service = DatabaseService()
        service.initialize()

        # Use connection to add to pool
        with service.get_connection(temp_db) as conn:
            with execute_sql(conn, "SELECT 1") as cursor:
                cursor.fetchone()

        # Verify connection is in pool
        stats = service.get_pool_stats()
        assert str(temp_db) in stats

        # Shutdown
        service.shutdown()

        assert not service.is_initialized()
        assert service._pool is None
        assert service.get_pool_stats() == {}

    def test_database_service_shutdown_idempotent(self):
        """Test that shutdown can be called multiple times safely."""
        service = DatabaseService()
        service.initialize()

        # First shutdown
        service.shutdown()
        assert not service.is_initialized()

        # Second shutdown should not error
        service.shutdown()
        assert not service.is_initialized()

    def test_database_service_concurrent_access(self, temp_db):
        """Test thread-safe concurrent access to database service."""
        service = DatabaseService()
        service.initialize()

        results = []
        errors = []
        barrier = threading.Barrier(5)  # all threads start simultaneously

        def worker():
            try:
                barrier.wait()

                with service.get_connection(temp_db) as conn:
                    with execute_sql(conn, "SELECT 1") as cursor:
                        result = cursor.fetchone()[0]
                        results.append(result)
            except (sqlite3.Error, OSError, RuntimeError) as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All operations should succeed
        assert len(errors) == 0
        assert len(results) == 5
        assert all(r == 1 for r in results)

    def test_database_service_error_handling(self):
        """Test service error handling with invalid database path."""
        service = DatabaseService()
        service.initialize()

        invalid_path = Path("/invalid/path/database.db")

        with pytest.raises((sqlite3.Error, OSError)):
            with service.get_connection(invalid_path):
                pass


class TestBackwardCompatibility:
    """Test backward compatibility functions."""

    def test_get_database_pool_returns_service(self):
        """Test that get_database_pool returns DatabaseService instance."""
        service = get_database_pool()
        assert isinstance(service, DatabaseService)
        assert service.is_initialized()

    def test_get_database_pool_new_instance(self):
        """Test that get_database_pool returns new instance each time."""
        service1 = get_database_pool()
        service2 = get_database_pool()
        assert service1 is not service2
        assert isinstance(service1, DatabaseService)
        assert isinstance(service2, DatabaseService)
        assert service1.is_initialized()
        assert service2.is_initialized()

    def test_close_database_pool(self):
        """Test closing the global database pool."""
        # Get initial service
        service = get_database_pool()
        assert service is not None

        # Close pool
        close_database_pool()

        # New service should be created
        new_service = get_database_pool()
        assert new_service is not service

    def test_get_database_connection_context_manager(self, temp_db):
        """Test the global get_database_connection function."""
        with get_database_connection(temp_db) as conn:
            assert isinstance(conn, sqlite3.Connection)
            with execute_sql(conn, "SELECT 1") as cursor:
                assert cursor.fetchone()[0] == 1

    def test_connection_error_handling(self):
        """Test error handling with invalid database path."""
        invalid_path = Path("/invalid/path/database.db")

        with pytest.raises((sqlite3.Error, OSError)):
            with get_database_connection(invalid_path) as conn:
                pass


class TestPragmaSettings:
    """Test that SQLite PRAGMA settings are applied correctly."""

    def test_pragma_settings_applied_service(self, temp_db):
        """Test that PRAGMA settings are applied through service."""
        service = DatabaseService()
        service.initialize()

        with service.get_connection(temp_db) as conn:
            with execute_sql(conn, "PRAGMA foreign_keys") as cursor:
                foreign_keys = cursor.fetchone()[0]
                assert foreign_keys == 1

            with execute_sql(conn, "PRAGMA journal_mode") as cursor:
                journal_mode = cursor.fetchone()[0]
                assert journal_mode == "wal"

            with execute_sql(conn, "PRAGMA synchronous") as cursor:
                synchronous = cursor.fetchone()[0]
                assert synchronous == 1  # NORMAL mode

    def test_pragma_settings_applied_backward_compat(self, temp_db):
        """Test that PRAGMA settings are applied via backward compatibility functions."""
        with get_database_connection(temp_db) as conn:
            with execute_sql(conn, "PRAGMA foreign_keys") as cursor:
                foreign_keys = cursor.fetchone()[0]
                assert foreign_keys == 1

            with execute_sql(conn, "PRAGMA journal_mode") as cursor:
                journal_mode = cursor.fetchone()[0]
                assert journal_mode == "wal"

            with execute_sql(conn, "PRAGMA synchronous") as cursor:
                synchronous = cursor.fetchone()[0]
                assert synchronous == 1  # NORMAL mode


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # Initialize database with basic table
    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        with safe_cursor(conn) as cursor:
            cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
            cursor.execute("INSERT INTO test (value) VALUES ('test_data')")
        conn.commit()
    finally:
        if conn:
            conn.close()

    yield db_path

    # Cleanup
    try:
        db_path.unlink()
    except FileNotFoundError:
        pass


@pytest.fixture(autouse=True)
def cleanup_global_pool():
    """Ensure global pool is cleaned up after each test."""
    # Clean up before test to ensure clean state
    close_database_pool()

    yield

    # Clean up after test to prevent resource leaks
    close_database_pool()
    # Force garbage collection to clean up any remaining connections
    gc.collect()
