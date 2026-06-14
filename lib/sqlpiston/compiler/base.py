from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Type, Union

from sqlpiston.builder.nodes import (
    ASTNode, BetweenNode, CaseNode, ComparisonNode, ExistsNode, Field,
    InNode, LogicalNode, SQLFunction, ExprValue,
)
from sqlpiston.builder.selectable import CompoundSelect, CTE, Select
from sqlpiston.builder.dml import Delete, Insert, Update, Upsert
from sqlpiston.builder.ddl import (
    AlterAction, AlterTable, ColumnDef, CreateIndex, CreateTable,
    CreateView, DropIndex, DropTable, DropView, Truncate,
)


class Compiler(ABC):
    """Base compiler. process() dispatches node type → visit_* method."""

    def process(self, node: ASTNode) -> Tuple[str, Tuple[ExprValue, ...]]:
        if isinstance(node, Select):
            return self.visit_select(node)
        if isinstance(node, CompoundSelect):
            return self.visit_compound_select(node)
        if isinstance(node, CTE):
            return self.visit_cte(node)
        if isinstance(node, Insert):
            return self.visit_insert(node)
        if isinstance(node, Update):
            return self.visit_update(node)
        if isinstance(node, Delete):
            return self.visit_delete(node)
        if isinstance(node, Upsert):
            return self.visit_upsert(node)
        if isinstance(node, CreateTable):
            return self.visit_create_table(node)
        if isinstance(node, AlterTable):
            return self.visit_alter_table(node)
        if isinstance(node, DropTable):
            return self.visit_drop_table(node)
        if isinstance(node, CreateIndex):
            return self.visit_create_index(node)
        if isinstance(node, DropIndex):
            return self.visit_drop_index(node)
        if isinstance(node, CreateView):
            return self.visit_create_view(node)
        if isinstance(node, DropView):
            return self.visit_drop_view(node)
        if isinstance(node, Truncate):
            return self.visit_truncate(node)
        if isinstance(node, ComparisonNode):
            return self.visit_comparison(node)
        if isinstance(node, InNode):
            return self.visit_in(node)
        if isinstance(node, BetweenNode):
            return self.visit_between(node)
        if isinstance(node, LogicalNode):
            return self.visit_logical(node)
        if isinstance(node, ExistsNode):
            return self.visit_exists(node)
        if isinstance(node, CaseNode):
            return self.visit_case(node)
        if isinstance(node, SQLFunction):
            return self.visit_function(node)
        raise TypeError(f"Unknown AST node type: {type(node).__name__}")

    # -- DQL --

    @abstractmethod
    def visit_select(self, node: Select) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover — abstract stub
    @abstractmethod
    def visit_compound_select(self, node: CompoundSelect) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def visit_cte(self, node: CTE) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def visit_insert(self, node: Insert) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def visit_update(self, node: Update) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def visit_delete(self, node: Delete) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def visit_upsert(self, node: Upsert) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def visit_create_table(self, node: CreateTable) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def visit_alter_table(self, node: AlterTable) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def visit_drop_table(self, node: DropTable) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def visit_create_index(self, node: CreateIndex) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def visit_drop_index(self, node: DropIndex) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def visit_create_view(self, node: CreateView) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def visit_drop_view(self, node: DropView) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def visit_truncate(self, node: Truncate) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def visit_comparison(self, node: ComparisonNode) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def visit_in(self, node: InNode) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def visit_between(self, node: BetweenNode) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def visit_logical(self, node: LogicalNode) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def visit_exists(self, node: ExistsNode) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def visit_case(self, node: CaseNode) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def visit_function(self, node: SQLFunction) -> Tuple[str, Tuple[ExprValue, ...]]: ...  # pragma: no cover
    @abstractmethod
    def placeholder(self) -> str: ...  # pragma: no cover — abstract stub
    @abstractmethod
    def quote_identifier(self, name: str) -> str: ...  # pragma: no cover — abstract stub

    # -- Shared helpers --

    def compile_field(self, field: Field) -> str:
        """Render table-qualified field name with proper quoting."""
        parts: List[str] = []
        if field.table:
            parts.append(self.quote_identifier(field.table))
        parts.append(self.quote_identifier(field.name))
        result = ".".join(parts)
        if field._alias_prop:
            result = f"{result} AS {self.quote_identifier(field._alias_prop)}"
        return result

    def compile_from(self, from_src: Union[str, Select]) -> Tuple[str, Tuple[ExprValue, ...]]:
        """Compile FROM clause source."""
        if isinstance(from_src, str):
            return self.quote_identifier(from_src), ()
        # Subquery
        sql, params = self.visit_select(from_src)
        alias = from_src._alias or "sub"
        return f"({sql}) AS {self.quote_identifier(alias)}", params

    def compile_joins(self, joins: List[Tuple[str, str, ASTNode]]) -> Tuple[str, Tuple[ExprValue, ...]]:
        """Compile JOIN clauses."""
        parts: List[str] = []
        params: List[ExprValue] = []
        for table, how, on in joins:
            if how == 'CROSS':
                parts.append(f"CROSS JOIN {self.quote_identifier(table)}")
            else:
                on_sql, on_params = self.process(on)
                parts.append(f"{how} JOIN {self.quote_identifier(table)} ON {on_sql}")
                params.extend(on_params)
        return " ".join(parts), tuple(params)

    def compile_condition(self, node: ASTNode) -> Tuple[str, Tuple[ExprValue, ...]]:
        """Compile a WHERE/HAVING/ON condition."""
        return self.process(node)

    def compile_order_by(self, orders: List[Tuple[Union[str, Field], str]]) -> str:
        """Compile ORDER BY clause."""
        parts: List[str] = []
        for field, direction in orders:
            if isinstance(field, str):
                parts.append(f"{self.quote_identifier(field)} {direction}")
            else:
                parts.append(f"{self.compile_field(field)} {direction}")
        return "ORDER BY " + ", ".join(parts)

    def compile_group_by(self, groups: List[Union[str, Field]]) -> str:
        """Compile GROUP BY clause."""
        parts: List[str] = []
        for g in groups:
            if isinstance(g, str):
                parts.append(self.quote_identifier(g))
            else:
                parts.append(self.compile_field(g))
        return "GROUP BY " + ", ".join(parts)

    def collect_params(self, *results: Tuple[str, Tuple[ExprValue, ...]]) -> Tuple[str, Tuple[ExprValue, ...]]:
        """Join SQL fragments and concatenate params."""
        sql_parts: List[str] = []
        all_params: List[ExprValue] = []
        for sql, params in results:
            if sql:
                sql_parts.append(sql)
            if params:
                all_params.extend(params)
        return " ".join(sql_parts), tuple(all_params)


class GenericCompiler(Compiler):
    """Platform-agnostic compiler. Uses %s and backtick quoting. Serves as baseline."""

    def placeholder(self) -> str:
        return '%s'

    def quote_identifier(self, name: str) -> str:
        return f'`{name}`'

    # -- Expression nodes --

    def visit_comparison(self, node: ComparisonNode) -> Tuple[str, Tuple[ExprValue, ...]]:
        field_str = self.compile_field(node.field)

        # IS NULL / IS NOT NULL — no parameter
        if node.operator in ('IS NULL', 'IS NOT NULL'):
            return f"{field_str} {node.operator}", ()

        value = node.value
        # Field vs Field — table-qualified comparison
        if isinstance(value, Field):
            return f"{field_str} {node.operator} {self.compile_field(value)}", ()

        # Field vs Select — scalar subquery
        if isinstance(value, Select):
            sub_sql, sub_params = self.visit_select(value)
            return f"{field_str} {node.operator} ({sub_sql})", sub_params

        # Field vs SQLFunction
        if isinstance(value, SQLFunction):
            func_sql, func_params = self.visit_function(value)
            return f"{field_str} {node.operator} {func_sql}", func_params

        # Field vs literal
        return f"{field_str} {node.operator} {self.placeholder()}", (value,)

    def visit_in(self, node: InNode) -> Tuple[str, Tuple[ExprValue, ...]]:
        field_str = self.compile_field(node.field)
        values = node.values

        # Subquery
        if isinstance(values, Select):
            sub_sql, sub_params = self.visit_select(values)
            return f"{field_str} IN ({sub_sql})", sub_params

        # Literal list
        placeholders = ", ".join([self.placeholder()] * len(values))
        return f"{field_str} IN ({placeholders})", tuple(values)

    def visit_between(self, node: BetweenNode) -> Tuple[str, Tuple[ExprValue, ...]]:
        field_str = self.compile_field(node.field)
        return (
            f"{field_str} BETWEEN {self.placeholder()} AND {self.placeholder()}",
            (node.low, node.high),
        )

    def visit_logical(self, node: LogicalNode) -> Tuple[str, Tuple[ExprValue, ...]]:
        if node.operator == 'NOT':
            child_sql, child_params = self.process(node.children[0])
            return f"NOT ({child_sql})", child_params

        # AND / OR
        parts: List[str] = []
        params: List[ExprValue] = []
        for child in node.children:
            child_sql, child_params = self.process(child)
            # Wrap non-leaf nodes in parens
            if isinstance(child, LogicalNode) and child.operator != 'NOT':
                child_sql = f"({child_sql})"
            parts.append(child_sql)
            params.extend(child_params)

        separator = f" {node.operator} "
        combined = separator.join(parts)
        if len(parts) > 1:
            combined = f"({combined})"
        return combined, tuple(params)

    def visit_exists(self, node: ExistsNode) -> Tuple[str, Tuple[ExprValue, ...]]:
        sub_sql, sub_params = self.visit_select(node.select)
        keyword = "NOT EXISTS" if node.negated else "EXISTS"
        return f"{keyword} ({sub_sql})", sub_params

    def visit_case(self, node: CaseNode) -> Tuple[str, Tuple[ExprValue, ...]]:
        parts: List[str] = ["CASE"]
        params: List[ExprValue] = []
        for condition, result in node._whens:
            cond_sql, cond_params = self.process(condition)
            parts.append(f"WHEN {cond_sql} THEN {self.placeholder()}")
            params.extend(cond_params)
            params.append(result)
        if node._else is not None:
            parts.append(f"ELSE {self.placeholder()}")
            params.append(node._else)
        parts.append("END")
        return " ".join(parts), tuple(params)

    def visit_function(self, node: SQLFunction) -> Tuple[str, Tuple[ExprValue, ...]]:
        params: List[ExprValue] = []
        arg_parts: List[str] = []
        for arg in node.args:
            if isinstance(arg, str) and arg == "*":
                arg_parts.append("*")
            elif isinstance(arg, Field):
                arg_parts.append(self.compile_field(arg))
            elif isinstance(arg, SQLFunction):
                sub_sql, sub_params = self.visit_function(arg)
                arg_parts.append(sub_sql)
                params.extend(sub_params)
            else:
                arg_parts.append(self.placeholder())
                params.append(arg)

        func_sql = f"{node.name}({', '.join(arg_parts)})"
        if node._alias:
            func_sql = f"{func_sql} AS {self.quote_identifier(node._alias)}"
        return func_sql, tuple(params)

    # -- DQL --

    def visit_select(self, node: Select) -> Tuple[str, Tuple[ExprValue, ...]]:
        sql_parts: List[str] = []
        all_params: List[ExprValue] = []

        # CTEs
        if node._ctes:
            cte_parts: List[str] = []
            for cte in node._ctes:
                cte_sql, cte_params = self.visit_cte(cte)
                cte_parts.append(cte_sql)
                all_params.extend(cte_params)
            sql_parts.append("WITH " + ", ".join(cte_parts))

        # SELECT [DISTINCT]
        cols: List[str] = []
        for col in node._columns:
            if isinstance(col, str):
                if col == "*":
                    cols.append("*")
                else:
                    cols.append(self.quote_identifier(col))
            elif isinstance(col, Field):
                cols.append(self.compile_field(col))
            elif isinstance(col, Select):
                sub_sql, sub_params = self.process(col)
                cols.append(f"({sub_sql})")
                all_params.extend(sub_params)
            elif isinstance(col, SQLFunction):
                func_sql, func_params = self.visit_function(col)
                cols.append(func_sql)
                all_params.extend(func_params)
        distinct = "DISTINCT " if node._distinct else ""
        sql_parts.append(f"SELECT {distinct}{', '.join(cols)}")

        # FROM
        if node._from:
            from_sql, from_params = self.compile_from(node._from)
            sql_parts.append(f"FROM {from_sql}")
            all_params.extend(from_params)

        # JOINs
        if node._joins:
            join_sql, join_params = self.compile_joins(node._joins)
            sql_parts.append(join_sql)
            all_params.extend(join_params)

        # WHERE
        if node._where:
            where_sql, where_params = self.compile_condition(node._where)
            sql_parts.append(f"WHERE {where_sql}")
            all_params.extend(where_params)

        # GROUP BY
        if node._group_by:
            sql_parts.append(self.compile_group_by(node._group_by))

        # HAVING
        if node._having:
            having_sql, having_params = self.compile_condition(node._having)
            sql_parts.append(f"HAVING {having_sql}")
            all_params.extend(having_params)

        # ORDER BY
        if node._order_by:
            sql_parts.append(self.compile_order_by(node._order_by))

        # LIMIT
        if node._limit is not None:
            sql_parts.append(f"LIMIT {self.placeholder()}")
            all_params.append(node._limit)

        # OFFSET
        if node._offset is not None:
            sql_parts.append(f"OFFSET {self.placeholder()}")
            all_params.append(node._offset)

        return " ".join(sql_parts), tuple(all_params)

    def visit_compound_select(self, node: CompoundSelect) -> Tuple[str, Tuple[ExprValue, ...]]:
        left_sql, left_params = self.visit_select(node.left)
        right_sql, right_params = self.visit_select(node.right)
        return (
            f"({left_sql}) {node.operator} ({right_sql})",
            left_params + right_params,
        )

    def visit_cte(self, node: CTE) -> Tuple[str, Tuple[ExprValue, ...]]:
        sub_sql, sub_params = self.visit_select(node.select)
        return f"{self.quote_identifier(node.name)} AS ({sub_sql})", sub_params

    # -- DML --

    def visit_insert(self, node: Insert) -> Tuple[str, Tuple[ExprValue, ...]]:
        if node._table is None:
            raise ValueError("INSERT requires a table name")

        table = self.quote_identifier(node._table)

        if node._select is not None:
            sub_sql, sub_params = self.visit_select(node._select)
            return f"INSERT INTO {table} {sub_sql}", sub_params

        if node._data is None:
            raise ValueError("INSERT requires values() or select()")

        cols = ", ".join(self.quote_identifier(k) for k in node._data.keys())
        placeholders = ", ".join([self.placeholder()] * len(node._data))
        return (
            f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
            tuple(node._data.values()),
        )

    def visit_update(self, node: Update) -> Tuple[str, Tuple[ExprValue, ...]]:
        if node._table is None:
            raise ValueError("UPDATE requires a table name")
        if node._data is None:
            raise ValueError("UPDATE requires set() data")

        table = self.quote_identifier(node._table)
        set_parts: List[str] = []
        params: List[ExprValue] = []
        for col, val in node._data.items():
            set_parts.append(f"{self.quote_identifier(col)} = {self.placeholder()}")
            params.append(val)

        sql = f"UPDATE {table} SET {', '.join(set_parts)}"

        if node._where:
            where_sql, where_params = self.process(node._where)
            sql += f" WHERE {where_sql}"
            params.extend(where_params)

        return sql, tuple(params)

    def visit_delete(self, node: Delete) -> Tuple[str, Tuple[ExprValue, ...]]:
        if node._table is None:
            raise ValueError("DELETE requires a table name")

        table = self.quote_identifier(node._table)
        sql = f"DELETE FROM {table}"
        params: List[ExprValue] = []

        if node._where:
            where_sql, where_params = self.process(node._where)
            sql += f" WHERE {where_sql}"
            params.extend(where_params)

        return sql, tuple(params)

    def visit_upsert(self, node: Upsert) -> Tuple[str, Tuple[ExprValue, ...]]:
        raise NotImplementedError("UPSERT must be compiled by a dialect-specific compiler")

    # -- DDL --

    def visit_create_table(self, node: CreateTable) -> Tuple[str, Tuple[ExprValue, ...]]:
        if node._table is None:
            raise ValueError("CREATE TABLE requires a table name")

        table = self.quote_identifier(node._table)
        if_not_exists = "IF NOT EXISTS " if node._if_not_exists else ""

        col_defs: List[str] = []
        params: List[ExprValue] = []
        for col in node._columns:
            col_parts = [self.quote_identifier(col.name), col.type_]
            if not col.nullable:
                col_parts.append("NOT NULL")
            if col.default is not None:
                col_parts.append(f"DEFAULT {self.placeholder()}")
                params.append(col.default)
            if col.primary_key:
                col_parts.append("PRIMARY KEY")
            if col.unique:
                col_parts.append("UNIQUE")
            col_defs.append(" ".join(col_parts))

        return (
            f"CREATE TABLE {if_not_exists}{table} ({', '.join(col_defs)})",
            tuple(params),
        )

    def visit_alter_table(self, node: AlterTable) -> Tuple[str, Tuple[ExprValue, ...]]:
        if node._table is None:
            raise ValueError("ALTER TABLE requires a table name")

        table = self.quote_identifier(node._table)
        sql_parts: List[str] = []
        all_params: List[ExprValue] = []

        for action, col_name, col_type, col_def in node._actions:
            if action == AlterAction.ADD:
                sql_parts.append(f"ALTER TABLE {table} ADD COLUMN {self._compile_column_def(col_def)}")
                if col_def is not None and col_def.default is not None:
                    all_params.append(col_def.default)
            elif action == AlterAction.DROP:
                sql_parts.append(f"ALTER TABLE {table} DROP COLUMN {self.quote_identifier(col_name)}")
            elif action == AlterAction.MODIFY:
                sql_parts.append(f"ALTER TABLE {table} MODIFY COLUMN {self._compile_column_def(col_def)}")
                if col_def is not None and col_def.default is not None:
                    all_params.append(col_def.default)

        return "; ".join(sql_parts), tuple(all_params)

    def _compile_column_def(self, col_def: Optional[ColumnDef]) -> str:
        if col_def is None:  # pragma: no cover — defensive guard, never called with None
            return ""
        parts = [self.quote_identifier(col_def.name), col_def.type_]
        if not col_def.nullable:
            parts.append("NOT NULL")
        if col_def.default is not None:
            parts.append(f"DEFAULT {self.placeholder()}")
        if col_def.unique:
            parts.append("UNIQUE")
        return " ".join(parts)

    def visit_drop_table(self, node: DropTable) -> Tuple[str, Tuple[ExprValue, ...]]:
        if node._table is None:
            raise ValueError("DROP TABLE requires a table name")
        if_exists = "IF EXISTS " if node._if_exists else ""
        return f"DROP TABLE {if_exists}{self.quote_identifier(node._table)}", ()

    def visit_create_index(self, node: CreateIndex) -> Tuple[str, Tuple[ExprValue, ...]]:
        if node._name is None or node._table is None:
            raise ValueError("CREATE INDEX requires name and table")
        unique = "UNIQUE " if node._unique else ""
        if_not_exists = "IF NOT EXISTS " if node._if_not_exists else ""
        cols = ", ".join(self.quote_identifier(c) for c in node._columns)
        return (
            f"CREATE {unique}INDEX {if_not_exists}{self.quote_identifier(node._name)} "
            f"ON {self.quote_identifier(node._table)} ({cols})",
            (),
        )

    def visit_drop_index(self, node: DropIndex) -> Tuple[str, Tuple[ExprValue, ...]]:
        if node._name is None:
            raise ValueError("DROP INDEX requires an index name")
        if_exists = "IF EXISTS " if node._if_exists else ""
        sql = f"DROP INDEX {if_exists}{self.quote_identifier(node._name)}"
        if node._table:
            sql += f" ON {self.quote_identifier(node._table)}"
        return sql, ()

    def visit_create_view(self, node: CreateView) -> Tuple[str, Tuple[ExprValue, ...]]:
        if node._name is None or node._select is None:
            raise ValueError("CREATE VIEW requires name and AS SELECT")
        if_not_exists = "IF NOT EXISTS " if node._if_not_exists else ""
        sub_sql, sub_params = self.visit_select(node._select)
        return (
            f"CREATE VIEW {if_not_exists}{self.quote_identifier(node._name)} AS {sub_sql}",
            sub_params,
        )

    def visit_drop_view(self, node: DropView) -> Tuple[str, Tuple[ExprValue, ...]]:
        if node._name is None:
            raise ValueError("DROP VIEW requires a view name")
        if_exists = "IF EXISTS " if node._if_exists else ""
        return f"DROP VIEW {if_exists}{self.quote_identifier(node._name)}", ()

    def visit_truncate(self, node: Truncate) -> Tuple[str, Tuple[ExprValue, ...]]:
        if node._table is None:
            raise ValueError("TRUNCATE requires a table name")
        return f"TRUNCATE TABLE {self.quote_identifier(node._table)}", ()


class Dialect:
    """Holds compiler factory and syntax config for a database."""

    def __init__(self, placeholder: str, quote_char: str, compiler_cls: Type[Compiler]) -> None:
        self.placeholder = placeholder
        self.quote_char = quote_char
        self._compiler_cls = compiler_cls

    def get_compiler(self) -> Compiler:
        return self._compiler_cls()
