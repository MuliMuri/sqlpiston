from sqlpiston.builder.nodes import Field, ExistsNode
from sqlpiston.builder.selectable import CTE, CompoundSelect, Select


class TestSelect:
    def test_empty_select(self) -> None:
        s = Select()
        assert s._columns == []
        assert s._from is None

    def test_select_columns(self) -> None:
        s = Select().select("id", "name")
        assert s._columns == ["id", "name"]

    def test_select_with_field(self) -> None:
        s = Select().select(Field("age"))
        assert len(s._columns) == 1

    def test_from_table(self) -> None:
        s = Select().from_table("users")
        assert s._from == "users"

    def test_from_subquery(self) -> None:
        sub = Select().select("id").from_table("users").as_("u")
        s = Select().from_table(sub)
        assert s._from is sub

    def test_where(self) -> None:
        cond = Field("age") >= 18
        s = Select().where(cond)
        assert s._where is cond

    def test_join_default(self) -> None:
        s = Select().from_table("users").join("orders", Field("user_id", "orders") == Field("id", "users"))
        assert len(s._joins) == 1
        assert s._joins[0] == ("orders", "INNER", s._joins[0][2])

    def test_left_join(self) -> None:
        s = Select().from_table("users").left_join("orders", Field("user_id", "orders") == Field("id", "users"))
        assert s._joins[0][1] == "LEFT"

    def test_right_join(self) -> None:
        s = Select().from_table("users").right_join("orders", Field("user_id", "orders") == Field("id", "users"))
        assert s._joins[0][1] == "RIGHT"

    def test_cross_join(self) -> None:
        s = Select().from_table("users").cross_join("categories")
        assert s._joins[0][1] == "CROSS"

    def test_group_by(self) -> None:
        s = Select().group_by("status")
        assert s._group_by == ["status"]

    def test_having(self) -> None:
        cond = Field("cnt") > 5
        s = Select().having(cond)
        assert s._having is cond

    def test_order_by(self) -> None:
        s = Select().order_by("id", "ASC")
        assert s._order_by == [("id", "ASC")]

    def test_order_by_default_asc(self) -> None:
        s = Select().order_by("id")
        assert s._order_by == [("id", "ASC")]

    def test_order_by_multiple(self) -> None:
        s = Select().order_by("id").order_by("name", "DESC")
        assert len(s._order_by) == 2
        assert s._order_by[1] == ("name", "DESC")

    def test_limit(self) -> None:
        s = Select().limit(10)
        assert s._limit == 10

    def test_offset(self) -> None:
        s = Select().offset(5)
        assert s._offset == 5

    def test_distinct(self) -> None:
        s = Select().distinct()
        assert s._distinct is True

    def test_distinct_idempotent(self) -> None:
        s = Select().distinct().distinct()
        assert s._distinct is True

    def test_as_sets_alias(self) -> None:
        s = Select().select("*").from_table("users").as_("u")
        assert s._alias == "u"

    def test_exists(self) -> None:
        s = Select().select("1").from_table("orders")
        node = s.exists()
        assert isinstance(node, ExistsNode)
        assert node.negated is False

    def test_not_exists(self) -> None:
        s = Select().select("1").from_table("orders")
        node = s.not_exists()
        assert isinstance(node, ExistsNode)
        assert node.negated is True

    def test_union(self) -> None:
        a = Select().select("name").from_table("customers")
        b = Select().select("name").from_table("suppliers")
        cs = a.union(b)
        assert isinstance(cs, CompoundSelect)
        assert cs.operator == "UNION"
        assert cs.left is a
        assert cs.right is b

    def test_union_all(self) -> None:
        a = Select().select("name").from_table("customers")
        b = Select().select("name").from_table("suppliers")
        cs = a.union_all(b)
        assert cs.operator == "UNION ALL"

    def test_intersect(self) -> None:
        a = Select().select("name").from_table("t1")
        b = Select().select("name").from_table("t2")
        cs = a.intersect(b)
        assert cs.operator == "INTERSECT"

    def test_except(self) -> None:
        a = Select().select("name").from_table("t1")
        b = Select().select("name").from_table("t2")
        cs = a.except_(b)
        assert cs.operator == "EXCEPT"

    def test_cte(self) -> None:
        s = Select().select("*").from_table("sales")
        c = s.cte("big_sales")
        assert isinstance(c, CTE)
        assert c.name == "big_sales"
        assert c.select is s

    def test_with_cte(self) -> None:
        c = Select().select("*").from_table("sales").cte("big_sales")
        s = Select().with_(c).select("*").from_table("big_sales")
        assert s._ctes is not None
        assert len(s._ctes) == 1

    def test_chaining_returns_self(self) -> None:
        s = Select()
        assert s.select("a") is s
        assert s.distinct() is s
        assert s.where(Field("x") == 1) is s

    def test_fluent_chain_state(self) -> None:
        s = (
            Select()
            .select("id", "name")
            .from_table("users")
            .where(Field("age") >= 18)
            .order_by("id")
            .limit(5)
            .offset(10)
        )
        assert s._columns == ["id", "name"]
        assert s._from == "users"
        assert s._where is not None
        assert s._limit == 5
        assert s._offset == 10


class TestCompoundSelect:
    def test_creation(self) -> None:
        left = Select().select("a").from_table("t1")
        right = Select().select("b").from_table("t2")
        cs = CompoundSelect("UNION", left, right)
        assert cs.operator == "UNION"
        assert cs.left is left
        assert cs.right is right


class TestCTE:
    def test_creation(self) -> None:
        s = Select().select("*").from_table("employees")
        cte = CTE("emp_cte", s)
        assert cte.name == "emp_cte"
        assert cte.select is s
