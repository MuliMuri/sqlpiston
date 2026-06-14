from abc import ABC
from typing import (
    TYPE_CHECKING, List, Literal, Optional, Sequence, Tuple, Union, cast, overload,
)

from sqlpiston._types import SQLValue

if TYPE_CHECKING:
    from sqlpiston.builder.selectable import Select
    from sqlpiston.compiler.base import Dialect

# ExprValue: a value that can appear in an AST expression.
# Can be a scalar literal, another Field reference, a Select subquery, or a function call.
# 'Select' is a string forward-reference to avoid circular imports with selectable.py.
ExprValue = Union[SQLValue, 'Field', 'Select', 'SQLFunction']


class Field:
    """Column reference. Operator overloading returns AST nodes, not values.

    Usage:
        Field("age") >= 18          → ComparisonNode
        Field("id", "users")        → qualified column
        Field("name").alias("n")    → name AS n
    """

    def __init__(self, name: str, table: Optional[str] = None) -> None:
        self._name = name
        self._table = table
        self._alias: Optional[str] = None

    def __repr__(self) -> str:
        parts: List[str] = []
        if self._table:
            parts.append(self._table)
        parts.append(self._name)
        base = ".".join(parts)
        if self._alias:
            return f"Field({base} AS {self._alias})"
        return f"Field({base})"

    def __eq__(self, value: object) -> 'ComparisonNode':  # type: ignore[override]  # intentional: return AST node, not bool
        return ComparisonNode(self, '=', cast(ExprValue, value))

    def __ne__(self, value: object) -> 'ComparisonNode':  # type: ignore[override]  # intentional: return AST node, not bool
        return ComparisonNode(self, '!=', cast(ExprValue, value))

    def __lt__(self, value: ExprValue) -> 'ComparisonNode':
        return ComparisonNode(self, '<', value)

    def __le__(self, value: ExprValue) -> 'ComparisonNode':
        return ComparisonNode(self, '<=', value)

    def __gt__(self, value: ExprValue) -> 'ComparisonNode':
        return ComparisonNode(self, '>', value)

    def __ge__(self, value: ExprValue) -> 'ComparisonNode':
        return ComparisonNode(self, '>=', value)

    def __hash__(self) -> int:
        return hash((self._name, self._table, self._alias))

    @overload
    def is_in(self, values: Sequence[SQLValue]) -> 'InNode': ...

    @overload
    def is_in(self, values: 'Select') -> 'InNode': ...

    def is_in(self, values: Union[Sequence[SQLValue], 'Select']) -> 'InNode':
        return InNode(self, values)

    def between(self, low: ExprValue, high: ExprValue) -> 'BetweenNode':
        return BetweenNode(self, low, high)

    def is_null(self) -> 'ComparisonNode':
        return ComparisonNode(self, 'IS NULL', None)

    def is_not_null(self) -> 'ComparisonNode':
        return ComparisonNode(self, 'IS NOT NULL', None)

    def alias(self, name: str) -> 'Field':
        f = Field(self._name, self._table)
        f._alias = name
        return f

    @property
    def name(self) -> str:
        return self._name

    @property
    def table(self) -> Optional[str]:
        return self._table

    @property
    def _alias_prop(self) -> Optional[str]:
        return self._alias


class ASTNode(ABC):
    """Base for all expression/statement nodes.

    compile() delegates to a dialect-specific compiler via the visitor pattern.
    """

    def __and__(self, other: 'ASTNode') -> 'LogicalNode':
        return LogicalNode('AND', [self, other])

    def __or__(self, other: 'ASTNode') -> 'LogicalNode':
        return LogicalNode('OR', [self, other])

    def __invert__(self) -> 'LogicalNode':
        return LogicalNode('NOT', [self])

    def compile(self, dialect: Optional['Dialect'] = None) -> Tuple[str, Tuple[ExprValue, ...]]:
        if dialect is None:
            from sqlpiston.compiler.base import Compiler, GenericCompiler
            compiler: Compiler = GenericCompiler()
        else:
            compiler = dialect.get_compiler()
        return compiler.process(self)


class ComparisonNode(ASTNode):
    """leaf: field OP value

    value can be:
    - SQL literal  → field OP %s    (parameterized)
    - Field        → field OP other_field   (table-qualified comparison)
    - Select       → field OP (SELECT ...)  (scalar subquery)
    - SQLFunction  → field OP func(...)
    """

    def __init__(self, field: Field, operator: str, value: ExprValue) -> None:
        self.field = field
        self.operator = operator
        self.value: ExprValue = value

    def __repr__(self) -> str:
        return f"ComparisonNode({self.field} {self.operator} {self.value!r})"


class InNode(ASTNode):
    """leaf: field IN (...literals...)  or  field IN (SELECT ...)"""

    def __init__(self, field: Field, values: Union[Sequence[SQLValue], 'Select']) -> None:
        self.field = field
        self.values: Union[Sequence[SQLValue], 'Select'] = values

    def __repr__(self) -> str:
        return f"InNode({self.field} IN {self.values!r})"


class BetweenNode(ASTNode):
    """leaf: field BETWEEN low AND high"""

    def __init__(self, field: Field, low: ExprValue, high: ExprValue) -> None:
        self.field = field
        self.low: ExprValue = low
        self.high: ExprValue = high

    def __repr__(self) -> str:
        return f"BetweenNode({self.field} BETWEEN {self.low!r} AND {self.high!r})"


class LogicalNode(ASTNode):
    """composite: AND / OR / NOT.

    Same-operator flattening: A & B & C → one LogicalNode('AND', [A,B,C]),
    not nested.
    """

    def __init__(self, operator: Literal['AND', 'OR', 'NOT'], children: List[ASTNode]) -> None:
        self.operator = operator
        self.children = children

    def __and__(self, other: ASTNode) -> 'LogicalNode':
        if self.operator == 'AND':
            return LogicalNode('AND', self.children + [other])
        return LogicalNode('AND', [self, other])

    def __or__(self, other: ASTNode) -> 'LogicalNode':
        if self.operator == 'OR':
            return LogicalNode('OR', self.children + [other])
        return LogicalNode('OR', [self, other])

    def __repr__(self) -> str:
        return f"LogicalNode({self.operator}, children={len(self.children)})"


class ExistsNode(ASTNode):
    """EXISTS (SELECT ...)  or  NOT EXISTS (SELECT ...)"""

    def __init__(self, select: 'Select', negated: bool = False) -> None:
        self.select = select
        self.negated = negated

    def __repr__(self) -> str:
        prefix = "NOT EXISTS" if self.negated else "EXISTS"
        return f"ExistsNode({prefix} {self.select!r})"


class CaseNode(ASTNode):
    """CASE WHEN cond1 THEN val1 WHEN cond2 THEN val2 ... [ELSE default] END

    Usage:
        CaseNode()
            .when(Field("score") >= 90, "A")
            .when(Field("score") >= 80, "B")
            .else_("C")
    """

    def __init__(self) -> None:
        self._whens: List[Tuple[ASTNode, ExprValue]] = []
        self._else: Optional[ExprValue] = None

    def when(self, condition: ASTNode, result: ExprValue) -> 'CaseNode':
        self._whens.append((condition, result))
        return self

    def else_(self, default: ExprValue) -> 'CaseNode':
        self._else = default
        return self

    def __repr__(self) -> str:
        return f"CaseNode(whens={len(self._whens)}, has_else={self._else is not None})"


class SQLFunction(ASTNode):
    """SQL function call: COUNT(*), SUM(col), COALESCE(a, b), etc.

    Usage:
        SQLFunction("count", "*")
        SQLFunction("coalesce", Field("name"), "N/A")
        SQLFunction("sum", Field("amount"))
    """

    def __init__(self, name: str, *args: Union[str, Field, 'SQLFunction']) -> None:
        self.name = name
        self.args: Tuple[Union[str, Field, 'SQLFunction'], ...] = args
        self._alias: Optional[str] = None

    def alias(self, name: str) -> 'SQLFunction':
        self._alias = name
        return self

    def __repr__(self) -> str:
        alias_str = f" AS {self._alias}" if self._alias else ""
        return f"SQLFunction({self.name}({', '.join(repr(a) for a in self.args)}){alias_str})"
