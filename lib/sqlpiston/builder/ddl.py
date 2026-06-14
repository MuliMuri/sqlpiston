from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, List, Optional, Tuple

from sqlpiston.builder.nodes import ASTNode
from sqlpiston._types import SQLValue

if TYPE_CHECKING:
    from sqlpiston.builder.selectable import Select


class AlterAction(Enum):
    ADD = 1
    DROP = 2
    MODIFY = 3


@dataclass
class ColumnDef:
    """Column definition for CREATE TABLE."""
    name: str
    type_: str
    nullable: bool = True
    primary_key: bool = False
    default: Optional[SQLValue] = None
    unique: bool = False


class CreateTable(ASTNode):
    """CREATE TABLE name (col1 TYPE, col2 TYPE, ...)"""

    def __init__(self) -> None:
        self._table: Optional[str] = None
        self._if_not_exists: bool = False
        self._columns: List[ColumnDef] = []

    def table(self, name: str) -> 'CreateTable':
        self._table = name
        return self

    def if_not_exists(self) -> 'CreateTable':
        self._if_not_exists = True
        return self

    def column(self, name: str, type_: str, *,
               nullable: bool = True,
               primary_key: bool = False,
               default: Optional[SQLValue] = None,
               unique: bool = False) -> 'CreateTable':
        self._columns.append(ColumnDef(
            name=name, type_=type_, nullable=nullable,
            primary_key=primary_key, default=default, unique=unique,
        ))
        return self

    def columns(self, *col_defs: ColumnDef) -> 'CreateTable':
        self._columns.extend(col_defs)
        return self

    def __repr__(self) -> str:
        return f"CreateTable(table={self._table!r}, columns={len(self._columns)})"


class AlterTable(ASTNode):
    """ALTER TABLE name ADD/DROP/MODIFY COLUMN ..."""

    def __init__(self) -> None:
        self._table: Optional[str] = None
        self._actions: List[Tuple[AlterAction, str, Optional[str], Optional[ColumnDef]]] = []

    def table(self, name: str) -> 'AlterTable':
        self._table = name
        return self

    def add_column(self, name: str, type_: str, *,
                   nullable: bool = True,
                   default: Optional[SQLValue] = None) -> 'AlterTable':
        col_def = ColumnDef(name=name, type_=type_, nullable=nullable, default=default)
        self._actions.append((AlterAction.ADD, name, type_, col_def))
        return self

    def drop_column(self, name: str) -> 'AlterTable':
        self._actions.append((AlterAction.DROP, name, None, None))
        return self

    def modify_column(self, name: str, type_: str, *,
                      nullable: bool = True,
                      default: Optional[SQLValue] = None) -> 'AlterTable':
        col_def = ColumnDef(name=name, type_=type_, nullable=nullable, default=default)
        self._actions.append((AlterAction.MODIFY, name, type_, col_def))
        return self

    def __repr__(self) -> str:
        return f"AlterTable(table={self._table!r}, actions={len(self._actions)})"


class DropTable(ASTNode):
    """DROP TABLE [IF EXISTS] name"""

    def __init__(self) -> None:
        self._table: Optional[str] = None
        self._if_exists: bool = False

    def table(self, name: str) -> 'DropTable':
        self._table = name
        return self

    def if_exists(self) -> 'DropTable':
        self._if_exists = True
        return self

    def __repr__(self) -> str:
        return f"DropTable(table={self._table!r}, if_exists={self._if_exists})"


class CreateIndex(ASTNode):
    """CREATE [UNIQUE] INDEX [IF NOT EXISTS] name ON table (col1, col2, ...)"""

    def __init__(self) -> None:
        self._name: Optional[str] = None
        self._table: Optional[str] = None
        self._columns: Tuple[str, ...] = ()
        self._unique: bool = False
        self._if_not_exists: bool = False

    def name(self, idx_name: str) -> 'CreateIndex':
        self._name = idx_name
        return self

    def on(self, table: str) -> 'CreateIndex':
        self._table = table
        return self

    def columns(self, *cols: str) -> 'CreateIndex':
        self._columns = cols
        return self

    def unique(self) -> 'CreateIndex':
        self._unique = True
        return self

    def if_not_exists(self) -> 'CreateIndex':
        self._if_not_exists = True
        return self

    def __repr__(self) -> str:
        return f"CreateIndex(name={self._name!r}, table={self._table!r})"


class DropIndex(ASTNode):
    """DROP INDEX [IF EXISTS] name ON table"""

    def __init__(self) -> None:
        self._name: Optional[str] = None
        self._table: Optional[str] = None
        self._if_exists: bool = False

    def name(self, idx_name: str) -> 'DropIndex':
        self._name = idx_name
        return self

    def on(self, table: str) -> 'DropIndex':
        self._table = table
        return self

    def if_exists(self) -> 'DropIndex':
        self._if_exists = True
        return self

    def __repr__(self) -> str:
        return f"DropIndex(name={self._name!r}, table={self._table!r})"


class CreateView(ASTNode):
    """CREATE VIEW [IF NOT EXISTS] name AS SELECT ..."""

    def __init__(self) -> None:
        self._name: Optional[str] = None
        self._select: Optional['Select'] = None
        self._if_not_exists: bool = False

    def name(self, view_name: str) -> 'CreateView':
        self._name = view_name
        return self

    def as_(self, select: 'Select') -> 'CreateView':
        self._select = select
        return self

    def if_not_exists(self) -> 'CreateView':
        self._if_not_exists = True
        return self

    def __repr__(self) -> str:
        return f"CreateView(name={self._name!r})"


class DropView(ASTNode):
    """DROP VIEW [IF EXISTS] name"""

    def __init__(self) -> None:
        self._name: Optional[str] = None
        self._if_exists: bool = False

    def name(self, view_name: str) -> 'DropView':
        self._name = view_name
        return self

    def if_exists(self) -> 'DropView':
        self._if_exists = True
        return self

    def __repr__(self) -> str:
        return f"DropView(name={self._name!r})"


class Truncate(ASTNode):
    """TRUNCATE TABLE name"""

    def __init__(self) -> None:
        self._table: Optional[str] = None

    def table(self, name: str) -> 'Truncate':
        self._table = name
        return self

    def __repr__(self) -> str:
        return f"Truncate(table={self._table!r})"
