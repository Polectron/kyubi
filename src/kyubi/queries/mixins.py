from copy import deepcopy
from typing import Self

from kyubi.fields import Expression, OrderClause
from kyubi.fields.expression import Operand, as_expression
from kyubi.queries.query import Query
from kyubi.tabledef import TableDef


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
