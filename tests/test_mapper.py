from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from sqlpiston._types import SQLValue
from sqlpiston.core.engine.base import Cursor
from sqlpiston.orm.mapper import ResultSet


class MockCursor(Cursor):
    def __init__(self, data: List[Tuple[SQLValue, ...]],
                 columns: List[str]) -> None:
        self._data = data
        self._desc = [(col, 0, None, None, None, None, None) for col in columns]

    def fetchall(self) -> List[Tuple[SQLValue, ...]]:
        return list(self._data)

    def fetchone(self) -> Optional[Tuple[SQLValue, ...]]:
        return self._data[0] if self._data else None

    @property
    def rowcount(self) -> int:
        return len(self._data)

    @property
    def description(self) -> List[Tuple[str, int, Any, Any, Any, Any, Any]]:
        return self._desc


@dataclass
class User:
    id: int
    name: str
    age: int


class TestResultSet:
    def test_all(self) -> None:
        cursor = MockCursor([(1, "Alice", 30)], ["id", "name", "age"])
        rs = ResultSet(cursor, ["id", "name", "age"])
        rows = rs.all()
        assert rows == [{"id": 1, "name": "Alice", "age": 30}]

    def test_all_empty(self) -> None:
        cursor = MockCursor([], ["id", "name"])
        rs = ResultSet(cursor, ["id", "name"])
        assert rs.all() == []

    def test_one(self) -> None:
        cursor = MockCursor([(1, "Alice")], ["id", "name"])
        rs = ResultSet(cursor, ["id", "name"])
        row = rs.one()
        assert row == {"id": 1, "name": "Alice"}

    def test_one_empty_raises(self) -> None:
        cursor = MockCursor([], ["id"])
        rs = ResultSet(cursor, ["id"])
        try:
            rs.one()
            assert False
        except ValueError:
            pass

    def test_one_multiple_raises(self) -> None:
        cursor = MockCursor([(1,), (2,)], ["id"])
        rs = ResultSet(cursor, ["id"])
        try:
            rs.one()
            assert False
        except ValueError:
            pass

    def test_one_or_none(self) -> None:
        cursor = MockCursor([], ["id"])
        rs = ResultSet(cursor, ["id"])
        assert rs.one_or_none() is None

    def test_first(self) -> None:
        cursor = MockCursor([(1, "A"), (2, "B")], ["id", "name"])
        rs = ResultSet(cursor, ["id", "name"])
        assert rs.first() == {"id": 1, "name": "A"}

    def test_first_empty(self) -> None:
        cursor = MockCursor([], ["id"])
        rs = ResultSet(cursor, ["id"])
        assert rs.first() is None

    def test_scalar(self) -> None:
        cursor = MockCursor([(42,)], ["val"])
        rs = ResultSet(cursor, ["val"])
        assert rs.scalar() == 42

    def test_scalar_empty_raises(self) -> None:
        cursor = MockCursor([], ["val"])
        rs = ResultSet(cursor, ["val"])
        try:
            rs.scalar()
            assert False
        except ValueError:
            pass

    def test_map(self) -> None:
        cursor = MockCursor([(1, "Alice", 30), (2, "Bob", 25)], ["id", "name", "age"])
        rs = ResultSet(cursor, ["id", "name", "age"])
        users = rs.map(User)
        assert len(users) == 2
        assert isinstance(users[0], User)
        assert users[0].name == "Alice"
        assert users[1].name == "Bob"

    def test_map_one(self) -> None:
        cursor = MockCursor([(1, "Alice", 30)], ["id", "name", "age"])
        rs = ResultSet(cursor, ["id", "name", "age"])
        user = rs.map_one(User)
        assert isinstance(user, User)
        assert user.name == "Alice"

    def test_rowcount(self) -> None:
        cursor = MockCursor([(1,), (2,), (3,)], ["id"])
        rs = ResultSet(cursor, ["id"])
        assert rs.rowcount == 3
