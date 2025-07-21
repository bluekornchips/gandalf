"""
Test database pool functionality and connection management.
"""

import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import execute_sql, safe_cursor


class TestDatabasePool:
    """Test database connection pooling and management."""

    def test_safe_cursor_context_manager(self):
        """Test safe_cursor context manager works correctly."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            # Create a test table
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute("CREATE TABLE hobbits (id INTEGER, name TEXT)")
                conn.execute("INSERT INTO hobbits VALUES (1, 'Frodo Baggins')")
                conn.commit()
            finally:
                conn.close()

            # Test safe_cursor
            with safe_cursor(db_path) as cursor:
                cursor.execute("SELECT * FROM hobbits WHERE id = ?", (1,))
                result = cursor.fetchone()
                assert result == (1, 'Frodo Baggins')

        finally:
            if db_path.exists():
                db_path.unlink()

    def test_execute_sql_function(self):
        """Test execute_sql utility function."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            # Create a test table
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute("CREATE TABLE fellowship (id INTEGER, name TEXT)")
                conn.execute("INSERT INTO fellowship VALUES (1, 'Gandalf Grey')")
                conn.execute("INSERT INTO fellowship VALUES (2, 'Aragorn King')")
                conn.commit()
            finally:
                conn.close()

            # Test execute_sql without parameters
            results = execute_sql(db_path, "SELECT * FROM fellowship")
            assert len(results) == 2
            assert (1, 'Gandalf Grey') in results
            assert (2, 'Aragorn King') in results

            # Test execute_sql with parameters
            results = execute_sql(db_path, "SELECT * FROM fellowship WHERE name = ?", ('Gandalf Grey',))
            assert len(results) == 1
            assert results[0] == (1, 'Gandalf Grey')

        finally:
            if db_path.exists():
                db_path.unlink()

    def test_cursor_cleanup_on_exception(self):
        """Test that cursors are properly cleaned up even when exceptions occur."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            # Create database
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute("CREATE TABLE shire (id INTEGER)")
                conn.commit()
            finally:
                conn.close()

            # Test that exception in cursor context doesn't leak connections
            with pytest.raises(sqlite3.OperationalError):
                with safe_cursor(db_path) as cursor:
                    cursor.execute("INVALID SQL STATEMENT")

            # Should still be able to use database after exception
            results = execute_sql(db_path, "SELECT name FROM sqlite_master WHERE type='table'")
            assert len(results) >= 1

        finally:
            if db_path.exists():
                db_path.unlink()
