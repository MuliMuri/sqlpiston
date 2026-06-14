"""Coverage gap filler for compiler/base.py and dialect compilers."""
import pytest

from sqlpiston.builder.nodes import (
    ASTNode, CaseNode, ComparisonNode, ExistsNode, Field, LogicalNode,
    SQLFunction,
)
from sqlpiston.builder.selectable import CTE, CompoundSelect, Select
from sqlpiston.builder.dml import Insert, Update, Delete, Upsert
from sqlpiston.compiler.mysql import MySQLCompiler, MySQLDialect
from sqlpiston.compiler.sqlite import SQLiteCompiler, SQLiteDialect
from sqlpiston.compiler.base import Dialect, GenericCompiler


# -- Compiler dispatch (process method) --

class TestCompilerDispatch:
    def test_process_select(self) -> None:
        c = GenericCompiler()
        stmt = Select().select("*").from_table("users")
        sql, _ = c.process(stmt)
        assert "SELECT" in sql

    def test_process_compound_select(self) -> None:
        c = GenericCompiler()
        a = Select().select("a").from_table("t1")
        b = Select().select("b").from_table("t2")
        cs = a.union(b)
        sql, _ = c.process(cs)
        assert "UNION" in sql

    def test_process_cte(self) -> None:
        c = GenericCompiler()
        s = Select().select("*").from_table("sales").cte("s")
        sql, _ = c.process(s)
        assert "SELECT" in sql

    def test_process_insert(self) -> None:
        c = GenericCompiler()
        stmt = Insert().into("users").values({"name": "X"})
        sql, _ = c.process(stmt)
        assert "INSERT" in sql

    def test_process_update(self) -> None:
        c = GenericCompiler()
        stmt = Update().table("users").set({"name": "X"})
        sql, _ = c.process(stmt)
        assert "UPDATE" in sql

    def test_process_delete(self) -> None:
        c = GenericCompiler()
        stmt = Delete().from_table("users")
        sql, _ = c.process(stmt)
        assert "DELETE" in sql

    def test_unsupported_type_raises(self) -> None:
        c = GenericCompiler()

        class UnknownNode(ASTNode):
            pass

        with pytest.raises(TypeError):
            c.process(UnknownNode())


# -- GenericCompiler error paths --

class TestInsertErrors:
    def test_no_table_raises(self) -> None:
        c = GenericCompiler()
        with pytest.raises(ValueError):
            c.visit_insert(Insert())

    def test_no_data_raises(self) -> None:
        c = GenericCompiler()
        with pytest.raises(ValueError):
            c.visit_insert(Insert().into("t"))

    def test_insert_select(self) -> None:
        c = GenericCompiler()
        sub = Select().select("name").from_table("temp")
        stmt = Insert().into("users").select(sub)
        sql, _ = c.visit_insert(stmt)
        assert "INSERT INTO" in sql
        assert "SELECT" in sql

    def test_insert_select_with_columns(self) -> None:
        c = GenericCompiler()
        sub = Select().select("name").from_table("temp")
        stmt = Insert().into("users").values({"name": ""}).select(sub)
        sql, _ = c.visit_insert(stmt)
        assert "INSERT INTO `users`" in sql
        assert "SELECT" in sql


class TestUpdateErrors:
    def test_no_table_raises(self) -> None:
        c = GenericCompiler()
        with pytest.raises(ValueError):
            c.visit_update(Update())

    def test_no_data_raises(self) -> None:
        c = GenericCompiler()
        with pytest.raises(ValueError):
            c.visit_update(Update().table("t"))


class TestDeleteErrors:
    def test_no_table_raises(self) -> None:
        c = GenericCompiler()
        with pytest.raises(ValueError):
            c.visit_delete(Delete())


class TestUpsertErrors:
    def test_generic_compiler_raises(self) -> None:
        c = GenericCompiler()
        stmt = Upsert().into("users").values({"id": 1})
        with pytest.raises(NotImplementedError):
            c.visit_upsert(stmt)


# -- Compiler sub-methods --

class TestCompileField:
    def test_with_table(self) -> None:
        c = GenericCompiler()
        result = c.compile_field(Field("id", "users"))
        assert "`users`.`id`" == result

    def test_with_alias(self) -> None:
        c = GenericCompiler()
        result = c.compile_field(Field("name").alias("n"))
        assert "AS `n`" in result

    def test_simple(self) -> None:
        c = GenericCompiler()
        result = c.compile_field(Field("col"))
        assert "`col`" == result


class TestCompileFrom:
    def test_string_table(self) -> None:
        c = GenericCompiler()
        sql, params = c.compile_from("users")
        assert "`users`" == sql
        assert params == ()

    def test_subquery(self) -> None:
        c = GenericCompiler()
        sub = Select().select("id").from_table("users")
        sql, params = c.compile_from(sub)
        assert "(SELECT" in sql
        assert "AS `sub`" in sql

    def test_subquery_with_alias(self) -> None:
        c = GenericCompiler()
        sub = Select().select("id").from_table("users").as_("u")
        sql, params = c.compile_from(sub)
        assert "AS `u`" in sql


class TestCompileJoins:
    def test_inner_join(self) -> None:
        c = GenericCompiler()
        on = Field("user_id", "orders") == Field("id", "users")
        sql, params = c.compile_joins([("orders", "INNER", on)])
        assert "INNER JOIN `orders` ON" in sql
        assert params == ()

    def test_cross_join(self) -> None:
        c = GenericCompiler()
        sql, params = c.compile_joins([("categories", "CROSS", None)])  # type: ignore[arg-type]
        assert "CROSS JOIN" in sql
        assert params == ()

    def test_multiple_joins(self) -> None:
        c = GenericCompiler()
        j1 = ("orders", "LEFT", Field("user_id", "orders") == Field("id", "users"))
        j2 = ("products", "INNER", Field("product_id", "orders") == Field("id", "products"))
        sql, params = c.compile_joins([j1, j2])
        assert "LEFT JOIN" in sql
        assert "INNER JOIN" in sql


class TestCompileOrderBy:
    def test_string_field(self) -> None:
        c = GenericCompiler()
        result = c.compile_order_by([("id", "ASC")])
        assert "ORDER BY `id` ASC" == result

    def test_field_object(self) -> None:
        c = GenericCompiler()
        result = c.compile_order_by([(Field("name"), "DESC")])
        assert "`name` DESC" in result


class TestCompileGroupBy:
    def test_string(self) -> None:
        c = GenericCompiler()
        result = c.compile_group_by(["status"])
        assert "GROUP BY `status`" == result

    def test_field(self) -> None:
        c = GenericCompiler()
        result = c.compile_group_by([Field("status")])
        assert "GROUP BY `status`" == result


# -- MySQL upsert edge cases --

class TestMySQLUpsertEdgeCases:
    def test_no_table_raises(self) -> None:
        c = MySQLCompiler()
        with pytest.raises(ValueError):
            c.visit_upsert(Upsert().values({"id": 1}))

    def test_no_data_raises(self) -> None:
        c = MySQLCompiler()
        with pytest.raises(ValueError):
            c.visit_upsert(Upsert().into("users"))

    def test_do_nothing_with_conflict(self) -> None:
        c = MySQLCompiler()
        stmt = (
            Upsert().into("users").values({"id": 1, "name": "X"})
            .on_conflict("id").do_nothing()
        )
        sql, params = c.visit_upsert(stmt)
        assert "ON DUPLICATE KEY UPDATE" in sql

    def test_do_nothing_without_conflict_insert_ignore(self) -> None:
        c = MySQLCompiler()
        stmt = Upsert().into("users").values({"id": 1}).do_nothing()
        sql, params = c.visit_upsert(stmt)
        assert "INSERT IGNORE INTO" in sql


# -- SQLite upsert edge cases --

class TestSQLiteUpsertEdgeCases:
    def test_no_table_raises(self) -> None:
        c = SQLiteCompiler()
        with pytest.raises(ValueError):
            c.visit_upsert(Upsert().values({"id": 1}))

    def test_do_nothing_without_conflict(self) -> None:
        c = SQLiteCompiler()
        stmt = Upsert().into("users").values({"id": 1}).do_nothing()
        sql, params = c.visit_upsert(stmt)
        assert "ON CONFLICT DO NOTHING" in sql


# -- CompoundSelect / CTE compiler coverage --

class TestCompoundSelectCompiler:
    def test_union(self) -> None:
        c = GenericCompiler()
        a = Select().select("name").from_table("customers")
        b = Select().select("name").from_table("suppliers")
        cs = a.union(b)
        sql, params = c.visit_compound_select(cs)
        assert "UNION" in sql
        assert params == ()

    def test_union_all(self) -> None:
        c = GenericCompiler()
        cs = CompoundSelect("UNION ALL",
                            Select().select("a").from_table("t1"),
                            Select().select("b").from_table("t2"))
        sql, _ = c.visit_compound_select(cs)
        assert "UNION ALL" in sql


class TestCTECompiler:
    def test_cte(self) -> None:
        c = GenericCompiler()
        cte = CTE("s", Select().select("*").from_table("sales"))
        sql, params = c.visit_cte(cte)
        assert "`s` AS" in sql

    def test_select_with_cte(self) -> None:
        c = GenericCompiler()
        cte = CTE("big_sales", Select().select("*").from_table("sales").where(Field("amount") > 100))
        stmt = Select().with_(cte).select("*").from_table("big_sales")
        sql, params = c.visit_select(stmt)
        assert "WITH `big_sales`" in sql
        assert "SELECT" in sql

    def test_select_with_multiple_ctes(self) -> None:
        c = GenericCompiler()
        cte1 = CTE("a", Select().select("1").from_table("t"))
        cte2 = CTE("b", Select().select("2").from_table("t"))
        stmt = Select().with_(cte1, cte2).select("*").from_table("a")
        sql, params = c.visit_select(stmt)
        assert "WITH `a`" in sql
        assert "`b`" in sql


# -- Scalar subquery compiler coverage --

class TestScalarSubquery:
    def test_field_vs_subquery(self) -> None:
        c = GenericCompiler()
        sub = Select().select(SQLFunction("avg", "salary")).from_table("employees")
        node = Field("salary") > sub
        sql, params = c.visit_comparison(node)
        assert "SELECT" in sql
        assert ">" in sql

    def test_field_vs_function(self) -> None:
        c = GenericCompiler()
        node = ComparisonNode(Field("x"), "=", SQLFunction("max", Field("y")))
        sql, params = c.visit_comparison(node)
        assert "max" in sql


# -- Dialect class --

class TestDialectBase:
    def test_get_compiler(self) -> None:
        d = Dialect("%s", "`", GenericCompiler)
        c = d.get_compiler()
        assert isinstance(c, GenericCompiler)


# -- LogicalNode edge cases (NOT, multi-child) --

class TestLogicalNodeEdgeCases:
    def test_nested_and_or_mixed(self) -> None:
        c = GenericCompiler()
        a = Field("a") == 1
        b = Field("b") == 2
        c2 = Field("c") == 3
        node = (a & b) | c2
        sql, params = c.visit_logical(node)
        assert "AND" in sql
        assert "OR" in sql

    def test_complex_nested(self) -> None:
        c = GenericCompiler()
        node = (Field("a") == 1) & (Field("b") == 2)
        node = node | (Field("c") == 3)
        sql, params = c.visit_logical(node)
        assert "AND" in sql


# -- GenericCompiler upsert raises NotImplementedError --

class TestGenericUpsert:
    def test_raises_not_implemented(self) -> None:
        c = GenericCompiler()
        with pytest.raises(NotImplementedError):
            c.visit_upsert(Upsert().into("t").values({"x": 1}))
