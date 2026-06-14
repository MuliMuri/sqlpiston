"""Coverage gaps: pool, session, mapper, nodes compile, etc."""
import pytest

from sqlpiston.builder.nodes import ASTNode, Field
from sqlpiston.builder.selectable import Select
from sqlpiston.builder.dml import Insert
from sqlpiston.builder.ddl import CreateTable
from sqlpiston.core.engine.sqlite import SQLiteEngine
from sqlpiston.core.pool import ConnectionPool
from sqlpiston.core.session import Session
from sqlpiston.orm.mapper import ResultSet
from sqlpiston.compiler.base import GenericCompiler


class TestConnectionPool:
    def test_create_pool(self) -> None:
        eng = SQLiteEngine()
        eng.init_engine(":memory:")
        pool = ConnectionPool(eng)
        assert pool is not None
        pool.close()
        eng.close()

    def test_acquire(self) -> None:
        eng = SQLiteEngine()
        eng.init_engine(":memory:")
        pool = ConnectionPool(eng, min_size=1)
        conn = pool.acquire()
        assert conn is not None
        pool.release(conn)
        pool.close()
        eng.close()

    def test_release(self) -> None:
        eng = SQLiteEngine()
        eng.init_engine(":memory:")
        pool = ConnectionPool(eng, min_size=1)
        conn = pool.acquire()
        pool.release(conn)
        # Should be able to acquire again
        conn2 = pool.acquire()
        pool.release(conn2)
        pool.close()
        eng.close()

    def test_context_manager(self) -> None:
        eng = SQLiteEngine()
        eng.init_engine(":memory:")
        with ConnectionPool(eng, min_size=1) as pool:
            conn = pool.acquire()
            pool.release(conn)
        eng.close()


class TestSession:
    def test_create_session(self) -> None:
        eng = SQLiteEngine()
        eng.init_engine(":memory:")
        session = Session(eng)
        assert session is not None
        session.close()
        eng.close()

    def test_context_manager(self) -> None:
        eng = SQLiteEngine()
        eng.init_engine(":memory:")
        with Session(eng) as session:
            assert session is not None
        eng.close()

    def test_begin_commit_rollback(self) -> None:
        eng = SQLiteEngine()
        eng.init_engine(":memory:")
        session = Session(eng)

        session._get_conn().execute(
            "CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)", ()
        )
        session.begin()
        session.execute(Insert().into("test").values({"id": 1, "val": "hello"}))
        session.commit()

        result = session.execute(Select().select("*").from_table("test"))
        assert len(result.all()) == 1

        session.begin()
        session.execute(Insert().into("test").values({"id": 2, "val": "world"}))
        session.rollback()

        result2 = session.execute(Select().select("*").from_table("test"))
        assert len(result2.all()) == 1  # rolled back

        session.close()
        eng.close()

    def test_close_without_conn(self) -> None:
        eng = SQLiteEngine()
        eng.init_engine(":memory:")
        session = Session(eng)
        session.close()  # should not raise
        eng.close()


class TestASTNodeCompile:
    def test_compile_with_dialect(self) -> None:
        from sqlpiston.compiler.mysql import MySQLDialect
        d = MySQLDialect()
        stmt = Select().select("id").from_table("users").where(Field("id") == 1)
        sql, params = stmt.compile(d)
        assert "SELECT" in sql
        assert "`id`" in sql
        assert params == (1,)

    def test_compile_no_dialect(self) -> None:
        stmt = Select().select("id").from_table("users").where(Field("id") == 1)
        sql, params = stmt.compile()
        assert "SELECT" in sql
        assert params == (1,)

    def test_compile_logical_node(self) -> None:
        node = (Field("a") == 1) & (Field("b") == 2)
        sql, params = node.compile()
        assert "AND" in sql
        assert params == (1, 2)


class TestMapperEdgeCases:
    def test_one_or_none_multiple_raises(self) -> None:
        from tests.test_mapper import MockCursor
        cursor = MockCursor([(1,), (2,)], ["id"])
        rs = ResultSet(cursor, ["id"])
        with pytest.raises(ValueError):
            rs.one_or_none()

    def test_iter(self) -> None:
        from tests.test_mapper import MockCursor
        cursor = MockCursor([(1, "A"), (2, "B")], ["id", "name"])
        rs = ResultSet(cursor, ["id", "name"])
        rows = list(rs)
        assert len(rows) == 2
        assert rows[0]["name"] == "A"


class TestCompilerEdgeCases:
    def test_select_with_zero_limit(self) -> None:
        c = GenericCompiler()
        stmt = Select().select("*").from_table("users").limit(0)
        sql, params = c.visit_select(stmt)
        assert "LIMIT %s" in sql
        assert params == (0,)

    def test_select_all_features(self) -> None:
        c = GenericCompiler()
        stmt = (
            Select()
            .select("id", "name")
            .distinct()
            .from_table("users")
            .join("orders", Field("user_id", "orders") == Field("id", "users"))
            .where(Field("age") >= 18)
            .group_by("status")
            .having(Field("cnt") > 5)
            .order_by("id", "DESC")
            .limit(10)
            .offset(20)
        )
        sql, params = c.visit_select(stmt)
        assert "SELECT DISTINCT" in sql
        assert "INNER JOIN" in sql
        assert "WHERE" in sql
        assert "GROUP BY" in sql
        assert "HAVING" in sql
        assert "ORDER BY" in sql
        assert "LIMIT" in sql
        assert "OFFSET" in sql

    def test_select_str_not_star(self) -> None:
        c = GenericCompiler()
        stmt = Select().select("id").from_table("users")
        sql, _ = c.visit_select(stmt)
        assert "`id`" in sql

    def test_select_with_field_column(self) -> None:
        c = GenericCompiler()
        stmt = Select().select(Field("id", "users")).from_table("users")
        sql, _ = c.visit_select(stmt)
        assert "`users`.`id`" in sql
