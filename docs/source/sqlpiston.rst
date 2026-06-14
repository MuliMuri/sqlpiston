SQLPiston API
=============

Engine
------

.. py:method:: DBEngine(db_type: DBType) -> Engine

    :param DBType db_type: Database type (``DBType.MySQL`` or ``DBType.SQLite``)
    :return: Concrete engine instance
    :rtype: Engine

    Factory function that returns a typed engine subclass.

    .. code-block:: python

        eng = DBEngine(DBType.SQLite)
        eng.init_engine(":memory:")

.. py:class:: DBType

    Enum with values ``MySQL`` and ``SQLite``.

.. py:class:: Session(engine: Engine, pool: Optional[ConnectionPool] = None)

    Entry point for users. Binds engine, compiles AST, executes SQL.

    .. py:method:: execute(stmt: ASTNode) -> ResultSet

        Compile the statement with the engine's dialect, execute via pool, return ``ResultSet``.

    .. py:method:: begin() -> None

        Begin a transaction on the current connection.

    .. py:method:: commit() -> None

        Commit the current transaction.

    .. py:method:: rollback() -> None

        Rollback the current transaction.

    .. py:method:: close() -> None

        Release connection and close pool.

.. py:class:: ConnectionPool(engine: Engine, min_size: int = 1, max_size: int = 10)

    Thread-safe connection pool.

    .. py:method:: acquire() -> Connection

    .. py:method:: release(conn: Connection) -> None

    .. py:method:: close() -> None

Builder — Expression Nodes
--------------------------

.. py:class:: Field(name: str, table: Optional[str] = None)

    Column reference. Overloaded operators return AST nodes.

    +------------------+---------------------------+
    | Operation        | Result                    |
    +==================+===========================+
    | ``Field>=val``   | ``ComparisonNode``        |
    +------------------+---------------------------+
    | ``Field!=val``   | ``ComparisonNode``        |
    +------------------+---------------------------+
    | ``Field<val``    | ``ComparisonNode``        |
    +------------------+---------------------------+
    | ``Field<=val``   | ``ComparisonNode``        |
    +------------------+---------------------------+
    | ``Field>val``    | ``ComparisonNode``        |
    +------------------+---------------------------+
    | ``Field>=val``   | ``ComparisonNode``        |
    +------------------+---------------------------+
    | ``&`` (on nodes) | ``LogicalNode('AND')``    |
    +------------------+---------------------------+
    | ``|`` (on nodes) | ``LogicalNode('OR')``     |
    +------------------+---------------------------+
    | ``~`` (on nodes) | ``LogicalNode('NOT')``    |
    +------------------+---------------------------+

    .. py:method:: is_in(values: Sequence[SQLValue] | Select) -> InNode

        ``field IN (v1, v2, ...)`` or ``field IN (SELECT ...)``.

    .. py:method:: between(low, high) -> BetweenNode

        ``field BETWEEN low AND high``.

    .. py:method:: is_null() -> ComparisonNode

        ``field IS NULL``.

    .. py:method:: is_not_null() -> ComparisonNode

        ``field IS NOT NULL``.

    .. py:method:: alias(name: str) -> Field

        Return a new Field with the given alias.

.. py:class:: CaseNode

    ``CASE WHEN ... THEN ... ELSE ... END`` expression.

    .. py:method:: when(condition: ASTNode, result) -> CaseNode

    .. py:method:: else_(default) -> CaseNode

.. py:class:: SQLFunction(name: str, *args)

    SQL function call. Examples: ``SQLFunction("count", "*")``, ``SQLFunction("sum", Field("amount"))``.

    .. py:method:: alias(name: str) -> SQLFunction

Builder — Statements
--------------------

.. py:class:: Select

    Fluent ``SELECT`` builder. All modifiers return ``self`` for chaining.

    .. py:method:: select(*columns) -> Select
    .. py:method:: distinct() -> Select
    .. py:method:: from_table(table: str | Select) -> Select
    .. py:method:: where(condition: ASTNode) -> Select
    .. py:method:: join(table, on, how='INNER') -> Select
    .. py:method:: left_join(table, on) -> Select
    .. py:method:: right_join(table, on) -> Select
    .. py:method:: cross_join(table) -> Select
    .. py:method:: group_by(*fields) -> Select
    .. py:method:: having(condition: ASTNode) -> Select
    .. py:method:: order_by(field, direction='ASC') -> Select
    .. py:method:: limit(count: int) -> Select
    .. py:method:: offset(start: int) -> Select
    .. py:method:: as_(alias: str) -> Select
    .. py:method:: exists() -> ExistsNode
    .. py:method:: not_exists() -> ExistsNode
    .. py:method:: union(other: Select) -> CompoundSelect
    .. py:method:: union_all(other: Select) -> CompoundSelect
    .. py:method:: intersect(other: Select) -> CompoundSelect
    .. py:method:: except_(other: Select) -> CompoundSelect
    .. py:method:: cte(name: str) -> CTE
    .. py:method:: with_(*ctes: CTE) -> Select

.. py:class:: Insert

    Fluent ``INSERT`` builder.

    .. py:method:: into(table: str) -> Insert
    .. py:method:: values(data: Dict[str, ColumnValue]) -> Insert
    .. py:method:: select(select: Select) -> Insert

.. py:class:: Update

    Fluent ``UPDATE`` builder.

    .. py:method:: table(name: str) -> Update
    .. py:method:: set(data: Dict[str, ColumnValue]) -> Update
    .. py:method:: where(condition: ASTNode) -> Update

.. py:class:: Delete

    Fluent ``DELETE`` builder.

    .. py:method:: from_table(table: str) -> Delete
    .. py:method:: where(condition: ASTNode) -> Delete

.. py:class:: Upsert

    Standard ``UPSERT`` — AST stores intent, dialect compilers translate.

    .. py:method:: into(table: str) -> Upsert
    .. py:method:: values(data: Dict[str, ColumnValue]) -> Upsert
    .. py:method:: on_conflict(*columns: str) -> Upsert
    .. py:method:: do_update(data: Dict[str, ColumnValue]) -> Upsert
    .. py:method:: do_nothing() -> Upsert

Builder — DDL
--------------

.. py:class:: CreateTable

    .. py:method:: table(name: str) -> CreateTable
    .. py:method:: if_not_exists() -> CreateTable
    .. py:method:: column(name, type_, *, nullable=True, primary_key=False, default=None, unique=False) -> CreateTable
    .. py:method:: columns(*col_defs: ColumnDef) -> CreateTable

.. py:class:: AlterTable

    .. py:method:: table(name: str) -> AlterTable
    .. py:method:: add_column(name, type_, *, nullable=True, default=None) -> AlterTable
    .. py:method:: drop_column(name: str) -> AlterTable
    .. py:method:: modify_column(name, type_, *, nullable=True, default=None) -> AlterTable

.. py:class:: DropTable

    .. py:method:: table(name: str) -> DropTable
    .. py:method:: if_exists() -> DropTable

.. py:class:: CreateIndex

    .. py:method:: name(idx_name: str) -> CreateIndex
    .. py:method:: on(table: str) -> CreateIndex
    .. py:method:: columns(*cols: str) -> CreateIndex
    .. py:method:: unique() -> CreateIndex
    .. py:method:: if_not_exists() -> CreateIndex

.. py:class:: DropIndex

    .. py:method:: name(idx_name: str) -> DropIndex
    .. py:method:: on(table: str) -> DropIndex
    .. py:method:: if_exists() -> DropIndex

.. py:class:: CreateView

    .. py:method:: name(view_name: str) -> CreateView
    .. py:method:: as_(select: Select) -> CreateView
    .. py:method:: if_not_exists() -> CreateView

.. py:class:: DropView

    .. py:method:: name(view_name: str) -> DropView
    .. py:method:: if_exists() -> DropView

.. py:class:: Truncate

    .. py:method:: table(name: str) -> Truncate

.. py:class:: ColumnDef(name, type_, nullable=True, primary_key=False, default=None, unique=False)

    Dataclass for column definitions.

ORM — Result Mapping
---------------------

.. py:class:: ResultSet

    Iterable set of mapped results from a query.

    .. py:method:: all() -> List[Dict[str, SQLValue]]

        Return all rows as dicts.

    .. py:method:: one() -> Dict[str, SQLValue]

        Return exactly one row. Raise if 0 or >1.

    .. py:method:: one_or_none() -> Optional[Dict[str, SQLValue]]

        Return one row or None.

    .. py:method:: first() -> Optional[Dict[str, SQLValue]]

        Return first row or None.

    .. py:method:: scalar() -> Any

        Return the first column of the first row.

    .. py:method:: map(target: Type[T]) -> List[T]

        Map all rows to a dataclass type.

    .. py:method:: map_one(target: Type[T]) -> T

        Map exactly one row to a dataclass type.

    .. py:attribute:: rowcount
        :type: int

Compiler
--------

.. py:class:: Dialect(placeholder: str, quote_char: str, compiler_cls: Type[Compiler])

    Holds compiler factory and syntax config for a database.

    .. py:method:: get_compiler() -> Compiler

.. py:class:: MySQLCompiler

    MySQL dialect. ``%s`` placeholders, ``\`backtick\``` quoting.

.. py:class:: SQLiteCompiler

    SQLite dialect. ``?`` placeholders, ``"double-quote"`` quoting.
