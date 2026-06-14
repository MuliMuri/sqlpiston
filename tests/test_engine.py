from sqlpiston.core.engine import DBType
from sqlpiston.core.engine.base import DBEngine
from sqlpiston.core.engine.mysql import MySQLEngine
from sqlpiston.core.engine.sqlite import SQLiteEngine
from sqlpiston.compiler.mysql import MySQLDialect
from sqlpiston.compiler.sqlite import SQLiteDialect


class TestDBType:
    def test_mysql(self) -> None:
        assert DBType.MySQL.value == 1

    def test_sqlite(self) -> None:
        assert DBType.SQLite.value == 2


class TestDBEngineFactory:
    def test_mysql_engine(self) -> None:
        eng = DBEngine(DBType.MySQL)
        assert isinstance(eng, MySQLEngine)

    def test_sqlite_engine(self) -> None:
        eng = DBEngine(DBType.SQLite)
        assert isinstance(eng, SQLiteEngine)

    def test_invalid_type_raises(self) -> None:
        try:
            DBEngine("invalid")  # type: ignore[arg-type]
        except ValueError:
            pass


class TestSQLiteEngine:
    def test_init_engine(self) -> None:
        eng = SQLiteEngine()
        eng.init_engine(":memory:")
        assert eng._file_path == ":memory:"

    def test_dialect(self) -> None:
        eng = SQLiteEngine()
        assert isinstance(eng.dialect, SQLiteDialect)

    def test_connect(self) -> None:
        eng = SQLiteEngine()
        eng.init_engine(":memory:")
        conn = eng.connect()
        assert conn is not None
        conn.close()
        eng.close()

    def test_connect_without_init_raises(self) -> None:
        eng = SQLiteEngine()
        try:
            eng.connect()
            assert False, "Should have raised RuntimeError"
        except RuntimeError:
            pass


class TestMySQLEngine:
    def test_init_engine(self) -> None:
        eng = MySQLEngine()
        eng.init_engine("localhost", 3306, "root", "", "test")
        assert eng._config is not None
        assert eng._config["host"] == "localhost"

    def test_dialect(self) -> None:
        eng = MySQLEngine()
        assert isinstance(eng.dialect, MySQLDialect)
