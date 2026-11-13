from typing import Literal as TypingLiteral

from kyubi.fields.expression import Expression
from kyubi.tabledef import TableDef


class Condition(Expression):
    def __init__(self, left: Expression, op: str, right: Expression):
        super().__init__()
        self._left = left
        self._op = op
        self._right = right

    def _as_operand(self, table_def: TableDef) -> str:
        return f"({self._value(table_def)})"

    def _value(self, table_def: TableDef) -> str:
        return (
            f"{self._left._as_operand(table_def)} "
            f"{self._op} {self._right._as_operand(table_def)}"
        )


class OrderClause:
    def __init__(self, field: Expression, order: TypingLiteral["asc", "desc"] = "asc"):
        self._field = field
        self._order = order

    def build(self, table_def: TableDef) -> str:
        return f"{self._field._value(table_def)} {self._order}"
