import sqlite3
from typing import Any, List, Optional, Tuple

from sqlpiston.builder.nodes import ExprValue
from sqlpiston._types import SQLValue
from sqlpiston.compiler.sqlite import SQLiteDialect
from sqlpiston.core.engine.base import Connection, Cursor, Engine


class SQLiteCursor(Cursor):
    def __init__(self, raw_cursor: sqlite3.Cursor) -> None:
        self._cursor = raw_cursor

    def fetchall(self) -> List[Tuple[SQLValue, ...]]:
        return [tuple(row) for row in self._cursor.fetchall()]

    def fetchone(self) -> Optional[Tuple[SQLValue, ...]]:
        row = self._cursor.fetchone()
        return tuple(row) if row else None

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    @property
    def description(self) -> List[Tuple[str, int, Any, Any, Any, Any, Any]]:
        desc = self._cursor.description
        if desc is None:
            return []
        return [tuple(d) for d in desc]


class SQLiteConnection(Connection):
    def __init__(self, raw_conn: sqlite3.Connection) -> None:
        self._conn = raw_conn

    def execute(self, sql: str, params: Tuple[ExprValue, ...]) -> SQLiteCursor:
        cursor = self._conn.cursor()
        cursor.execute(sql, params)
        return SQLiteCursor(cursor)

    def begin(self) -> None:
        self._conn.execute("BEGIN")

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()


class SQLiteEngine(Engine):
    def __init__(self) -> None:
        self._file_path: Optional[str] = None
        self._conn: Optional[sqlite3.Connection] = None

    def init_engine(self, file_path: str) -> None:
        self._file_path = file_path

    @property
    def dialect(self) -> SQLiteDialect:
        return SQLiteDialect()

    def connect(self) -> SQLiteConnection:
        if self._file_path is None:
            raise RuntimeError("Call init_engine() before connect()")
        self._conn = sqlite3.connect(self._file_path)
        return SQLiteConnection(self._conn)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
