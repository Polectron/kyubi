from collections.abc import Sequence
from copy import deepcopy
from typing import Self

from kyubi.fields import Expression, OrderClause
from kyubi.fields.expression import Operand, as_expression
from kyubi.queries.query import Query
from kyubi.tabledef import TableDef


class SelectQuery(Query):
    def __init__(self, table_def: TableDef, fields: Sequence[Operand] | None = None):
        super().__init__(table_def)
        self._select_fields: list[Expression] = (
            [as_expression(f) for f in fields] if fields else []
        )
        self._conditions: list[Expression] = []
        self._order: list[OrderClause] = []
        self._limit: int | None = None
        self._offset: int | None = None

    def where(self, *args: Operand) -> Self:
        new_query = deepcopy(self)
        new_query._conditions.extend([as_expression(f) for f in args])
        return new_query

    def order_by(self, *args: OrderClause) -> Self:
        new_query = deepcopy(self)
        new_query._order.extend(args)
        return new_query

    def limit(self, limit: int) -> Self:
        new_query = deepcopy(self)
        new_query._limit = limit
        return new_query

    def offset(self, offset: int) -> Self:
        new_query = deepcopy(self)
        new_query._offset = offset
        return new_query

    def group_by(self, *args: Expression) -> "GroupByQuery":
        return GroupByQuery(self, args)


class GroupByQuery(SelectQuery):
    def __init__(self, source: SelectQuery, fields: Sequence[Expression]):
        source = deepcopy(source)
        super().__init__(source._table_def, source._select_fields)
        self._conditions = source._conditions
        self._order = source._order
        self._limit = source._limit
        self._offset = source._offset
        self._group_by = list(fields)
        self._having = []

    def group_by(self, *args: Expression) -> Self:
        new_query = deepcopy(self)
        new_query._group_by.extend(args)
        return new_query

    def having(self, *args: Expression) -> Self:
        new_query = deepcopy(self)
        new_query._having.extend(args)
        return new_query
