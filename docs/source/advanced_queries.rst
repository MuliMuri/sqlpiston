Advanced Queries
=================

JOIN
----

.. code-block:: python

    Select() \
        .select("users.name", "orders.total") \
        .from_table("users") \
        .join("orders",
              Field("user_id", "orders") == Field("id", "users")) \
        .where(Field("total", "orders") > 100)

Subquery in WHERE (IN)
-----------------------

.. code-block:: python

    admin_ids = Select().select("id").from_table("admins")
    stmt = Select().select("name").from_table("users") \
        .where(Field("id").is_in(admin_ids))

EXISTS
------

.. code-block:: python

    sub = (
        Select().select("1").from_table("orders")
        .where(Field("user_id", "orders") == Field("id", "users"))
    )
    stmt = Select().select("name").from_table("users") \
        .where(sub.exists())

Scalar Subquery
---------------

.. code-block:: python

    avg_salary = Select().select(SQLFunction("avg", "salary")) \
        .from_table("employees")
    stmt = Select().select("name").from_table("staff") \
        .where(Field("salary") > avg_salary)

Subquery in FROM (Derived Table)
---------------------------------

.. code-block:: python

    sub = (
        Select()
        .select("user_id", SQLFunction("count", "*").alias("cnt"))
        .from_table("orders")
        .group_by("user_id")
        .as_("t")
    )
    stmt = (
        Select()
        .select("users.name", "t.cnt")
        .from_table(sub)
        .join("users",
              Field("id", "users") == Field("user_id", "t"))
    )

UNION
-----

.. code-block:: python

    Select().select("name").from_table("customers") \
        .union_all(
            Select().select("name").from_table("suppliers")
        )

CTE (WITH)
----------

.. code-block:: python

    cte = Select().select("*").from_table("sales") \
        .where(Field("amount") > 100).cte("big_sales")
    stmt = Select().with_(cte).select("*").from_table("big_sales")

CASE WHEN
---------

.. code-block:: python

    from sqlpiston import CaseNode

    grade = (
        CaseNode()
        .when(Field("score") >= 90, "A")
        .when(Field("score") >= 80, "B")
        .when(Field("score") >= 70, "C")
        .else_("D")
    )
    stmt = Select().select("name", grade).from_table("students")

INSERT ... SELECT
-----------------

.. code-block:: python

    Insert().into("archived_users").select(
        Select().select("name", "age")
            .from_table("users")
            .where(Field("last_login") < "2024-01-01")
    )

UPSERT
------

MySQL dialect:

.. code-block:: python

    Upsert() \
        .into("users") \
        .values({"id": 1, "name": "X", "age": 25}) \
        .on_conflict("id") \
        .do_update({"name": "X", "age": 25})

The same UPSERT AST compiles differently per dialect:

+------------+---------------------------------------------+
| Dialect    | SQL                                         |
+============+=============================================+
| MySQL      | ``INSERT INTO ... ON DUPLICATE KEY UPDATE`` |
+------------+---------------------------------------------+
| SQLite     | ``INSERT INTO ... ON CONFLICT DO UPDATE``   |
+------------+---------------------------------------------+

DDL
---

.. code-block:: python

    from sqlpiston import CreateTable, AlterTable, DropTable

    # CREATE
    CreateTable().table("users").if_not_exists() \
        .column("id", "INTEGER", primary_key=True, nullable=False) \
        .column("name", "VARCHAR(255)") \
        .column("email", "VARCHAR(255)", unique=True)

    # ALTER
    AlterTable().table("users") \
        .add_column("age", "INTEGER", default=0)

    # DROP
    DropTable().table("users").if_exists()
