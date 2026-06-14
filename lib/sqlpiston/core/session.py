from typing import Any, Optional

from sqlpiston.builder.nodes import ASTNode
from sqlpiston.core.engine.base import Connection, Engine
from sqlpiston.core.pool import ConnectionPool
from sqlpiston.orm.mapper import ResultSet


class Session:
    """Entry point for users. Binds engine, compiles AST, executes SQL.

    Usage::

        s = Session(engine)
        result = s.execute(
            Select().select('id', 'name').from_table('users').where(Field('age') >= 18)
        )
        s.commit()
        s.close()
    """

    def __init__(self, engine: Engine, pool: Optional[ConnectionPool] = None) -> None:
        self._engine = engine
        self._pool = pool if pool is not None else ConnectionPool(engine)
        self._current_conn: Optional[Connection] = None

    def _get_conn(self) -> Connection:
        if self._current_conn is None:
            self._current_conn = self._pool.acquire()
        return self._current_conn

    def execute(self, stmt: ASTNode) -> ResultSet:
        conn = self._get_conn()
        sql, params = stmt.compile(self._engine.dialect)
        cursor = conn.execute(sql, params)
        column_names = [desc[0] for desc in cursor.description] if cursor.description else []
        return ResultSet(cursor, column_names)

    def begin(self) -> None:
        conn = self._get_conn()
        conn.begin()

    def commit(self) -> None:
        if self._current_conn:
            self._current_conn.commit()

    def rollback(self) -> None:
        if self._current_conn:
            self._current_conn.rollback()

    def close(self) -> None:
        if self._current_conn:
            self._pool.release(self._current_conn)
            self._current_conn = None
        self._pool.close()

    def __enter__(self) -> 'Session':
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
