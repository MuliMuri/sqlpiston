from dataclasses import dataclass

from sqlpiston.builder.nodes import Field, SQLFunction
from sqlpiston.builder.selectable import Select
from sqlpiston.builder.dml import Insert, Update, Delete
from sqlpiston.compiler.mysql import MySQLCompiler
from sqlpiston.compiler.sqlite import SQLiteCompiler
from sqlpiston.core.engine.base import DBEngine
from sqlpiston.core.engine import DBType
from sqlpiston.core.engine.sqlite import SQLiteEngine
from sqlpiston.core.session import Session


@dataclass
class Person:
    id: int
    name: str
    age: int


class TestASTToSQLIntegration:
    """Full AST → compile → params pipeline tests."""

    def test_simple_select_mysql(self) -> None:
        c = MySQLCompiler()
        stmt = (
            Select()
            .select("id", "name")
            .from_table("users")
            .where(Field("age") >= 18)
            .order_by("id")
            .limit(5)
        )
        sql, params = c.visit_select(stmt)
        assert sql.startswith("SELECT")
        assert "FROM `users`" in sql
        assert "`age` >= %s" in sql
        assert params == (18, 5)

    def test_simple_select_sqlite(self) -> None:
        c = SQLiteCompiler()
        stmt = Select().select("*").from_table("users")
        sql, params = c.visit_select(stmt)
        assert '"users"' in sql
        assert params == ()

    def test_ast_compiles_via_node(self) -> None:
        """ASTNode.compile() delegates to compiler."""
        stmt = (
            Select()
            .select("id")
            .from_table("users")
            .where(Field("id") == 1)
        )
        # Default (no dialect → GenericCompiler)
        sql, params = stmt.compile()
        assert "SELECT" in sql
        assert params == (1,)

    def test_compound_select(self) -> None:
        c = MySQLCompiler()
        a = Select().select("name").from_table("customers")
        b = Select().select("name").from_table("suppliers")
        cs = a.union_all(b)
        sql, params = c.visit_compound_select(cs)
        assert "UNION ALL" in sql

    def test_exists_subquery(self) -> None:
        c = MySQLCompiler()
        sub = (
            Select().select("1").from_table("orders")
            .where(Field("user_id", "orders") == Field("id", "users"))
        )
        stmt = Select().select("name").from_table("users").where(sub.exists())
        sql, params = c.visit_select(stmt)
        assert "EXISTS" in sql

    def test_insert_and_select_integration(self) -> None:
        c = MySQLCompiler()
        stmt = (
            Insert().into("users")
            .values({"name": "X", "age": 25})
        )
        sql, params = c.visit_insert(stmt)
        assert "INSERT INTO `users`" in sql
        assert params == ("X", 25)


class TestSessionIntegration:
    """Session: AST → compile → execute on SQLite :memory:"""

    def test_full_session_flow(self) -> None:
        eng = SQLiteEngine()
        eng.init_engine(":memory:")
        session = Session(eng)

        # Create table
        from sqlpiston.builder.ddl import CreateTable
        session._get_conn().execute(
            "CREATE TABLE people (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)", ()
        )

        # Insert
        session.execute(
            Insert().into("people").values({"id": 1, "name": "Alice", "age": 30})
        )
        session.execute(
            Insert().into("people").values({"id": 2, "name": "Bob", "age": 25})
        )

        # Select
        result = session.execute(
            Select().select("*").from_table("people").where(Field("age") >= 18)
        )
        rows = result.all()
        assert len(rows) == 2
        assert rows[0]["name"] in ("Alice", "Bob")

        # Update
        session.execute(
            Update().table("people").set({"age": 31}).where(Field("id") == 1)
        )
        updated = session.execute(
            Select().select("age").from_table("people").where(Field("id") == 1)
        )
        assert updated.scalar() == 31

        # Delete
        session.execute(Delete().from_table("people").where(Field("id") == 2))
        remaining = session.execute(
            Select().select("id").from_table("people")
        )
        assert len(remaining.all()) == 1

        session.commit()
        session.close()
        eng.close()

    def test_session_map(self) -> None:
        eng = SQLiteEngine()
        eng.init_engine(":memory:")
        session = Session(eng)

        session._get_conn().execute(
            "CREATE TABLE people (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)", ()
        )
        session.execute(Insert().into("people").values({"id": 1, "name": "Alice", "age": 30}))

        result = session.execute(Select().select("*").from_table("people"))
        people = result.map(Person)
        assert len(people) == 1
        assert isinstance(people[0], Person)
        assert people[0].name == "Alice"

        session.close()
        eng.close()
