"""Final coverage gap fillers: repr, edge cases, MySQL engine unit tests."""
import pytest

from sqlpiston.builder.nodes import Field, ComparisonNode, InNode, BetweenNode, LogicalNode
from sqlpiston.builder.nodes import ExistsNode, CaseNode, SQLFunction, ASTNode
from sqlpiston.builder.selectable import CTE, CompoundSelect, Select
from sqlpiston.builder.dml import Insert, Update, Delete, Upsert
from sqlpiston.builder.ddl import (
    AlterAction, AlterTable, ColumnDef, CreateIndex, CreateTable, CreateView,
    DropIndex, DropTable, DropView, Truncate,
)
from sqlpiston.core.engine.mysql import MySQLEngine, MySQLCursor, MySQLConnection
from sqlpiston.core.engine.sqlite import SQLiteEngine
from sqlpiston.core.pool import ConnectionPool
from sqlpiston.core.session import Session


# --- Repr methods ---

class TestReprMethods:
    def test_field_repr(self) -> None:
        assert "Field" in repr(Field("col"))
        assert "tbl" in repr(Field("col", "tbl"))

    def test_comparison_repr(self) -> None:
        node = Field("age") >= 18
        r = repr(node)
        assert "ComparisonNode" in r

    def test_in_repr(self) -> None:
        node = Field("id").is_in([1, 2])
        assert "InNode" in repr(node)

    def test_between_repr(self) -> None:
        node = Field("dt").between("a", "b")
        assert "BetweenNode" in repr(node)

    def test_logical_repr(self) -> None:
        node = (Field("a") == 1) & (Field("b") == 2)
        assert "LogicalNode" in repr(node)

    def test_exists_repr(self) -> None:
        node = ExistsNode(Select().select("*").from_table("t"), negated=True)
        assert "NOT EXISTS" in repr(node)

    def test_case_repr(self) -> None:
        c = CaseNode().when(Field("x") == 1, "y")
        assert "CaseNode" in repr(c)

    def test_sqlfunction_repr(self) -> None:
        f = SQLFunction("count", "*")
        assert "SQLFunction" in repr(f)

    def test_select_repr(self) -> None:
        s = Select().select("*").from_table("users")
        assert "Select" in repr(s)

    def test_compound_select_repr(self) -> None:
        a = Select().select("a").from_table("t1")
        b = Select().select("b").from_table("t2")
        cs = a.union(b)
        assert "CompoundSelect" in repr(cs)

    def test_cte_repr(self) -> None:
        c = CTE("x", Select().select("*").from_table("t"))
        assert "CTE" in repr(c)

    def test_insert_repr(self) -> None:
        assert "Insert" in repr(Insert().into("users"))

    def test_update_repr(self) -> None:
        assert "Update" in repr(Update().table("users"))

    def test_delete_repr(self) -> None:
        assert "Delete" in repr(Delete().from_table("users"))

    def test_upsert_repr(self) -> None:
        assert "Upsert" in repr(Upsert().into("users").on_conflict("id"))

    def test_create_table_repr(self) -> None:
        ct = CreateTable().table("users").column("id", "INTEGER")
        assert "CreateTable" in repr(ct)

    def test_alter_table_repr(self) -> None:
        at = AlterTable().table("users").add_column("x", "INT")
        assert "AlterTable" in repr(at)

    def test_drop_table_repr(self) -> None:
        assert "DropTable" in repr(DropTable().table("users"))

    def test_create_index_repr(self) -> None:
        ci = CreateIndex().name("idx").on("users").columns("x")
        assert "CreateIndex" in repr(ci)

    def test_drop_index_repr(self) -> None:
        assert "DropIndex" in repr(DropIndex().name("idx").on("users"))

    def test_create_view_repr(self) -> None:
        assert "CreateView" in repr(CreateView().name("v"))

    def test_drop_view_repr(self) -> None:
        assert "DropView" in repr(DropView().name("v"))

    def test_truncate_repr(self) -> None:
        assert "Truncate" in repr(Truncate().table("users"))


# --- Field __hash__ ---

class TestFieldHash:
    def test_hash(self) -> None:
        h1 = hash(Field("a"))
        h2 = hash(Field("a"))
        assert h1 == h2

    def test_hash_different(self) -> None:
        h1 = hash(Field("a"))
        h2 = hash(Field("b"))
        assert h1 != h2

    def test_hash_with_table(self) -> None:
        h1 = hash(Field("a", "t1"))
        h2 = hash(Field("a", "t2"))
        assert h1 != h2


# --- MySQL engine unit tests (no live DB needed) ---

class TestMySQLEngineUnit:
    def test_init_engine_stores_config(self) -> None:
        eng = MySQLEngine()
        eng.init_engine("localhost", 3306, "root", "", "test")
        assert eng._config is not None
        assert eng._config["host"] == "localhost"
        assert eng._config["port"] == 3306

    def test_close_without_conn(self) -> None:
        eng = MySQLEngine()
        eng.close()  # should not raise

    def test_connect_without_init_raises(self) -> None:
        eng = MySQLEngine()
        with pytest.raises(RuntimeError):
            eng.connect()


# --- Pool exhaust ---

class TestPoolExhaust:
    def test_exhaust_acquire_creates_new(self) -> None:
        eng = SQLiteEngine()
        eng.init_engine(":memory:")
        pool = ConnectionPool(eng, min_size=0, max_size=3)
        conn = pool.acquire()  # should create new
        assert conn is not None
        pool.release(conn)
        pool.close()
        eng.close()

    def test_exhaust_raises(self) -> None:
        eng = SQLiteEngine()
        eng.init_engine(":memory:")
        pool = ConnectionPool(eng, min_size=1, max_size=1)
        conn = pool.acquire()
        with pytest.raises(RuntimeError):
            pool.acquire()
        pool.release(conn)
        pool.close()
        eng.close()


# --- Mapper one_or_none multiple rows ---

class TestMapperOneOrNone:
    def test_one_or_none_multiple(self) -> None:
        from tests.test_mapper import MockCursor
        cursor = MockCursor([(1,), (2,)], ["id"])
        from sqlpiston.orm.mapper import ResultSet
        rs = ResultSet(cursor, ["id"])
        with pytest.raises(ValueError):
            rs.one_or_none()


# --- Select with subquery as column ---

class TestSelectSubqueryColumn:
    def test_scalar_subquery_in_select(self) -> None:
        from sqlpiston.compiler.mysql import MySQLCompiler
        c = MySQLCompiler()
        sub = Select().select(SQLFunction("count", "*")).from_table("orders").as_("cnt")
        stmt = Select().select("name", sub).from_table("users")
        sql, params = c.visit_select(stmt)
        assert "SELECT" in sql
        assert "count" in sql

    def test_function_in_select(self) -> None:
        from sqlpiston.compiler.mysql import MySQLCompiler
        c = MySQLCompiler()
        stmt = Select().select(SQLFunction("count", "*").alias("cnt")).from_table("users")
        sql, params = c.visit_select(stmt)
        assert "count(*)" in sql
        assert "AS `cnt`" in sql


# --- Default GenericCompiler on table alias ---

class TestCompileFromAlias:
    def test_from_with_alias_subquery(self) -> None:
        from sqlpiston.compiler.mysql import MySQLCompiler
        c = MySQLCompiler()
        sub = Select().select("id").from_table("users").as_("u")
        sql, params = c.compile_from(sub)
        assert "AS `u`" in sql


# --- LogicalNode NOT edge case ---

class TestLogicalNotEdge:
    def test_not_single_child_compile(self) -> None:
        from sqlpiston.compiler.mysql import MySQLCompiler
        c = MySQLCompiler()
        node = ~(Field("deleted") == 1)
        sql, params = c.visit_logical(node)
        assert "NOT" in sql


# --- MySQL do_nothing no conflict simple case ---

class TestMySQLUpsertNoConflict:
    def test_do_nothing_no_conflict(self) -> None:
        from sqlpiston.compiler.mysql import MySQLCompiler
        c = MySQLCompiler()
        stmt = Upsert().into("users").values({"id": 1, "name": "X"}).do_nothing()
        sql, params = c.visit_upsert(stmt)
        assert "INSERT IGNORE INTO" in sql
        assert params == (1, "X")

    def test_simple_upsert_no_update(self) -> None:
        from sqlpiston.compiler.mysql import MySQLCompiler
        c = MySQLCompiler()
        stmt = Upsert().into("users").values({"id": 1})
        sql, params = c.visit_upsert(stmt)
        assert "INSERT INTO" in sql

    def test_simple_upsert_no_conflict_sqlite(self) -> None:
        from sqlpiston.compiler.sqlite import SQLiteCompiler
        c = SQLiteCompiler()
        stmt = Upsert().into("users").values({"id": 1})
        sql, params = c.visit_upsert(stmt)
        assert "INSERT INTO" in sql
