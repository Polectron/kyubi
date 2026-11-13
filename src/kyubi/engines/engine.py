from __future__ import annotations

import abc
from functools import singledispatchmethod
from typing import TYPE_CHECKING

from kyubi.queries.select import GroupByQuery, SelectQuery

if TYPE_CHECKING:
    from kyubi.queries.query import Query


class Engine(abc.ABC):
    def _build_select(self, query: SelectQuery) -> str:
        return f"SELECT {', '.join(field.build(query._table_def) for field in query._select_fields)} FROM {query._table_def.table_name}{f' AS {query._table_def.alias}' if query._table_def.alias else ''}"

    def _build_conditions(self, query: SelectQuery) -> str:
        return f" WHERE {' AND '.join(condition._value(query._table_def) for condition in query._conditions)}"

    def _build_order(self, query: SelectQuery) -> str:
        return f" ORDER BY {', '.join(order.build(query._table_def) for order in query._order)}"

    def _build_limit(self, query: SelectQuery) -> str:
        return f" LIMIT {query._limit}"

    def _build_offset(self, query: SelectQuery) -> str:
        return f" OFFSET {query._offset}"

    def _build_group_by(self, query: GroupByQuery) -> str:
        return f" GROUP BY {', '.join(group_by._value(query._table_def) for group_by in query._group_by)}"

    def _build_having(self, query: GroupByQuery) -> str:
        return f" HAVING {' AND '.join(condition._value(query._table_def) for condition in query._having)}"

    @singledispatchmethod
    def build(self, query: Query) -> str:
        raise NotImplementedError

    @build.register
    def _(self, query: SelectQuery) -> str:
        raise NotImplementedError

    @build.register
    def _(self, query: GroupByQuery) -> str:
        raise NotImplementedError
