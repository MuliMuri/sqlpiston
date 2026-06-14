"""Cover process() dispatch branches, sqlite rowcount, field alias repr."""
import sqlite3

from sqlpiston.builder.nodes import Field, BetweenNode, CaseNode, SQLFunction
from sqlpiston.builder.selectable import Select
from sqlpiston.builder.dml import Upsert
from sqlpiston.builder.ddl import (
    AlterTable, CreateIndex, CreateTable, DropIndex, DropTable,
    DropView, Truncate,
)
from sqlpiston.compiler.base import GenericCompiler
from sqlpiston.core.engine.sqlite import SQLiteCursor, SQLiteEngine
from sqlpiston.core.session import Session


class TestProcessDispatch:
    """Test process() dispatch for all node types."""

    def test_process_upsert(self) -> None:
        c = GenericCompiler()
        stmt = Upsert().into("users").values({"id": 1})
        try:
            c.process(stmt)
        except NotImplementedError:
            pass

    def test_process_create_table(self) -> None:
        c = GenericCompiler()
        stmt = CreateTable().table("users").column("id", "INTEGER")
        sql, _ = c.process(stmt)
        assert "CREATE TABLE" in sql

    def test_process_alter_table(self) -> None:
        c = GenericCompiler()
        stmt = AlterTable().table("users").add_column("x", "INT")
        sql, _ = c.process(stmt)
        assert "ALTER TABLE" in sql

    def test_process_drop_table(self) -> None:
        c = GenericCompiler()
        stmt = DropTable().table("users")
        sql, _ = c.process(stmt)
        assert "DROP TABLE" in sql

    def test_process_create_index(self) -> None:
        c = GenericCompiler()
        stmt = CreateIndex().name("idx").on("users").columns("name")
        sql, _ = c.process(stmt)
        assert "CREATE INDEX" in sql

    def test_process_drop_index(self) -> None:
        c = GenericCompiler()
        stmt = DropIndex().name("idx").on("users")
        sql, _ = c.process(stmt)
        assert "DROP INDEX" in sql

    def test_process_between(self) -> None:
        c = GenericCompiler()
        node = Field("dt").between("2020", "2024")
        sql, _ = c.process(node)
        assert "BETWEEN" in sql

    def test_process_case(self) -> None:
        c = GenericCompiler()
        node = CaseNode().when(Field("x") == 1, "yes").else_("no")
        sql, _ = c.process(node)
        assert "CASE" in sql

    def test_process_drop_view(self) -> None:
        c = GenericCompiler()
        stmt = DropView().name("v")
        sql, _ = c.process(stmt)
        assert "DROP VIEW" in sql

    def test_process_truncate(self) -> None:
        c = GenericCompiler()
        stmt = Truncate().table("users")
        sql, _ = c.process(stmt)
        assert "TRUNCATE" in sql


class TestFieldReprAlias:
    def test_repr_with_alias(self) -> None:
        f = Field("name").alias("n")
        assert "AS n" in repr(f)


class TestProcessDispatchMore:
    def test_process_create_view(self) -> None:
        from sqlpiston.builder.ddl import CreateView
        c = GenericCompiler()
        stmt = CreateView().name("v").as_(Select().select("*").from_table("users"))
        sql, _ = c.process(stmt)
        assert "CREATE VIEW" in sql

    def test_process_in(self) -> None:
        c = GenericCompiler()
        node = Field("id").is_in([1, 2])
        sql, _ = c.process(node)
        assert "IN" in sql

    def test_process_function(self) -> None:
        c = GenericCompiler()
        node = SQLFunction("count", "*")
        sql, _ = c.process(node)
        assert "count" in sql


class TestSQLiteRowcount:
    def test_rowcount(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE t (id INTEGER)")
        conn.execute("INSERT INTO t VALUES (1)")
        cur = conn.cursor()
        cur.execute("DELETE FROM t")
        wrapped = SQLiteCursor(cur)
        assert wrapped.rowcount == 1
        cur.close()
        conn.close()
