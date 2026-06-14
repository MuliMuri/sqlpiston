from sqlpiston.builder.ddl import (
    AlterAction, AlterTable, ColumnDef, CreateIndex, CreateTable,
    CreateView, DropIndex, DropTable, DropView, Truncate,
)


class TestColumnDef:
    def test_defaults(self) -> None:
        cd = ColumnDef(name="id", type_="INTEGER")
        assert cd.name == "id"
        assert cd.type_ == "INTEGER"
        assert cd.nullable is True
        assert cd.primary_key is False
        assert cd.default is None
        assert cd.unique is False

    def test_full(self) -> None:
        cd = ColumnDef(
            name="id", type_="INTEGER", nullable=False,
            primary_key=True, unique=True, default=None,
        )
        assert cd.primary_key is True
        assert cd.unique is True
        assert cd.nullable is False


class TestCreateTable:
    def test_table(self) -> None:
        ct = CreateTable().table("users")
        assert ct._table == "users"

    def test_if_not_exists(self) -> None:
        ct = CreateTable().table("users").if_not_exists()
        assert ct._if_not_exists is True

    def test_column(self) -> None:
        ct = CreateTable().table("users").column("id", "INTEGER")
        assert len(ct._columns) == 1
        assert ct._columns[0].name == "id"

    def test_columns_bulk(self) -> None:
        cols = [
            ColumnDef("id", "INTEGER", primary_key=True),
            ColumnDef("name", "VARCHAR(255)"),
        ]
        ct = CreateTable().table("users").columns(*cols)
        assert len(ct._columns) == 2


class TestAlterTable:
    def test_add_column(self) -> None:
        at = AlterTable().table("users").add_column("age", "INTEGER")
        assert len(at._actions) == 1
        assert at._actions[0][0] == AlterAction.ADD

    def test_drop_column(self) -> None:
        at = AlterTable().table("users").drop_column("age")
        assert len(at._actions) == 1
        assert at._actions[0][0] == AlterAction.DROP

    def test_modify_column(self) -> None:
        at = AlterTable().table("users").modify_column("name", "TEXT")
        assert len(at._actions) == 1
        assert at._actions[0][0] == AlterAction.MODIFY

    def test_multiple_actions(self) -> None:
        at = (
            AlterTable()
            .table("users")
            .add_column("age", "INTEGER")
            .drop_column("temp")
        )
        assert len(at._actions) == 2


class TestDropTable:
    def test_table(self) -> None:
        dt = DropTable().table("users")
        assert dt._table == "users"

    def test_if_exists(self) -> None:
        dt = DropTable().table("users").if_exists()
        assert dt._if_exists is True


class TestCreateIndex:
    def test_basic(self) -> None:
        ci = CreateIndex().name("idx_name").on("users").columns("name")
        assert ci._name == "idx_name"
        assert ci._table == "users"
        assert ci._columns == ("name",)

    def test_unique(self) -> None:
        ci = CreateIndex().name("idx").on("users").columns("email").unique()
        assert ci._unique is True

    def test_if_not_exists(self) -> None:
        ci = CreateIndex().name("idx").on("users").columns("email").if_not_exists()
        assert ci._if_not_exists is True


class TestDropIndex:
    def test_basic(self) -> None:
        di = DropIndex().name("idx_name").on("users")
        assert di._name == "idx_name"
        assert di._table == "users"

    def test_if_exists(self) -> None:
        di = DropIndex().name("idx").on("users").if_exists()
        assert di._if_exists is True


class TestCreateView:
    def test_basic(self) -> None:
        cv = CreateView().name("active_users")
        assert cv._name == "active_users"

    def test_if_not_exists(self) -> None:
        cv = CreateView().name("v").if_not_exists()
        assert cv._if_not_exists is True


class TestDropView:
    def test_basic(self) -> None:
        dv = DropView().name("v")
        assert dv._name == "v"

    def test_if_exists(self) -> None:
        dv = DropView().name("v").if_exists()
        assert dv._if_exists is True


class TestTruncate:
    def test_table(self) -> None:
        t = Truncate().table("users")
        assert t._table == "users"
