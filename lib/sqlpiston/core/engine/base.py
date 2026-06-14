from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, List, Optional, Tuple

from sqlpiston.builder.nodes import ExprValue
from sqlpiston._types import SQLValue
from sqlpiston.compiler.base import Dialect


class DBType(Enum):
    MySQL = 1
    SQLite = 2


class Cursor(ABC):
    """Query result cursor. Wraps DB-API cursor."""

    @abstractmethod
    def fetchall(self) -> List[Tuple[SQLValue, ...]]:
        ...

    @abstractmethod
    def fetchone(self) -> Optional[Tuple[SQLValue, ...]]:
        ...

    @property
    @abstractmethod
    def rowcount(self) -> int:
        ...

    @property
    @abstractmethod
    def description(self) -> List[Tuple[str, int, Any, Any, Any, Any, Any]]:
        ...


class Connection(ABC):
    """A single database connection."""

    @abstractmethod
    def execute(self, sql: str, params: Tuple[ExprValue, ...]) -> Cursor:
        ...

    @abstractmethod
    def begin(self) -> None:
        ...

    @abstractmethod
    def commit(self) -> None:
        ...

    @abstractmethod
    def rollback(self) -> None:
        ...

    @abstractmethod
    def close(self) -> None:
        ...

    def __enter__(self) -> 'Connection':  # pragma: no cover — abstract class, covered via subclasses
        return self

    def __exit__(self, *args: Any) -> None:  # pragma: no cover — abstract class, covered via subclasses
        self.close()


class Engine(ABC):
    """Abstract database engine."""

    @property
    @abstractmethod
    def dialect(self) -> Dialect:
        ...

    @abstractmethod
    def connect(self) -> Connection:
        ...

    @abstractmethod
    def close(self) -> None:
        ...

    def __enter__(self) -> 'Engine':  # pragma: no cover — abstract class, covered via subclasses
        return self

    def __exit__(self, *args: Any) -> None:  # pragma: no cover — abstract class, covered via subclasses
        self.close()


def DBEngine(db_type: DBType) -> Engine:
    """Factory: returns typed engine by DBType."""
    if db_type == DBType.MySQL:
        from sqlpiston.core.engine.mysql import MySQLEngine
        return MySQLEngine()
    elif db_type == DBType.SQLite:
        from sqlpiston.core.engine.sqlite import SQLiteEngine
        return SQLiteEngine()
    else:
        raise ValueError(f"Unsupported DB type: {db_type}")
