from typing import TYPE_CHECKING, List, Literal, Optional, Tuple, Union

from sqlpiston.builder.nodes import (
    ASTNode, ExistsNode, Field, SQLFunction,
)

if TYPE_CHECKING:
    pass  # all types needed are in nodes.py already

# SelectColumn is already defined via Field/SQLFunction/Select
# We extend the concept here: a column in a SELECT clause can be str, Field, SQLFunction, or Select (scalar subquery)
SelectColumn = Union[str, Field, SQLFunction, 'Select']


class Select(ASTNode):
    """Fluent SELECT builder. All modifiers return self for chaining.

    Usage:
        Select().select("id", "name").from_table("users").where(Field("age") >= 18)

    Subquery usage:
        sub = Select().select("id").from_table("users").as_("u")
        Select().select("*").from_table(sub)

    Scalar subquery in WHERE:
        sub = Select().select(SQLFunction("avg", "salary")).from_table("employees")
        Select().select("name").from_table("staff").where(Field("salary") > sub)

    EXISTS:
        sub = Select().select("1").from_table("orders").where(...)
        Select().select("name").from_table("users").where(sub.exists())
    """

    def __init__(self) -> None:
        self._columns: List[SelectColumn] = []
        self._distinct: bool = False
        self._from: Optional[Union[str, 'Select']] = None
        self._where: Optional[ASTNode] = None
        self._joins: List[Tuple[str, str, ASTNode]] = []
        self._group_by: List[Union[str, Field]] = []
        self._having: Optional[ASTNode] = None
        self._order_by: List[Tuple[Union[str, Field], str]] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._alias: Optional[str] = None
        self._ctes: Optional[List['CTE']] = None

    def select(self, *columns: SelectColumn) -> 'Select':
        self._columns.extend(columns)
        return self

    def distinct(self) -> 'Select':
        self._distinct = True
        return self

    def from_table(self, table: Union[str, 'Select']) -> 'Select':
        self._from = table
        return self

    def where(self, condition: ASTNode) -> 'Select':
        self._where = condition
        return self

    def join(self, table: str, on: ASTNode,
             how: Literal['INNER', 'LEFT', 'RIGHT', 'CROSS'] = 'INNER') -> 'Select':
        self._joins.append((table, how, on))
        return self

    def left_join(self, table: str, on: ASTNode) -> 'Select':
        return self.join(table, on, how='LEFT')

    def right_join(self, table: str, on: ASTNode) -> 'Select':
        return self.join(table, on, how='RIGHT')

    def cross_join(self, table: str) -> 'Select':
        self._joins.append((table, 'CROSS', None))  # type: ignore[arg-type]  # CROSS JOIN has no ON
        return self

    def group_by(self, *fields: Union[str, Field]) -> 'Select':
        self._group_by.extend(fields)
        return self

    def having(self, condition: ASTNode) -> 'Select':
        self._having = condition
        return self

    def order_by(self, field: Union[str, Field],
                 direction: Literal['ASC', 'DESC'] = 'ASC') -> 'Select':
        self._order_by.append((field, direction))
        return self

    def limit(self, count: int) -> 'Select':
        self._limit = count
        return self

    def offset(self, start: int) -> 'Select':
        self._offset = start
        return self

    def as_(self, alias: str) -> 'Select':
        self._alias = alias
        return self

    def exists(self) -> ExistsNode:
        return ExistsNode(self, negated=False)

    def not_exists(self) -> ExistsNode:
        return ExistsNode(self, negated=True)

    def union(self, other: 'Select') -> 'CompoundSelect':
        return CompoundSelect('UNION', self, other)

    def union_all(self, other: 'Select') -> 'CompoundSelect':
        return CompoundSelect('UNION ALL', self, other)

    def intersect(self, other: 'Select') -> 'CompoundSelect':
        return CompoundSelect('INTERSECT', self, other)

    def except_(self, other: 'Select') -> 'CompoundSelect':
        return CompoundSelect('EXCEPT', self, other)

    def cte(self, name: str) -> 'CTE':
        return CTE(name, self)

    def with_(self, *ctes: 'CTE') -> 'Select':
        self._ctes = list(ctes)
        return self

    def __repr__(self) -> str:
        return f"Select(columns={self._columns}, from={self._from!r}, alias={self._alias!r})"


class CompoundSelect(ASTNode):
    """Combine two Selects: UNION / UNION ALL / INTERSECT / EXCEPT."""

    def __init__(self, operator: str, left: Select, right: Select) -> None:
        self.operator = operator
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        return f"CompoundSelect({self.operator})"


class CTE(ASTNode):
    """CTE node: name AS (SELECT ...)"""

    def __init__(self, name: str, select: Select) -> None:
        self.name = name
        self.select = select

    def __repr__(self) -> str:
        return f"CTE({self.name})"
