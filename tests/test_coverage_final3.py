"""Last coverage gaps."""
from sqlpiston.builder.nodes import CaseNode, Field
from sqlpiston.compiler.mysql import MySQLCompiler


class TestCaseNodeElse:
    def test_else_repr(self) -> None:
        c = CaseNode()
        c.when(Field("x") == 1, "yes")
        c.else_("no")
        r = repr(c)
        assert "has_else=True" in r


class TestCaseCompilerElse:
    def test_compile_case_with_else(self) -> None:
        c = MySQLCompiler()
        node = (
            CaseNode()
            .when(Field("score") >= 90, "A")
            .else_("F")
        )
        sql, params = c.visit_case(node)
        assert "ELSE" in sql
        assert params[-1] == "F"


class TestFieldHash:
    def test_hash_with_alias(self) -> None:
        f = Field("a").alias("x")
        h = hash(f)
        assert isinstance(h, int)


class TestOneOrNoneHappy:
    def test_one_or_none_happy_path(self) -> None:
        from tests.test_mapper import MockCursor
        from sqlpiston.orm.mapper import ResultSet
        cursor = MockCursor([(42,)], ["val"])
        rs = ResultSet(cursor, ["val"])
        result = rs.one_or_none()
        assert result == {"val": 42}
