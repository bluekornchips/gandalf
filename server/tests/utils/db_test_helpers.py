"""
Database test helpers for SQLite: context manager for temp DBs and table creation.
"""

import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any


@contextmanager
def temporary_sqlite_db(
    schema_sql: str | None = None,
    data: dict[str, list[Any]] | None = None,
):
    """
    Context manager for a temporary SQLite database file.
    Optionally creates tables and populates them with data.
    Yields the Path to the database file.
    """
    db_file = Path(tempfile.mktemp(suffix=".db"))
    try:
        with sqlite3.connect(str(db_file)) as conn:
            if schema_sql:
                conn.executescript(schema_sql)
            if data:
                for table, rows in data.items():
                    if rows:
                        placeholders = ", ".join(["?" for _ in rows[0]])
                        conn.executemany(
                            f"INSERT INTO {table} VALUES ({placeholders})",
                            rows,
                        )
            conn.commit()
        yield db_file
    finally:
        if db_file.exists():
            db_file.unlink()


def create_table_sql(table: str, columns: list[str]) -> str:
    """
    Helper to generate a CREATE TABLE statement for SQLite.
    """
    cols = ", ".join([f"{col} TEXT" for col in columns])
    return f"CREATE TABLE IF NOT EXISTS {table} ({cols});"
