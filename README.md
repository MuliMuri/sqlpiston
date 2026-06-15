# SQLPiston

[![test](https://github.com/MuliMuri/sqlpiston/actions/workflows/test.yml/badge.svg)](https://github.com/MuliMuri/sqlpiston/actions/workflows/test.yml)
[![lint](https://github.com/MuliMuri/sqlpiston/actions/workflows/lint.yml/badge.svg)](https://github.com/MuliMuri/sqlpiston/actions/workflows/lint.yml)
[![coverage](https://codecov.io/gh/MuliMuri/sqlpiston/branch/main/graph/badge.svg)](https://codecov.io/gh/MuliMuri/sqlpiston)
[![pypi](https://img.shields.io/pypi/v/sqlpiston.svg)](https://pypi.org/project/sqlpiston/)
[![python](https://img.shields.io/pypi/pyversions/sqlpiston)](https://pypi.org/project/sqlpiston/)
[![license](https://img.shields.io/github/license/MuliMuri/sqlpiston)](https://github.com/MuliMuri/sqlpiston/blob/main/LICENSE)

*Write once, query everywhere — build SQL with Python operators.*

[中文版](README_ZH.md)

SQLPiston is a low-level SQL library that builds parameterized SQL queries
through Python operator overloading. AST nodes carry zero SQL knowledge;
dialect-specific compilers translate the same AST into the right SQL for each
database.

## Install

```bash
git clone https://github.com/MuliMuri/sqlpiston.git
cd sqlpiston
pip install -e .
```

Python 3.9+ on Linux / macOS / Windows.

## Basic Usage

```python
from sqlpiston import Select, Field, Insert
from sqlpiston import DBEngine, DBType, Session
from dataclasses import dataclass

eng = DBEngine(DBType.SQLite)
eng.init_engine(":memory:")
session = Session(eng)

stmt = (
    Select()
    .select("id", "name", "age")
    .from_table("users")
    .where((Field("age") >= 18) & (Field("status") == "active"))
    .order_by("id", "ASC")
    .limit(10)
)
result = session.execute(stmt)

@dataclass
class User:
    id: int
    name: str
    age: int

users = result.map(User)

session.execute(
    Insert().into("users").values({"name": "Alice", "age": 25})
)

session.commit()
session.close()
```

<details>
<summary>More examples: JOIN, subquery, CTE, UPSERT, DDL</summary>

**JOIN**

```python
Select() \
    .select("users.name", "orders.total") \
    .from_table("users") \
    .join("orders",
          Field("user_id", "orders") == Field("id", "users")) \
    .where(Field("total", "orders") > 100)
```

**Subquery (IN / EXISTS / Scalar)**

```python
# IN subquery
admin_ids = Select().select("id").from_table("admins")
stmt = Select().select("name").from_table("users") \
    .where(Field("id").is_in(admin_ids))

# EXISTS
sub = Select().select("1").from_table("orders") \
    .where(Field("user_id", "orders") == Field("id", "users"))
stmt = Select().select("name").from_table("users").where(sub.exists())

# Scalar
avg = Select().select(SQLFunction("avg", "salary")).from_table("employees")
stmt = Select().select("name").from_table("staff").where(Field("salary") > avg)
```

**CTE**

```python
cte = Select().select("*").from_table("sales") \
    .where(Field("amount") > 100).cte("big_sales")
stmt = Select().with_(cte).select("*").from_table("big_sales")
```

**UPSERT — same AST, different SQL per dialect**

```python
Upsert() \
    .into("users") \
    .values({"id": 1, "name": "X"}) \
    .on_conflict("id") \
    .do_update({"name": "X"})
```

| Dialect | Generated SQL |
|---------|--------------|
| MySQL   | `INSERT INTO ... ON DUPLICATE KEY UPDATE` |
| SQLite  | `INSERT INTO ... ON CONFLICT DO UPDATE`   |

**DDL**

```python
CreateTable().table("users").if_not_exists() \
    .column("id", "INTEGER", primary_key=True, nullable=False) \
    .column("name", "VARCHAR(255)")

AlterTable().table("users").add_column("age", "INTEGER", default=0)

DropTable().table("users").if_exists()
```

</details>

## Highlights

- **Operator overloading** — `Field("age") >= 18` builds AST, not a boolean
- **Dialect-aware** — same AST compiles to MySQL (%s, backticks) or SQLite (?, double-quotes)
- **Full standard SQL** — SELECT, INSERT, UPDATE, DELETE, UPSERT, CTE, UNION, subqueries, DDL
- **Parameterized by design** — values never interpolated into SQL strings
- **Weak ORM** — result-to-dataclass mapping, no identity map or change tracking

## Documentation

```bash
cd docs
pip install -r requirements.txt
sphinx-build -b html source build/html
```

## License

MIT
