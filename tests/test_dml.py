from sqlpiston.builder.dml import Delete, Insert, Update, Upsert
from sqlpiston.builder.nodes import Field
from sqlpiston.builder.selectable import Select


class TestInsert:
    def test_into(self) -> None:
        s = Insert().into("users")
        assert s._table == "users"

    def test_values(self) -> None:
        s = Insert().into("users").values({"name": "X", "age": 25})
        assert s._data == {"name": "X", "age": 25}

    def test_select(self) -> None:
        sub = Select().select("name", "age").from_table("temp")
        s = Insert().into("users").select(sub)
        assert s._select is sub
        assert s._data is None

    def test_values_then_select(self) -> None:
        sub = Select().select("name").from_table("temp")
        s = Insert().into("users").values({"name": "X"}).select(sub)
        assert s._select is sub
        assert s._data is None

    def test_select_then_values(self) -> None:
        sub = Select().select("name").from_table("temp")
        s = Insert().into("users").select(sub).values({"name": "X"})
        assert s._data == {"name": "X"}
        assert s._select is None

    def test_chaining_returns_self(self) -> None:
        s = Insert()
        assert s.into("x") is s
        assert s.values({}) is s


class TestUpdate:
    def test_table(self) -> None:
        s = Update().table("users")
        assert s._table == "users"

    def test_set(self) -> None:
        s = Update().table("users").set({"name": "Y"})
        assert s._data == {"name": "Y"}

    def test_where(self) -> None:
        cond = Field("id") == 1
        s = Update().table("users").set({"name": "Y"}).where(cond)
        assert s._where is cond


class TestDelete:
    def test_from_table(self) -> None:
        s = Delete().from_table("users")
        assert s._table == "users"

    def test_where(self) -> None:
        cond = Field("id") == 1
        s = Delete().from_table("users").where(cond)
        assert s._where is cond


class TestUpsert:
    def test_basic(self) -> None:
        s = Upsert().into("users").values({"id": 1, "name": "X"})
        assert s._table == "users"
        assert s._data == {"id": 1, "name": "X"}

    def test_on_conflict(self) -> None:
        s = Upsert().into("users").values({"id": 1}).on_conflict("id")
        assert s._conflict_columns == ("id",)

    def test_on_conflict_multiple(self) -> None:
        s = Upsert().into("users").values({"id": 1}).on_conflict("id", "email")
        assert s._conflict_columns == ("id", "email")

    def test_do_update(self) -> None:
        s = Upsert().into("users").values({"id": 1}).on_conflict("id").do_update({"name": "X"})
        assert s._update_data == {"name": "X"}
        assert s._do_nothing is False

    def test_do_nothing(self) -> None:
        s = Upsert().into("users").values({"id": 1}).on_conflict("id").do_nothing()
        assert s._do_nothing is True
