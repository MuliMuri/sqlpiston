from typing import List, Tuple

from sqlpiston.builder.dml import Upsert
from sqlpiston.compiler.base import Dialect, GenericCompiler
from sqlpiston.builder.nodes import ExprValue
from sqlpiston._types import ColumnValue


class SQLiteCompiler(GenericCompiler):
    """SQLite dialect compiler. ? placeholders, "double-quote" quoting."""

    def placeholder(self) -> str:
        return '?'

    def quote_identifier(self, name: str) -> str:
        return f'"{name}"'

    def visit_upsert(self, node: Upsert) -> Tuple[str, Tuple[ExprValue, ...]]:
        if node._table is None or node._data is None:
            raise ValueError("UPSERT requires table and values")

        table = self.quote_identifier(node._table)
        cols = ", ".join(self.quote_identifier(k) for k in node._data.keys())
        placeholders = ", ".join([self.placeholder()] * len(node._data))
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"

        if node._do_nothing and node._conflict_columns:
            conflict_cols = ", ".join(self.quote_identifier(c) for c in node._conflict_columns)
            sql += f" ON CONFLICT ({conflict_cols}) DO NOTHING"
            return sql, tuple(node._data.values())

        if node._update_data and node._conflict_columns:
            conflict_cols = ", ".join(self.quote_identifier(c) for c in node._conflict_columns)
            update_parts: List[str] = []
            update_params: List[ColumnValue] = []
            for col, val in node._update_data.items():
                update_parts.append(f"{self.quote_identifier(col)} = {self.placeholder()}")
                update_params.append(val)
            sql += f" ON CONFLICT ({conflict_cols}) DO UPDATE SET {', '.join(update_parts)}"
            return sql, tuple(list(node._data.values()) + update_params)

        if node._do_nothing:
            sql += " ON CONFLICT DO NOTHING"
            return sql, tuple(node._data.values())

        return sql, tuple(node._data.values())


class SQLiteDialect(Dialect):
    def __init__(self) -> None:
        super().__init__(placeholder='?', quote_char='"', compiler_cls=SQLiteCompiler)
