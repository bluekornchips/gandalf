"""
Database connection pooling utility for SQLite databases.

The global pattern is contained to this module and provides a clean API
for both controlled (DatabaseService) and convenient (global functions) usage.
- SQLite connection pooling benefits from reuse across the application
- Many utility functions need database access without service injection
- Module-level singleton prevents connection leaks from abandoned pools
- Thread-safe implementation for no race conditons
- Alternative would require dependency injection throughout the codebase.
    - I tried this and it was a nightmare and slow.

"""

import sqlite3
import threading
from collections import defaultdict
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from src.config.constants.database import SQL_SELECT_ONE
from src.utils.common import log_debug, log_error


class ConnectionPool:
    """Thread-safe SQLite connection pool with path-based pooling and health monitoring."""

    def __init__(self, max_connections: int = 5, timeout: float = 2.0) -> None:
        """Initialize the connection pool."""
        self.max_connections = max_connections
        self.timeout = timeout
        self._pools: dict[str, list[sqlite3.Connection]] = defaultdict(list)
        self._lock = threading.Lock()

    def _create_connection(self, db_path: Path) -> sqlite3.Connection:
        """Create a new SQLite connection with optimized settings."""
        conn = sqlite3.connect(
            str(db_path), timeout=self.timeout, check_same_thread=False
        )
        # Enable foreign keys and WAL mode for better performance
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn

    def _close_connection_safely(self, conn: sqlite3.Connection) -> None:
        """Safely close a database connection with error handling."""
        if conn:
            try:
                conn.close()
                log_debug("Connection closed safely")
            except (sqlite3.Error, OSError) as e:
                log_error(e, "error closing database connection")

    def _is_connection_healthy(self, conn: sqlite3.Connection) -> bool:
        """Test if a connection is still healthy and usable."""
        try:
            if not conn:
                return False

            cursor = conn.cursor()
            try:
                cursor.execute(SQL_SELECT_ONE)
                cursor.fetchone()
                return True
            finally:
                try:
                    cursor.close()
                except (sqlite3.Error, OSError):
                    pass
        except (sqlite3.Error, OSError) as e:
            log_error(e, "connection health check failed")
            return False

    @contextmanager
    def get_connection(
        self, db_path: Path
    ) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection from the pool or create a new one."""
        db_path_str = str(db_path)
        conn = None

        try:
            # Try to get an existing connection from the pool
            with self._lock:
                if self._pools[db_path_str]:
                    conn = self._pools[db_path_str].pop()
                    log_debug(f"Reusing pooled connection for {db_path}")
                else:
                    conn = self._create_connection(db_path)
                    log_debug(f"Created new connection for {db_path}")

            yield conn

        except (sqlite3.Error, OSError) as e:
            log_error(e, f"database connection error for {db_path}")
            if conn:
                self._close_connection_safely(conn)
            raise
        finally:
            if conn:
                if self._is_connection_healthy(conn):
                    with self._lock:
                        if len(self._pools[db_path_str]) < self.max_connections:
                            self._pools[db_path_str].append(conn)
                            log_debug(
                                f"Returned healthy connection to pool for {db_path_str}"
                            )
                        else:
                            self._close_connection_safely(conn)
                            log_debug(
                                f"Pool full, closed excess connection for {db_path_str}"
                            )
                else:
                    self._close_connection_safely(conn)

    def close_all(self) -> None:
        """Close all connections in all pools."""
        with self._lock:
            total_closed = 0
            for db_path_str, connections in self._pools.items():
                for conn in connections:
                    self._close_connection_safely(conn)
                    total_closed += 1
                connections.clear()
            self._pools.clear()
            if total_closed > 0:
                log_debug(f"Closed {total_closed} database connections")

    def get_pool_stats(self) -> dict[str, int]:
        """Get current pool statistics by database path."""
        with self._lock:
            return {
                db_path: len(connections)
                for db_path, connections in self._pools.items()
            }


class DatabaseService:
    """Database service with explicit initialization and lifecycle management."""

    def __init__(self) -> None:
        """Initialize the database service."""
        self._pool: ConnectionPool | None = None
        self._initialized = False
        self._lock = threading.Lock()

    def initialize(self, max_connections: int = 5, timeout: float = 2.0) -> None:
        """Initialize the database service with connection pool."""
        with self._lock:
            if self._initialized:
                return
            self._pool = ConnectionPool(max_connections, timeout)
            self._initialized = True
            log_debug("Database service initialized")

    def is_initialized(self) -> bool:
        """Check if the database service is initialized."""
        return self._initialized

    @contextmanager
    def get_connection(
        self, db_path: Path
    ) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection from the service pool."""
        if not self._initialized or not self._pool:
            raise RuntimeError(
                "DatabaseService not initialized. Call initialize() first."
            )

        with self._pool.get_connection(db_path) as conn:
            yield conn

    def get_pool_stats(self) -> dict[str, int]:
        """Get current pool statistics."""
        if not self._pool:
            return {}
        return self._pool.get_pool_stats()

    def shutdown(self) -> None:
        """Shutdown the database service and close all connections."""
        with self._lock:
            if self._pool:
                self._pool.close_all()
                self._pool = None
                self._initialized = False
                log_debug("Database service shutdown completed")


# Module-level connection pool for convenience functions
_pool: ConnectionPool | None = None
_pool_lock = threading.Lock()


def _get_pool() -> ConnectionPool:
    """Get or create the module-level connection pool."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ConnectionPool()
    return _pool


@contextmanager
def get_database_connection(db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    """Get a database connection using the module-level connection pool."""
    pool = _get_pool()
    with pool.get_connection(db_path) as conn:
        yield conn


def close_all_connections() -> None:
    """Close all connections in the module-level pool."""
    global _pool
    if _pool is not None:
        with _pool_lock:
            if _pool is not None:
                _pool.close_all()
                _pool = None


def get_database_pool() -> DatabaseService:
    """Get a new DatabaseService instance."""
    service = DatabaseService()
    service.initialize()
    return service


def close_database_pool() -> None:
    """Close the database pool."""
    close_all_connections()
