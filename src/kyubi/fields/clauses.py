from typing import Literal as TypingLiteral

from kyubi.fields.expression import Expression, Qualification


class Condition(Expression):
    def __init__(self, left: Expression, op: str, right: Expression):
        super().__init__()
        self._left = left
        self._op = op
        self._right = right

    def _as_operand(self, *, qualify: Qualification = "alias") -> str:
        return f"({self.build(alias=False, qualify=qualify)})"

    def build(self, *, alias: bool = True, qualify: Qualification = "alias") -> str:
        return (
            f"{self._left._as_operand(qualify=qualify)} "
            f"{self._op} {self._right._as_operand(qualify=qualify)}"
            f"{self._build_alias() if alias else ''}"
        )


class OrderClause:
    def __init__(self, field: Expression, order: TypingLiteral["asc", "desc"] = "asc"):
        self._field = field
        self._order = order

    def build(self, *, qualify: Qualification = "alias") -> str:
        return f"{self._field.build(alias=False, qualify=qualify)} {self._order}"
