from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Self

from kyubi.fields import Expression, Field, OrderClause
from kyubi.fields.expression import Operand, as_expression
from kyubi.queries.query import Query
from kyubi.tabledef import TableDef

if TYPE_CHECKING:
    from kyubi.table import Table


class WhereMixin(Query):
    def __init__(self, table_def: TableDef):
        super().__init__(table_def)
        self._conditions: list[Expression] = []

    def where(self, *args: Operand) -> Self:
        new_query = deepcopy(self)
        new_query._conditions.extend(as_expression(arg) for arg in args)
        return new_query


class OrderByMixin(Query):
    def __init__(self, table_def: TableDef):
        super().__init__(table_def)
        self._order: list[OrderClause] = []

    def order_by(self, *args: OrderClause) -> Self:
        new_query = deepcopy(self)
        new_query._order.extend(args)
        return new_query


class LimitMixin(Query):
    def __init__(self, table_def: TableDef):
        super().__init__(table_def)
        self._limit: int | None = None

    def limit(self, limit: int) -> Self:
        new_query = deepcopy(self)
        new_query._limit = limit
        return new_query


class OffsetMixin(Query):
    def __init__(self, table_def: TableDef):
        super().__init__(table_def)
        self._offset: int | None = None

    def offset(self, offset: int) -> Self:
        new_query = deepcopy(self)
        new_query._offset = offset
        return new_query


class PaginationMixin(LimitMixin, OffsetMixin):
    pass


class ReturningMixin(Query):
    def __init__(self, table_def: TableDef):
        super().__init__(table_def)
        self._returning: list[Field] = []

    def returning(self, *args: Field) -> Self:
        new_query = deepcopy(self)
        new_query._returning.extend(args)
        return new_query

    def _validate_returning(self) -> None:
        for field in self._returning:
            field._validate_source(self._table_def)


@dataclass
class JoinConfig:
    table_def: TableDef
    join_type: Literal["LEFT", "RIGHT", "FULL", "INNER", "CROSS"]
    on: tuple[Expression, ...] = ()
    using: tuple[str, ...] = ()


class JoinMixin(Query):
    def __init__(self, table_def: TableDef):
        super().__init__(table_def)
        self._joins: list[JoinConfig] = []

    def _join(
        self,
        table: Table,
        join_type: Literal["LEFT", "RIGHT", "FULL", "INNER", "CROSS"],
        on: Expression | Sequence[Expression] | None,
        using: str | Sequence[str] | None,
    ) -> Self:
        new_query = deepcopy(self)
        new_query._joins.append(
            JoinConfig(
                table_def=table._build_table_def(),
                join_type=join_type,
                on=(on,) if isinstance(on, Expression) else tuple(on or ()),
                using=(using,) if isinstance(using, str) else tuple(using or ()),
            )
        )
        return new_query

    def join(
        self,
        table: Table,
        on: Expression | Sequence[Expression] | None = None,
        using: str | Sequence[str] | None = None,
    ) -> Self:
        return self._join(table, "INNER", on, using)

    def inner_join(
        self,
        table: Table,
        on: Expression | Sequence[Expression] | None = None,
        using: str | Sequence[str] | None = None,
    ) -> Self:
        return self._join(table, "INNER", on, using)

    def left_join(
        self,
        table: Table,
        on: Expression | Sequence[Expression] | None = None,
        using: str | Sequence[str] | None = None,
    ) -> Self:
        return self._join(table, "LEFT", on, using)

    def right_join(
        self,
        table: Table,
        on: Expression | Sequence[Expression] | None = None,
        using: str | Sequence[str] | None = None,
    ) -> Self:
        return self._join(table, "RIGHT", on, using)

    def full_join(
        self,
        table: Table,
        on: Expression | Sequence[Expression] | None = None,
        using: str | Sequence[str] | None = None,
    ) -> Self:
        return self._join(table, "FULL", on, using)

    def cross_join(
        self,
        table: Table,
        on: Expression | Sequence[Expression] | None = None,
        using: str | Sequence[str] | None = None,
    ) -> Self:
        return self._join(table, "CROSS", on, using)
