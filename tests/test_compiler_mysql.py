from sqlpiston.builder.nodes import Field, CaseNode, SQLFunction, ComparisonNode
from sqlpiston.builder.selectable import Select
from sqlpiston.builder.dml import Insert, Update, Delete, Upsert
from sqlpiston.builder.ddl import CreateTable, AlterTable, DropTable, ColumnDef
from sqlpiston.compiler.mysql import MySQLCompiler, MySQLDialect
from sqlpiston.compiler.base import Dialect


class TestMySQLCompilerSelect:
    def test_simple_select(self) -> None:
        c = MySQLCompiler()
        stmt = Select().select("id", "name").from_table("users")
        sql, params = c.visit_select(stmt)
        assert sql == "SELECT `id`, `name` FROM `users`"
        assert params == ()

    def test_select_with_where(self) -> None:
        c = MySQLCompiler()
        stmt = Select().select("*").from_table("users").where(Field("age") >= 18)
        sql, params = c.visit_select(stmt)
        assert "WHERE `age` >= %s" in sql
        assert params == (18,)

    def test_select_with_join(self) -> None:
        c = MySQLCompiler()
        stmt = (
            Select()
            .select("users.name", "orders.total")
            .from_table("users")
            .join("orders", Field("user_id", "orders") == Field("id", "users"))
        )
        sql, params = c.visit_select(stmt)
        assert "INNER JOIN `orders`" in sql
        assert "`orders`.`user_id` = `users`.`id`" in sql
        assert params == ()

    def test_select_with_limit_offset(self) -> None:
        c = MySQLCompiler()
        stmt = Select().select("*").from_table("users").limit(10).offset(5)
        sql, params = c.visit_select(stmt)
        assert "LIMIT %s" in sql
        assert "OFFSET %s" in sql
        assert params == (10, 5)

    def test_select_distinct(self) -> None:
        c = MySQLCompiler()
        stmt = Select().select("country").distinct().from_table("users")
        sql, _ = c.visit_select(stmt)
        assert "DISTINCT" in sql

    def test_select_order_by(self) -> None:
        c = MySQLCompiler()
        stmt = Select().select("*").from_table("users").order_by("id", "DESC")
        sql, _ = c.visit_select(stmt)
        assert "ORDER BY `id` DESC" in sql


class TestMySQLCompilerComparison:
    def test_literal(self) -> None:
        c = MySQLCompiler()
        node = Field("age") >= 18
        sql, params = c.visit_comparison(node)
        assert "`age` >= %s" in sql
        assert params == (18,)

    def test_field_vs_field(self) -> None:
        c = MySQLCompiler()
        node = Field("user_id", "orders") == Field("id", "users")
        sql, params = c.visit_comparison(node)
        assert "`orders`.`user_id` = `users`.`id`" == sql
        assert params == ()

    def test_is_null(self) -> None:
        c = MySQLCompiler()
        node = Field("deleted_at").is_null()
        sql, params = c.visit_comparison(node)
        assert "IS NULL" in sql
        assert params == ()

    def test_is_not_null(self) -> None:
        c = MySQLCompiler()
        node = Field("email").is_not_null()
        sql, _ = c.visit_comparison(node)
        assert "IS NOT NULL" in sql


class TestMySQLCompilerIn:
    def test_literal_list(self) -> None:
        c = MySQLCompiler()
        node = Field("id").is_in([1, 2, 3])
        sql, params = c.visit_in(node)
        assert "IN (%s, %s, %s)" in sql
        assert params == (1, 2, 3)

    def test_subquery(self) -> None:
        c = MySQLCompiler()
        sub = Select().select("id").from_table("admins")
        node = Field("id").is_in(sub)
        sql, params = c.visit_in(node)
        assert "IN (SELECT" in sql
        assert params == ()


class TestMySQLCompilerBetween:
    def test_between(self) -> None:
        c = MySQLCompiler()
        node = Field("dt").between("2020-01-01", "2024-01-01")
        sql, params = c.visit_between(node)
        assert "BETWEEN %s AND %s" in sql
        assert params == ("2020-01-01", "2024-01-01")


class TestMySQLCompilerLogical:
    def test_and(self) -> None:
        c = MySQLCompiler()
        node = (Field("a") == 1) & (Field("b") == 2)
        sql, params = c.visit_logical(node)
        assert "AND" in sql
        assert params == (1, 2)


class TestMySQLCompilerFunction:
    def test_count_star(self) -> None:
        c = MySQLCompiler()
        node = SQLFunction("count", "*")
        sql, params = c.visit_function(node)
        assert sql == "count(*)"
        assert params == ()

    def test_sum(self) -> None:
        c = MySQLCompiler()
        node = SQLFunction("sum", Field("amount"))
        sql, params = c.visit_function(node)
        assert sql == "sum(`amount`)"
        assert params == ()

    def test_coalesce(self) -> None:
        c = MySQLCompiler()
        node = SQLFunction("coalesce", Field("name"), "N/A")
        sql, params = c.visit_function(node)
        assert "coalesce" in sql
        assert "%s" in sql
        assert params == ("N/A",)


class TestMySQLCompilerCase:
    def test_case_when(self) -> None:
        c = MySQLCompiler()
        node = CaseNode().when(Field("score") >= 90, "A").else_("D")
        sql, params = c.visit_case(node)
        assert "CASE" in sql
        assert "WHEN" in sql
        assert "ELSE" in sql
        assert "END" in sql


class TestMySQLCompilerExists:
    def test_exists(self) -> None:
        c = MySQLCompiler()
        sub = Select().select("1").from_table("orders")
        from sqlpiston.builder.nodes import ExistsNode
        node = ExistsNode(sub)
        sql, params = c.visit_exists(node)
        assert "EXISTS" in sql
        assert params == ()


class TestMySQLCompilerDML:
    def test_insert_values(self) -> None:
        c = MySQLCompiler()
        stmt = Insert().into("users").values({"name": "X", "age": 25})
        sql, params = c.visit_insert(stmt)
        assert "INSERT INTO `users`" in sql
        assert params == ("X", 25)

    def test_update(self) -> None:
        c = MySQLCompiler()
        stmt = Update().table("users").set({"name": "Y"}).where(Field("id") == 1)
        sql, params = c.visit_update(stmt)
        assert "UPDATE `users`" in sql
        assert "SET `name` = %s" in sql
        assert "WHERE" in sql

    def test_delete(self) -> None:
        c = MySQLCompiler()
        stmt = Delete().from_table("users").where(Field("id") == 1)
        sql, params = c.visit_delete(stmt)
        assert "DELETE FROM `users`" in sql

    def test_upsert_on_duplicate_key(self) -> None:
        c = MySQLCompiler()
        stmt = (
            Upsert().into("users").values({"id": 1, "name": "X"})
            .on_conflict("id").do_update({"name": "X"})
        )
        sql, params = c.visit_upsert(stmt)
        assert "INSERT INTO" in sql
        assert "ON DUPLICATE KEY UPDATE" in sql
        assert "VALUES(`name`)" in sql


class TestMySQLCompilerDDL:
    def test_create_table(self) -> None:
        c = MySQLCompiler()
        stmt = (
            CreateTable().table("users").if_not_exists()
            .column("id", "INTEGER", primary_key=True, nullable=False)
            .column("name", "VARCHAR(255)")
        )
        sql, params = c.visit_create_table(stmt)
        assert "CREATE TABLE IF NOT EXISTS" in sql
        assert "PRIMARY KEY" in sql

    def test_drop_table(self) -> None:
        c = MySQLCompiler()
        stmt = DropTable().table("users").if_exists()
        sql, params = c.visit_drop_table(stmt)
        assert "DROP TABLE IF EXISTS" in sql


class TestMySQLDialect:
    def test_get_compiler(self) -> None:
        d = MySQLDialect()
        compiler = d.get_compiler()
        assert isinstance(compiler, MySQLCompiler)

    def test_dialect_config(self) -> None:
        d = MySQLDialect()
        assert d.placeholder == '%s'
        assert d.quote_char == '`'
