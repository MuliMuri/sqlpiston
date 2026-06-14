Basic Usage
===========

You can simply use SQLPiston by importing the required classes.

.. code-block:: python

    from sqlpiston import Select, Field, Insert, Update
    from sqlpiston import DBEngine, DBType, Session
    from dataclasses import dataclass

    # Create engine and session
    eng = DBEngine(DBType.SQLite)
    eng.init_engine(":memory:")
    session = Session(eng)

    # Build a SELECT with operator overloading
    stmt = (
        Select()
        .select("id", "name", "age")
        .from_table("users")
        .where((Field("age") >= 18) & (Field("status") == "active"))
        .order_by("id", "ASC")
        .limit(10)
    )

    # Execute and map results
    result = session.execute(stmt)

    @dataclass
    class User:
        id: int
        name: str
        age: int

    users = result.map(User)

    # INSERT
    session.execute(
        Insert().into("users").values({"name": "Alice", "age": 25})
    )

    # UPDATE
    session.execute(
        Update()
        .table("users")
        .set({"status": "inactive"})
        .where(Field("last_login") < "2024-01-01")
    )

    session.commit()
    session.close()
