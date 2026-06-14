# SQLPiston

[![test](https://github.com/MuliMuri/sqlpiston/actions/workflows/test.yml/badge.svg)](https://github.com/MuliMuri/sqlpiston/actions/workflows/test.yml)
[![lint](https://github.com/MuliMuri/sqlpiston/actions/workflows/lint.yml/badge.svg)](https://github.com/MuliMuri/sqlpiston/actions/workflows/lint.yml)
[![coverage](https://codecov.io/gh/MuliMuri/sqlpiston/branch/main/graph/badge.svg)](https://codecov.io/gh/MuliMuri/sqlpiston)
[![pypi](https://img.shields.io/pypi/v/sqlpiston.svg)](https://pypi.org/project/sqlpiston/)
[![python](https://img.shields.io/pypi/pyversions/sqlpiston)](https://pypi.org/project/sqlpiston/)
[![license](https://img.shields.io/github/license/MuliMuri/sqlpiston)](https://github.com/MuliMuri/sqlpiston/blob/main/LICENSE)

*一次编写，到处查询 — 用 Python 运算符构建 SQL。*

[English](README.md)

SQLPiston 是一个底层 Python SQL 库，通过运算符重载构建参数化 SQL
查询。AST 节点不包含任何 SQL 知识；方言编译器将同一个 AST 翻译为不同数据库的 SQL。

## 安装

```bash
git clone https://github.com/MuliMuri/sqlpiston.git
cd sqlpiston
pip install -e .
```

Python 3.9+，支持 Linux / macOS / Windows。

## 基本用法

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
<summary>更多示例：JOIN、子查询、CTE、UPSERT、DDL</summary>

**JOIN**

```python
Select() \
    .select("users.name", "orders.total") \
    .from_table("users") \
    .join("orders",
          Field("user_id", "orders") == Field("id", "users")) \
    .where(Field("total", "orders") > 100)
```

**子查询（IN / EXISTS / 标量）**

```python
# IN 子查询
admin_ids = Select().select("id").from_table("admins")
stmt = Select().select("name").from_table("users") \
    .where(Field("id").is_in(admin_ids))

# EXISTS
sub = Select().select("1").from_table("orders") \
    .where(Field("user_id", "orders") == Field("id", "users"))
stmt = Select().select("name").from_table("users").where(sub.exists())

# 标量子查询
avg = Select().select(SQLFunction("avg", "salary")).from_table("employees")
stmt = Select().select("name").from_table("staff").where(Field("salary") > avg)
```

**CTE**

```python
cte = Select().select("*").from_table("sales") \
    .where(Field("amount") > 100).cte("big_sales")
stmt = Select().with_(cte).select("*").from_table("big_sales")
```

**UPSERT — 同一 AST，不同方言生成不同 SQL**

```python
Upsert() \
    .into("users") \
    .values({"id": 1, "name": "X"}) \
    .on_conflict("id") \
    .do_update({"name": "X"})
```

| 方言   | 生成 SQL |
|--------|---------|
| MySQL  | `INSERT INTO ... ON DUPLICATE KEY UPDATE` |
| SQLite | `INSERT INTO ... ON CONFLICT DO UPDATE`   |

**DDL**

```python
CreateTable().table("users").if_not_exists() \
    .column("id", "INTEGER", primary_key=True, nullable=False) \
    .column("name", "VARCHAR(255)")

AlterTable().table("users").add_column("age", "INTEGER", default=0)

DropTable().table("users").if_exists()
```

</details>

## 特性

- **运算符重载** — `Field("age") >= 18` 构建 AST 节点，而非布尔值
- **方言感知** — 同一 AST 编译为 MySQL（%s、反引号）或 SQLite（?、双引号）
- **标准 SQL 全覆盖** — SELECT / INSERT / UPDATE / DELETE / UPSERT / CTE / UNION / 子查询 / DDL
- **默认参数化** — 值永远不会拼入 SQL 字符串
- **弱 ORM** — 结果到 dataclass 的映射，无 identity map 和变更追踪

## 文档

```bash
cd docs
pip install -r requirements.txt
sphinx-build -b html source build/html
```

## 许可证

MIT
