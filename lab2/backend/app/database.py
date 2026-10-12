"""SQLite helpers for the People Management API."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DEFAULT_DATABASE_PATH = "./data/people.db"


def resolve_database_path(path: str | Path | None = None) -> str:
    """Return the configured database path and create its parent directory."""
    raw_path = str(path) if path is not None else os.getenv("DATABASE_PATH", DEFAULT_DATABASE_PATH)

    # Each operation opens its own connection, so an in-memory database would
    # not persist between requests. Require a file-backed database instead.
    if raw_path == ":memory:":
        raise ValueError("DATABASE_PATH must be a file path; :memory: is not supported")

    database_path = Path(raw_path).expanduser()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return str(database_path)


@contextmanager
def get_connection(path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    """Open a short-lived connection and commit or roll back its transaction."""
    connection = sqlite3.connect(resolve_database_path(path), timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db(path: str | Path | None = None) -> None:
    """Create the people table if it does not exist yet."""
    with get_connection(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 100),
                email TEXT NOT NULL CHECK (length(trim(email)) BETWEEN 3 AND 254),
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )
            """
        )
