from __future__ import annotations

import abc
from functools import singledispatchmethod
from typing import TYPE_CHECKING

from kyubi.fields.expression import as_expression
from kyubi.queries.delete import DeleteQuery
from kyubi.queries.insert import InsertQuery
from kyubi.queries.mixins import LimitMixin, OffsetMixin, OrderByMixin, WhereMixin
from kyubi.queries.select import GroupByQuery, SelectQuery
from kyubi.queries.update import UpdateQuery

if TYPE_CHECKING:
    from kyubi.queries.query import Query


class Engine(abc.ABC):
    def _table_name(self, query: Query) -> str:
        return f"{query._table_def.table_name}{f' AS {query._table_def.alias}' if query._table_def.alias else ''}"

    def _build_select(self, query: SelectQuery) -> str:
        return f"SELECT {', '.join(field.build(query._table_def) for field in query._select_fields)}"

    def _build_from(self, query: Query) -> str:
        return f" FROM {self._table_name(query)}"

    def _build_into(self, query: Query) -> str:
        return f" INTO {self._table_name(query)}"

    def _build_insert(self, query: InsertQuery) -> str:
        keys = query._to_insert[0].keys()
        rows = [
            f"({', '.join(as_expression(row[key])._as_operand(query._table_def) for key in keys)})"
            for row in query._to_insert
        ]
        return f"INSERT{self._build_into(query)} ({', '.join(keys)}) VALUES {', '.join(rows)}"

    def _build_update(self, query: UpdateQuery) -> str:
        updates = [f"{k} = {as_expression(v)._as_operand(query._table_def)}" for k, v in query._to_update.items()]
        q = f"UPDATE {self._table_name(query)} SET {', '.join(updates)}"
        return q

    def _build_conditions(self, query: WhereMixin) -> str:
        return f" WHERE {' AND '.join(condition._value(query._table_def) for condition in query._conditions)}"

    def _build_order(self, query: OrderByMixin) -> str:
        return f" ORDER BY {', '.join(order.build(query._table_def) for order in query._order)}"

    def _build_limit(self, query: LimitMixin) -> str:
        return f" LIMIT {query._limit}"

    def _build_offset(self, query: OffsetMixin) -> str:
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

    @build.register
    def _(self, query: DeleteQuery) -> str:
        raise NotImplementedError

    @build.register
    def _(self, query: InsertQuery) -> str:
        raise NotImplementedError

    @build.register
    def _(self, query: UpdateQuery) -> str:
        raise NotImplementedError
