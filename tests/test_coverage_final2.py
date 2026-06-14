"""Very final coverage gap fillers."""
import sqlite3
from sqlpiston.builder.nodes import SQLFunction, Field
from sqlpiston.builder.ddl import AlterTable
from sqlpiston.builder.selectable import Select
from sqlpiston.compiler.base import GenericCompiler
from sqlpiston.compiler.mysql import MySQLCompiler
from sqlpiston.core.engine.sqlite import SQLiteCursor


class TestCollectParams:
    def test_collect_params(self) -> None:
        c = GenericCompiler()
        result = c.collect_params(
            ("SELECT a", ("x",)),
            (" FROM `t`", ()),
            (" WHERE b = %s", ("y",)),
        )
        assert result == ("SELECT a  FROM `t`  WHERE b = %s", ("x", "y"))

    def test_collect_params_empty_sql(self) -> None:
        c = GenericCompiler()
        result = c.collect_params(
            ("", ()),
            ("SELECT 1", ()),
        )
        assert "SELECT 1" in result[0]
        assert result[1] == ()


class TestNestedSQLFunction:
    def test_nested_function(self) -> None:
        c = GenericCompiler()
        inner = SQLFunction("sum", Field("amount"))
        outer = SQLFunction("coalesce", inner, "0")
        sql, params = c.visit_function(outer)
        assert "coalesce" in sql
        assert "sum" in sql


class TestAlterTableFull:
    def test_modify_with_default(self) -> None:
        c = MySQLCompiler()
        stmt = AlterTable().table("users").modify_column("name", "TEXT", default="unknown")
        sql, params = c.visit_alter_table(stmt)
        assert "MODIFY COLUMN" in sql
        assert params == ("unknown",)

    def test_add_with_default(self) -> None:
        c = MySQLCompiler()
        stmt = AlterTable().table("users").add_column("age", "INTEGER", default=0)
        sql, params = c.visit_alter_table(stmt)
        assert "ADD COLUMN" in sql
        assert params == (0,)

    def test_compile_column_def_not_null_unique(self) -> None:
        from sqlpiston.builder.ddl import ColumnDef
        c = MySQLCompiler()
        cd = ColumnDef("id", "INTEGER", nullable=False, unique=True)
        result = c._compile_column_def(cd)
        assert "NOT NULL" in result
        assert "UNIQUE" in result

    def test_compile_column_def_with_default(self) -> None:
        from sqlpiston.builder.ddl import ColumnDef
        c = MySQLCompiler()
        cd = ColumnDef("status", "VARCHAR(10)", default="active")
        result = c._compile_column_def(cd)
        assert "DEFAULT %s" in result


class TestSQLiteNullDescription:
    def test_description_none(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE t (id INTEGER)")
        cur = conn.cursor()
        # Execute a statement that doesn't return rows, then try to get description
        cur.execute("SELECT * FROM t WHERE 1=0")
        wrapped = SQLiteCursor(cur)
        desc = wrapped.description
        # description is available even for empty result sets
        assert isinstance(desc, list)
        cur.close()
        conn.close()


class TestSelectColumnFallthrough:
    """Test the else branch in visit_select column handling (line 371)."""

    def test_fallthrough_str_representation(self) -> None:
        c = GenericCompiler()
        stmt = Select().select("id").from_table("users")
        sql, _ = c.visit_select(stmt)
        assert "`id`" in sql


class TestMapperOneOrNoneCoverage:
    def test_one_or_none_multiple_raises(self) -> None:
        from tests.test_mapper import MockCursor
        from sqlpiston.orm.mapper import ResultSet
        cursor = MockCursor([(1,), (2,), (3,)], ["id"])
        rs = ResultSet(cursor, ["id"])
        try:
            rs.one_or_none()
            assert False, "Should have raised"
        except ValueError:
            pass
