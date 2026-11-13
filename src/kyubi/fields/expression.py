from __future__ import annotations

import abc
from copy import copy
from typing import Self

from kyubi.tabledef import TableDef

type Operand = Expression | str | float | bool | None


class Expression(abc.ABC):
    def __init__(self, alias: str | None = None):
        self._alias = alias

    def alias(self, alias: str) -> Self:
        new_field = copy(self)
        new_field._alias = alias
        return new_field

    def _build_alias(self) -> str:
        return f" AS {self._alias}" if self._alias else ""

    @abc.abstractmethod
    def _value(self, table_def: TableDef) -> str:
        raise NotImplementedError

    def _as_operand(self, table_def: TableDef) -> str:
        return self._value(table_def)

    def build(self, table_def: TableDef) -> str:
        return f"{self._value(table_def)}{self._build_alias()}"

    def __add__(self, other: Operand) -> Addition:
        return Addition(self, other)

    def __radd__(self, other: Operand) -> Addition:
        return Addition(other, self)

    def __sub__(self, other: Operand) -> Subtraction:
        return Subtraction(self, other)

    def __rsub__(self, other: Operand) -> Subtraction:
        return Subtraction(other, self)

    def __mul__(self, other: Operand) -> Multiplication:
        return Multiplication(self, other)

    def __rmul__(self, other: Operand) -> Multiplication:
        return Multiplication(other, self)

    def __truediv__(self, other: Operand) -> Division:
        return Division(self, other)

    def __rtruediv__(self, other: Operand) -> Division:
        return Division(other, self)

    def __pos__(self) -> Positive:
        return Positive(self)

    def __neg__(self) -> Negative:
        return Negative(self)

    def not_(self) -> Not:
        return Not(self)

    def __lt__(self, other: Operand) -> Less:
        return Less(self, other)

    def __le__(self, other: Operand) -> LessOrEqual:
        return LessOrEqual(self, other)

    def __eq__(self, other: object) -> Equal | IsNull:  # type: ignore[override]
        operand = as_expression(other)
        if _is_null(self):
            return IsNull(operand)
        if _is_null(operand):
            return IsNull(self)
        return Equal(self, operand)

    def __ne__(self, other: object) -> NotEqual | IsNotNull:  # type: ignore[override]
        operand = as_expression(other)
        if _is_null(self):
            return IsNotNull(operand)
        if _is_null(operand):
            return IsNotNull(self)
        return NotEqual(self, operand)

    def __gt__(self, other: Operand) -> Greater:
        return Greater(self, other)

    def __ge__(self, other: Operand) -> GreaterOrEqual:
        return GreaterOrEqual(self, other)

    def is_in(self, *other: Operand) -> IsIn:
        return IsIn(self, list(other))

    def between(self, a: Operand, b: Operand):
        return Between(self, a, b)

    def __and__(self, other: Operand):
        return And(self, other)

    def __or__(self, other: Operand):
        return Or(self, other)


class IsIn(Expression):
    def __init__(
        self, left: Operand, to_check: list[Operand], alias: str | None = None
    ):
        super().__init__(alias)
        self._left = as_expression(left)
        self._to_check = [as_expression(i) for i in to_check]

    def _value(self, table_def: TableDef) -> str:
        return f"{self._left._as_operand(table_def)} IN ({', '.join([i._as_operand(table_def) for i in self._to_check])})"


class Between(Expression):
    def __init__(self, left: Operand, a: Operand, b: Operand, alias: str | None = None):
        super().__init__(alias)
        self._left = as_expression(left)
        self._a = as_expression(a)
        self._b = as_expression(b)

    def _value(self, table_def: TableDef) -> str:
        return f"{self._left._as_operand(table_def)} BETWEEN {self._a._as_operand(table_def)} AND {self._b._as_operand(table_def)}"


class _BinaryExpression(Expression):
    _operator: str

    def __init__(self, left: Operand, right: Operand, alias: str | None = None):
        super().__init__(alias)
        self._left = as_expression(left)
        self._right = as_expression(right)

    def _as_operand(self, table_def: TableDef) -> str:
        return f"({self._value(table_def)})"

    def _value(self, table_def: TableDef) -> str:
        left = self._left._as_operand(table_def)
        right = self._right._as_operand(table_def)
        return f"{left} {self._operator} {right}"


class And(_BinaryExpression):
    _operator = "AND"


class Or(_BinaryExpression):
    _operator = "OR"


class Addition(_BinaryExpression):
    _operator = "+"


class Subtraction(_BinaryExpression):
    _operator = "-"


class Multiplication(_BinaryExpression):
    _operator = "*"


class Division(_BinaryExpression):
    _operator = "/"


def as_expression(value: object) -> Expression:
    if isinstance(value, Expression):
        return value
    if value is None or isinstance(value, (str, int, float, bool)):
        return Literal(value)
    raise TypeError(f"Unsupported operand type: {type(value).__name__}")


def _is_null(expression: Expression) -> bool:
    return isinstance(expression, Literal) and expression._literal is None


class Less(_BinaryExpression):
    _operator = "<"


class LessOrEqual(_BinaryExpression):
    _operator = "<="


class Equal(_BinaryExpression):
    _operator = "="


class NotEqual(_BinaryExpression):
    _operator = "!="


class _NullComparison(_BinaryExpression):
    def __init__(self, expression: Expression, alias: str | None = None):
        super().__init__(expression, Literal(None), alias)


class IsNull(_NullComparison):
    _operator = "IS"


class IsNotNull(_NullComparison):
    _operator = "IS NOT"


class GreaterOrEqual(_BinaryExpression):
    _operator = ">="


class Greater(_BinaryExpression):
    _operator = ">"


class _UnaryExpression(Expression):
    _operator: str

    def __init__(self, operand: Expression, alias: str | None = None):
        super().__init__(alias)
        self._operand = operand

    def _as_operand(self, table_def: TableDef) -> str:
        return f"({self._value(table_def)})"

    def _value(self, table_def: TableDef) -> str:
        operand = self._operand._as_operand(table_def)
        if self._operator in {"+", "-"} and operand.startswith(("+", "-")):
            operand = f"({operand})"
        return f"{self._operator}{operand}"


class Positive(_UnaryExpression):
    _operator = "+"


class Negative(_UnaryExpression):
    _operator = "-"


class Not(_UnaryExpression):
    _operator = "NOT "


def escape_string(s: str) -> str:
    return s.replace("'", "''")


class Literal(Expression):
    def __init__(self, value: str | float | bool | None, alias: str | None = None):
        super().__init__(alias)
        self._literal = value

    def _value(self, table_def: TableDef) -> str:
        if isinstance(self._literal, str):
            return f"'{escape_string(self._literal)}'"
        if self._literal is None:
            return "NULL"
        return str(self._literal)
