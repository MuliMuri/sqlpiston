import pytest

from sqlpiston.builder.nodes import (
    ASTNode, BetweenNode, CaseNode, ComparisonNode, ExistsNode, Field,
    InNode, LogicalNode, SQLFunction,
)
from sqlpiston.builder.selectable import Select


class TestField:
    def test_init_simple(self) -> None:
        f = Field("name")
        assert f.name == "name"
        assert f.table is None

    def test_init_with_table(self) -> None:
        f = Field("id", "users")
        assert f.name == "id"
        assert f.table == "users"

    def test_eq_returns_comparison_node(self) -> None:
        node = Field("age") == 18
        assert isinstance(node, ComparisonNode)
        assert node.field.name == "age"
        assert node.operator == "="
        assert node.value == 18

    def test_ne_returns_comparison_node(self) -> None:
        node = Field("status") != "inactive"
        assert isinstance(node, ComparisonNode)
        assert node.operator == "!="
        assert node.value == "inactive"

    def test_lt_returns_comparison_node(self) -> None:
        node = Field("score") < 60
        assert node.operator == "<"

    def test_le_returns_comparison_node(self) -> None:
        node = Field("score") <= 60
        assert node.operator == "<="

    def test_gt_returns_comparison_node(self) -> None:
        node = Field("score") > 90
        assert node.operator == ">"

    def test_ge_returns_comparison_node(self) -> None:
        node = Field("score") >= 90
        assert node.operator == ">="

    def test_is_in_with_literals(self) -> None:
        node = Field("id").is_in([1, 2, 3])
        assert isinstance(node, InNode)
        assert node.field.name == "id"
        assert node.values == [1, 2, 3]

    def test_is_in_with_select(self) -> None:
        sub = Select().select("id").from_table("admins")
        node = Field("id").is_in(sub)
        assert isinstance(node, InNode)
        assert node.values is sub

    def test_between(self) -> None:
        node = Field("datetime").between("2020-01-01", "2024-01-01")
        assert isinstance(node, BetweenNode)
        assert node.low == "2020-01-01"
        assert node.high == "2024-01-01"

    def test_is_null(self) -> None:
        node = Field("deleted_at").is_null()
        assert node.operator == "IS NULL"
        assert node.value is None

    def test_is_not_null(self) -> None:
        node = Field("email").is_not_null()
        assert node.operator == "IS NOT NULL"
        assert node.value is None

    def test_alias(self) -> None:
        f = Field("name").alias("user_name")
        assert f.name == "name"
        assert f._alias_prop == "user_name"

    def test_alias_does_not_mutate_original(self) -> None:
        f = Field("name")
        aliased = f.alias("n")
        assert f._alias_prop is None
        assert aliased._alias_prop == "n"

    def test_repr(self) -> None:
        f = Field("col", "tbl")
        assert "col" in repr(f)
        assert "tbl" in repr(f)


class TestFieldComparisonWithField:
    def test_field_eq_field(self) -> None:
        node = Field("user_id", "orders") == Field("id", "users")
        assert node.operator == "="
        assert isinstance(node.value, Field)

    def test_field_gt_field(self) -> None:
        node = Field("a") > Field("b")
        assert node.operator == ">"


class TestASTNode:
    def test_and_returns_logical_node(self) -> None:
        a = Field("x") == 1
        b = Field("y") == 2
        node = a & b
        assert isinstance(node, LogicalNode)
        assert node.operator == "AND"
        assert len(node.children) == 2

    def test_or_returns_logical_node(self) -> None:
        a = Field("x") == 1
        b = Field("y") == 2
        node = a | b
        assert isinstance(node, LogicalNode)
        assert node.operator == "OR"
        assert len(node.children) == 2

    def test_invert_returns_logical_node(self) -> None:
        a = Field("x") == 1
        node = ~a
        assert isinstance(node, LogicalNode)
        assert node.operator == "NOT"
        assert len(node.children) == 1


class TestLogicalNodeFlattening:
    def test_and_flattens_same_operator(self) -> None:
        a = Field("a") == 1
        b = Field("b") == 2
        c = Field("c") == 3
        node = (a & b) & c
        assert node.operator == "AND"
        assert len(node.children) == 3

    def test_and_does_not_flatten_different_operator(self) -> None:
        a = Field("a") == 1
        b = Field("b") == 2
        c = Field("c") == 3
        node = (a | b) & c
        assert node.operator == "AND"
        assert len(node.children) == 2
        assert isinstance(node.children[0], LogicalNode)
        assert node.children[0].operator == "OR"

    def test_or_flattens_same_operator(self) -> None:
        a = Field("a") == 1
        b = Field("b") == 2
        c = Field("c") == 3
        node = (a | b) | c
        assert node.operator == "OR"
        assert len(node.children) == 3

    def test_or_does_not_flatten_different_operator(self) -> None:
        a = Field("a") == 1
        b = Field("b") == 2
        c = Field("c") == 3
        node = (a & b) | c
        assert node.operator == "OR"
        assert len(node.children) == 2

    def test_not_single_child(self) -> None:
        a = Field("x") == 1
        node = ~a
        assert node.operator == "NOT"
        assert len(node.children) == 1

    def test_flattening_preserves_order(self) -> None:
        a = Field("a") == 1
        b = Field("b") == 2
        c = Field("c") == 3
        node = a & b & c
        assert len(node.children) == 3
        assert node.children[0] is a
        assert node.children[1] is b
        assert node.children[2] is c


class TestExistsNode:
    def test_exists_default(self) -> None:
        sub = Select().select("1").from_table("orders")
        node = ExistsNode(sub)
        assert node.select is sub
        assert node.negated is False

    def test_not_exists(self) -> None:
        sub = Select().select("1").from_table("orders")
        node = ExistsNode(sub, negated=True)
        assert node.negated is True


class TestCaseNode:
    def test_when_chain(self) -> None:
        c = CaseNode()
        c.when(Field("score") >= 90, "A")
        c.when(Field("score") >= 80, "B")
        assert len(c._whens) == 2

    def test_else_last_wins(self) -> None:
        c = CaseNode()
        c.else_("N/A")
        c.else_("Unknown")
        assert c._else == "Unknown"

    def test_no_else(self) -> None:
        c = CaseNode()
        c.when(Field("x") == 1, "one")
        assert c._else is None


class TestSQLFunction:
    def test_count_star(self) -> None:
        f = SQLFunction("count", "*")
        assert f.name == "count"
        assert f.args == ("*",)

    def test_coalesce(self) -> None:
        f = SQLFunction("coalesce", Field("name"), "N/A")
        assert f.name == "coalesce"
        assert len(f.args) == 2

    def test_sum(self) -> None:
        f = SQLFunction("sum", Field("amount"))
        assert f.name == "sum"

    def test_alias(self) -> None:
        f = SQLFunction("count", "*")
        f.alias("cnt")
        assert f._alias == "cnt"
