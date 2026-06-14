from sqlpiston.builder.nodes import Field
from sqlpiston.builder.selectable import Select
from sqlpiston.builder.dml import Insert, Upsert
from sqlpiston.compiler.sqlite import SQLiteCompiler, SQLiteDialect
from sqlpiston.compiler.base import Dialect


class TestSQLiteCompilerBasics:
    def test_placeholder(self) -> None:
        c = SQLiteCompiler()
        assert c.placeholder() == '?'

    def test_quote_identifier(self) -> None:
        c = SQLiteCompiler()
        assert c.quote_identifier("name") == '"name"'

    def test_simple_select(self) -> None:
        c = SQLiteCompiler()
        stmt = Select().select("id", "name").from_table("users")
        sql, params = c.visit_select(stmt)
        assert sql == 'SELECT "id", "name" FROM "users"'
        assert params == ()

    def test_select_with_where(self) -> None:
        c = SQLiteCompiler()
        stmt = Select().select("*").from_table("users").where(Field("age") >= 18)
        sql, params = c.visit_select(stmt)
        assert '"age" >= ?' in sql
        assert params == (18,)

    def test_insert_values(self) -> None:
        c = SQLiteCompiler()
        stmt = Insert().into("users").values({"name": "X", "age": 25})
        sql, params = c.visit_insert(stmt)
        assert 'INSERT INTO "users"' in sql
        assert '?', '?' in sql or ', ?' in sql
        assert params == ("X", 25)


class TestSQLiteCompilerUpsert:
    def test_upsert_on_conflict_do_update(self) -> None:
        c = SQLiteCompiler()
        stmt = (
            Upsert().into("users").values({"id": 1, "name": "X"})
            .on_conflict("id").do_update({"name": "X"})
        )
        sql, params = c.visit_upsert(stmt)
        assert "INSERT INTO" in sql
        assert "ON CONFLICT" in sql
        assert "DO UPDATE SET" in sql

    def test_upsert_on_conflict_do_nothing(self) -> None:
        c = SQLiteCompiler()
        stmt = (
            Upsert().into("users").values({"id": 1, "name": "X"})
            .on_conflict("id").do_nothing()
        )
        sql, params = c.visit_upsert(stmt)
        assert "ON CONFLICT" in sql
        assert "DO NOTHING" in sql


class TestSQLiteDialect:
    def test_get_compiler(self) -> None:
        d = SQLiteDialect()
        compiler = d.get_compiler()
        assert isinstance(compiler, SQLiteCompiler)

    def test_dialect_config(self) -> None:
        d = SQLiteDialect()
        assert d.placeholder == '?'
        assert d.quote_char == '"'
