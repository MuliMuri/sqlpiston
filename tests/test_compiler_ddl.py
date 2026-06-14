"""Tests for DDL compiler (GenericCompiler DDL methods)."""
import pytest

from sqlpiston.builder.ddl import (
    AlterTable, ColumnDef, CreateIndex, CreateTable, CreateView,
    DropIndex, DropTable, DropView, Truncate,
)
from sqlpiston.builder.selectable import Select
from sqlpiston.compiler.mysql import MySQLCompiler


class TestCreateTable:
    def test_create_table_basic(self) -> None:
        c = MySQLCompiler()
        stmt = (
            CreateTable().table("users")
            .column("id", "INTEGER", primary_key=True, nullable=False)
            .column("name", "VARCHAR(255)")
        )
        sql, params = c.visit_create_table(stmt)
        assert "CREATE TABLE `users`" in sql
        assert "`id` INTEGER NOT NULL PRIMARY KEY" in sql
        assert "`name` VARCHAR(255)" in sql
        assert params == ()

    def test_create_table_if_not_exists(self) -> None:
        c = MySQLCompiler()
        stmt = CreateTable().table("users").if_not_exists().column("id", "INTEGER")
        sql, params = c.visit_create_table(stmt)
        assert "IF NOT EXISTS" in sql

    def test_create_table_with_default(self) -> None:
        c = MySQLCompiler()
        stmt = CreateTable().table("users").column("status", "VARCHAR(10)", default="active")
        sql, params = c.visit_create_table(stmt)
        assert "DEFAULT %s" in sql
        assert params == ("active",)

    def test_create_table_unique(self) -> None:
        c = MySQLCompiler()
        stmt = CreateTable().table("users").column("email", "VARCHAR(255)", unique=True)
        sql, _ = c.visit_create_table(stmt)
        assert "UNIQUE" in sql

    def test_create_table_no_table_raises(self) -> None:
        c = MySQLCompiler()
        stmt = CreateTable().column("id", "INTEGER")
        with pytest.raises(ValueError):
            c.visit_create_table(stmt)

    def test_create_table_with_columns_bulk(self) -> None:
        c = MySQLCompiler()
        cols = [ColumnDef("a", "INT"), ColumnDef("b", "TEXT")]
        stmt = CreateTable().table("t").columns(*cols)
        sql, _ = c.visit_create_table(stmt)
        assert "`a` INT" in sql
        assert "`b` TEXT" in sql


class TestAlterTable:
    def test_add_column(self) -> None:
        c = MySQLCompiler()
        stmt = AlterTable().table("users").add_column("age", "INTEGER")
        sql, params = c.visit_alter_table(stmt)
        assert "ALTER TABLE `users` ADD COLUMN" in sql
        assert "`age` INTEGER" in sql
        assert params == ()

    def test_drop_column(self) -> None:
        c = MySQLCompiler()
        stmt = AlterTable().table("users").drop_column("temp")
        sql, params = c.visit_alter_table(stmt)
        assert "DROP COLUMN `temp`" in sql
        assert params == ()

    def test_modify_column(self) -> None:
        c = MySQLCompiler()
        stmt = AlterTable().table("users").modify_column("name", "TEXT")
        sql, params = c.visit_alter_table(stmt)
        assert "MODIFY COLUMN" in sql

    def test_no_table_raises(self) -> None:
        c = MySQLCompiler()
        stmt = AlterTable().add_column("x", "INT")
        with pytest.raises(ValueError):
            c.visit_alter_table(stmt)

    def test_multiple_actions(self) -> None:
        c = MySQLCompiler()
        stmt = (
            AlterTable().table("users")
            .add_column("age", "INTEGER", default=0)
            .drop_column("temp")
        )
        sql, params = c.visit_alter_table(stmt)
        assert ";" in sql
        assert params == (0,)


class TestDropTable:
    def test_drop_table(self) -> None:
        c = MySQLCompiler()
        stmt = DropTable().table("users")
        sql, params = c.visit_drop_table(stmt)
        assert "DROP TABLE `users`" == sql
        assert params == ()

    def test_drop_table_if_exists(self) -> None:
        c = MySQLCompiler()
        stmt = DropTable().table("users").if_exists()
        sql, _ = c.visit_drop_table(stmt)
        assert "IF EXISTS" in sql

    def test_no_table_raises(self) -> None:
        c = MySQLCompiler()
        with pytest.raises(ValueError):
            c.visit_drop_table(DropTable())


class TestCreateIndex:
    def test_create_index(self) -> None:
        c = MySQLCompiler()
        stmt = CreateIndex().name("idx_name").on("users").columns("name")
        sql, params = c.visit_create_index(stmt)
        assert "CREATE INDEX `idx_name`" in sql
        assert "ON `users`" in sql
        assert params == ()

    def test_unique_index(self) -> None:
        c = MySQLCompiler()
        stmt = CreateIndex().name("idx").on("users").columns("email").unique()
        sql, _ = c.visit_create_index(stmt)
        assert "CREATE UNIQUE INDEX" in sql

    def test_if_not_exists(self) -> None:
        c = MySQLCompiler()
        stmt = CreateIndex().name("idx").on("users").columns("x").if_not_exists()
        sql, _ = c.visit_create_index(stmt)
        assert "IF NOT EXISTS" in sql

    def test_no_name_raises(self) -> None:
        c = MySQLCompiler()
        with pytest.raises(ValueError):
            c.visit_create_index(CreateIndex().on("users").columns("x"))

    def test_no_table_raises(self) -> None:
        c = MySQLCompiler()
        with pytest.raises(ValueError):
            c.visit_create_index(CreateIndex().name("idx").columns("x"))


class TestDropIndex:
    def test_drop_index(self) -> None:
        c = MySQLCompiler()
        stmt = DropIndex().name("idx_name").on("users")
        sql, params = c.visit_drop_index(stmt)
        assert "DROP INDEX `idx_name`" in sql
        assert "ON `users`" in sql
        assert params == ()

    def test_drop_index_if_exists(self) -> None:
        c = MySQLCompiler()
        stmt = DropIndex().name("idx").on("users").if_exists()
        sql, _ = c.visit_drop_index(stmt)
        assert "IF EXISTS" in sql

    def test_no_name_raises(self) -> None:
        c = MySQLCompiler()
        with pytest.raises(ValueError):
            c.visit_drop_index(DropIndex())


class TestCreateView:
    def test_create_view(self) -> None:
        c = MySQLCompiler()
        sel = Select().select("id", "name").from_table("users")
        stmt = CreateView().name("active_users").as_(sel)
        sql, params = c.visit_create_view(stmt)
        assert "CREATE VIEW `active_users`" in sql
        assert "SELECT" in sql

    def test_if_not_exists(self) -> None:
        c = MySQLCompiler()
        sel = Select().select("*").from_table("users")
        stmt = CreateView().name("v").as_(sel).if_not_exists()
        sql, _ = c.visit_create_view(stmt)
        assert "IF NOT EXISTS" in sql

    def test_no_name_raises(self) -> None:
        c = MySQLCompiler()
        with pytest.raises(ValueError):
            c.visit_create_view(CreateView().as_(Select().select("*").from_table("t")))

    def test_no_select_raises(self) -> None:
        c = MySQLCompiler()
        with pytest.raises(ValueError):
            c.visit_create_view(CreateView().name("v"))


class TestDropView:
    def test_drop_view(self) -> None:
        c = MySQLCompiler()
        stmt = DropView().name("v")
        sql, params = c.visit_drop_view(stmt)
        assert "DROP VIEW `v`" == sql
        assert params == ()

    def test_if_exists(self) -> None:
        c = MySQLCompiler()
        stmt = DropView().name("v").if_exists()
        sql, _ = c.visit_drop_view(stmt)
        assert "IF EXISTS" in sql

    def test_no_name_raises(self) -> None:
        c = MySQLCompiler()
        with pytest.raises(ValueError):
            c.visit_drop_view(DropView())


class TestTruncate:
    def test_truncate(self) -> None:
        c = MySQLCompiler()
        stmt = Truncate().table("users")
        sql, params = c.visit_truncate(stmt)
        assert "TRUNCATE TABLE `users`" == sql
        assert params == ()

    def test_no_table_raises(self) -> None:
        c = MySQLCompiler()
        with pytest.raises(ValueError):
            c.visit_truncate(Truncate())
