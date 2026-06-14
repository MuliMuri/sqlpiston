from typing import TypeAlias, Union


SQLValue: TypeAlias = Union[str, int, float, bool, None, bytes]
ColumnValue = SQLValue
