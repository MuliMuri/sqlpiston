from typing import (
    Any, Dict, Iterator, List, Optional, Type, TypeVar,
)

from sqlpiston._types import SQLValue
from sqlpiston.core.engine.base import Cursor

T = TypeVar('T')


class ResultSet:
    """Iterable set of mapped results from a query."""

    def __init__(self, cursor: Cursor, column_names: List[str]) -> None:
        self._cursor = cursor
        self._column_names = column_names

    def all(self) -> List[Dict[str, SQLValue]]:
        rows = self._cursor.fetchall()
        return [dict(zip(self._column_names, row)) for row in rows]

    def one(self) -> Dict[str, SQLValue]:
        rows = self.all()
        if len(rows) == 0:
            raise ValueError("Expected exactly one row, got none")
        if len(rows) > 1:
            raise ValueError(f"Expected exactly one row, got {len(rows)}")
        return rows[0]

    def one_or_none(self) -> Optional[Dict[str, SQLValue]]:
        rows = self.all()
        if len(rows) == 0:
            return None
        if len(rows) > 1:
            raise ValueError(f"Expected at most one row, got {len(rows)}")
        return rows[0]

    def first(self) -> Optional[Dict[str, SQLValue]]:
        row = self._cursor.fetchone()
        if row is None:
            return None
        return dict(zip(self._column_names, row))

    def scalar(self) -> Any:
        row = self._cursor.fetchone()
        if row is None:
            raise ValueError("Expected at least one row for scalar(), got none")
        return row[0]

    def map(self, target: Type[T]) -> List[T]:
        rows = self.all()
        results: List[T] = []
        for row in rows:
            obj = target(**row)
            results.append(obj)
        return results

    def map_one(self, target: Type[T]) -> T:
        row = self.one()
        return target(**row)

    def __iter__(self) -> Iterator[Dict[str, SQLValue]]:
        all_rows = self.all()
        return iter(all_rows)

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount
