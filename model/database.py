"""Подключение к SQLite и схема таблиц."""
import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    login TEXT PRIMARY KEY, password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL, role TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS space_objects (
    catalog_number TEXT PRIMARY KEY,
    intl_designator TEXT NOT NULL UNIQUE,
    object_type TEXT NOT NULL, size_m REAL NOT NULL,
    semi_major_axis_km REAL NOT NULL, eccentricity REAL NOT NULL,
    inclination_deg REAL NOT NULL,
    status TEXT NOT NULL, registered_at TEXT NOT NULL, last_observed_at TEXT);

CREATE TABLE IF NOT EXISTS tools (
    tool_id TEXT PRIMARY KEY, tool_type TEXT NOT NULL,
    min_altitude_km REAL NOT NULL, max_altitude_km REAL NOT NULL,
    min_inclination_deg REAL NOT NULL, max_inclination_deg REAL NOT NULL,
    sensitivity_m REAL NOT NULL, mode TEXT NOT NULL, status TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_id TEXT NOT NULL REFERENCES tools(tool_id),
    catalog_number TEXT NOT NULL REFERENCES space_objects(catalog_number),
    observed_at TEXT NOT NULL, raw_data TEXT NOT NULL,
    result TEXT NOT NULL, operator_login TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS journal (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL, catalog_number TEXT NOT NULL,
    occurred_at TEXT NOT NULL, details TEXT NOT NULL);
"""


class Database:
    """Обёртка над соединением SQLite (``":memory:"`` удобно для тестов)."""

    def __init__(self, path: str = ":memory:") -> None:
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(_SCHEMA)
        self.connection.commit()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        cursor = self.connection.execute(sql, params)
        self.connection.commit()
        return cursor

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self.connection.execute(sql, params).fetchall()

    def close(self) -> None:
        self.connection.close()
