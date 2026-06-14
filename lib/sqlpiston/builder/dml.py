from typing import TYPE_CHECKING, Dict, Optional, Tuple

from sqlpiston.builder.nodes import ASTNode
from sqlpiston._types import ColumnValue

if TYPE_CHECKING:
    from sqlpiston.builder.selectable import Select


class Insert(ASTNode):
    """INSERT INTO table (col1, col2) VALUES (v1, v2)
       INSERT INTO table (col1, col2) SELECT ...
    """

    def __init__(self) -> None:
        self._table: Optional[str] = None
        self._data: Optional[Dict[str, ColumnValue]] = None
        self._select: Optional['Select'] = None

    def into(self, table: str) -> 'Insert':
        self._table = table
        return self

    def values(self, data: Dict[str, ColumnValue]) -> 'Insert':
        self._data = data
        self._select = None
        return self

    def select(self, select: 'Select') -> 'Insert':
        self._select = select
        self._data = None
        return self

    def __repr__(self) -> str:
        return f"Insert(into={self._table!r})"


class Update(ASTNode):
    """UPDATE table SET col1=v1, col2=v2 WHERE condition"""

    def __init__(self) -> None:
        self._table: Optional[str] = None
        self._data: Optional[Dict[str, ColumnValue]] = None
        self._where: Optional[ASTNode] = None

    def table(self, name: str) -> 'Update':
        self._table = name
        return self

    def set(self, data: Dict[str, ColumnValue]) -> 'Update':
        self._data = data
        return self

    def where(self, condition: ASTNode) -> 'Update':
        self._where = condition
        return self

    def __repr__(self) -> str:
        return f"Update(table={self._table!r})"


class Delete(ASTNode):
    """DELETE FROM table WHERE condition"""

    def __init__(self) -> None:
        self._table: Optional[str] = None
        self._where: Optional[ASTNode] = None

    def from_table(self, table: str) -> 'Delete':
        self._table = table
        return self

    def where(self, condition: ASTNode) -> 'Delete':
        self._where = condition
        return self

    def __repr__(self) -> str:
        return f"Delete(from={self._table!r})"


class Upsert(ASTNode):
    """Standard UPSERT — AST stores intent; dialect compilers translate per DB.

    MySQL compiler  → INSERT INTO ... VALUES (...) ON DUPLICATE KEY UPDATE ...
    SQLite compiler → INSERT INTO ... VALUES (...) ON CONFLICT (...) DO UPDATE SET ...

    Usage:
        Upsert()
            .into("users")
            .values({"id": 1, "name": "X"})
            .on_conflict("id")
            .do_update({"name": "X"})
    """

    def __init__(self) -> None:
        self._table: Optional[str] = None
        self._data: Optional[Dict[str, ColumnValue]] = None
        self._conflict_columns: Optional[Tuple[str, ...]] = None
        self._update_data: Optional[Dict[str, ColumnValue]] = None
        self._do_nothing: bool = False

    def into(self, table: str) -> 'Upsert':
        self._table = table
        return self

    def values(self, data: Dict[str, ColumnValue]) -> 'Upsert':
        self._data = data
        return self

    def on_conflict(self, *columns: str) -> 'Upsert':
        self._conflict_columns = columns
        return self

    def do_update(self, data: Dict[str, ColumnValue]) -> 'Upsert':
        self._update_data = data
        self._do_nothing = False
        return self

    def do_nothing(self) -> 'Upsert':
        self._do_nothing = True
        return self

    def __repr__(self) -> str:
        return f"Upsert(into={self._table!r}, conflict={self._conflict_columns!r})"
