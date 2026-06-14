from typing import Any, Dict, List, Optional, Tuple, cast

from sqlpiston.builder.nodes import ExprValue
from sqlpiston._types import SQLValue
from sqlpiston.compiler.mysql import MySQLDialect
from sqlpiston.core.engine.base import Connection, Cursor, Engine


class MySQLCursor(Cursor):  # pragma: no cover — requires mysql.connector (optional dependency)
    def __init__(self, raw_cursor: Any) -> None:
        self._cursor = raw_cursor

    def fetchall(self) -> List[Tuple[SQLValue, ...]]:
        return [tuple(row) for row in self._cursor.fetchall()]

    def fetchone(self) -> Optional[Tuple[SQLValue, ...]]:
        row = self._cursor.fetchone()
        return tuple(row) if row else None

    @property
    def rowcount(self) -> int:
        return int(self._cursor.rowcount)

    @property
    def description(self) -> List[Tuple[str, int, Any, Any, Any, Any, Any]]:  # pragma: no cover — requires mysql.connector
        desc = self._cursor.description
        if desc is None:
            return []
        return cast(List[Tuple[str, int, Any, Any, Any, Any, Any]], desc)


class MySQLConnection(Connection):  # pragma: no cover — requires mysql.connector (optional dependency)
    def __init__(self, raw_conn: Any) -> None:
        self._conn = raw_conn

    def execute(self, sql: str, params: Tuple[ExprValue, ...]) -> MySQLCursor:
        cursor = self._conn.cursor()
        cursor.execute(sql, params)
        return MySQLCursor(cursor)

    def begin(self) -> None:
        self._conn.begin()

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()


class MySQLEngine(Engine):
    def __init__(self) -> None:
        self._config: Optional[Dict[str, Any]] = None
        self._conn: Any = None

    def init_engine(self, host: str, port: int, user: str, password: str, database: str) -> None:
        self._config = {
            'host': host, 'port': port,
            'user': user, 'password': password,
            'database': database,
        }

    @property
    def dialect(self) -> MySQLDialect:
        return MySQLDialect()

    def connect(self) -> MySQLConnection:  # pragma: no cover — requires mysql.connector (optional dependency)
        if self._config is None:
            raise RuntimeError("Call init_engine() before connect()")
        import mysql.connector  # type: ignore[import-not-found]
        self._conn = mysql.connector.connect(**self._config)
        return MySQLConnection(self._conn)

    def close(self) -> None:  # pragma: no cover — requires mysql.connector
        if self._conn:
            self._conn.close()
            self._conn = None
