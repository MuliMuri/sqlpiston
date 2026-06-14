from typing import List, Tuple

from sqlpiston.builder.dml import Upsert
from sqlpiston.compiler.base import Dialect, GenericCompiler
from sqlpiston.builder.nodes import ExprValue
from sqlpiston._types import ColumnValue


class MySQLCompiler(GenericCompiler):
    """MySQL dialect compiler. %s placeholders, `backtick` quoting."""

    def placeholder(self) -> str:
        return '%s'

    def quote_identifier(self, name: str) -> str:
        return f'`{name}`'

    def visit_upsert(self, node: Upsert) -> Tuple[str, Tuple[ExprValue, ...]]:
        if node._table is None or node._data is None:
            raise ValueError("UPSERT requires table and values")

        table = self.quote_identifier(node._table)
        cols = ", ".join(self.quote_identifier(k) for k in node._data.keys())
        placeholders = ", ".join([self.placeholder()] * len(node._data))
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"

        if node._do_nothing and node._conflict_columns:
            conflict_cols = ", ".join(self.quote_identifier(c) for c in node._conflict_columns)
            sql += f" ON DUPLICATE KEY UPDATE {conflict_cols} = {conflict_cols}"
            return sql, tuple(node._data.values())

        if node._update_data:
            update_parts: List[str] = []
            params: List[ColumnValue] = list(node._data.values())
            for col in node._update_data:
                update_parts.append(f"{self.quote_identifier(col)} = VALUES({self.quote_identifier(col)})")
            sql += " ON DUPLICATE KEY UPDATE " + ", ".join(update_parts)
            return sql, tuple(params)

        if node._do_nothing:
            # INSERT IGNORE as fallback
            sql = sql.replace("INSERT INTO", "INSERT IGNORE INTO")
            return sql, tuple(node._data.values())

        return sql, tuple(node._data.values())


class MySQLDialect(Dialect):
    def __init__(self) -> None:
        super().__init__(placeholder='%s', quote_char='`', compiler_cls=MySQLCompiler)
