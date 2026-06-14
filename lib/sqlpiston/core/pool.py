import threading
from typing import Any, List

from sqlpiston.core.engine.base import Connection, Engine


class ConnectionPool:
    """Thread-safe connection pool."""

    def __init__(self, engine: Engine, min_size: int = 1, max_size: int = 10) -> None:
        self._engine = engine
        self._min_size = min_size
        self._max_size = max_size
        self._lock = threading.Lock()
        self._available: List[Connection] = []
        self._in_use: int = 0

        for _ in range(min_size):
            self._available.append(engine.connect())

    def acquire(self) -> Connection:
        with self._lock:
            if self._available:
                conn = self._available.pop()
                self._in_use += 1
                return conn
            if self._in_use >= self._max_size:
                raise RuntimeError("Connection pool exhausted")
            conn = self._engine.connect()
            self._in_use += 1
            return conn

    def release(self, conn: Connection) -> None:
        with self._lock:
            self._in_use -= 1
            self._available.append(conn)

    def close(self) -> None:
        with self._lock:
            for conn in self._available:
                conn.close()
            self._available.clear()
            self._in_use = 0

    def __enter__(self) -> 'ConnectionPool':
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
