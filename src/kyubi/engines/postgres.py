from functools import singledispatchmethod

from kyubi.engines.engine import Engine
from kyubi.queries.query import Query
from kyubi.queries.select import GroupByQuery, SelectQuery


class Postgres(Engine):
    def _build_pagination(self, query: SelectQuery) -> str:
        result = ""
        if query._limit is not None:
            result += self._build_limit(query)
        if query._offset is not None:
            result += self._build_offset(query)
        return result

    @singledispatchmethod
    def build(self, query: Query) -> str:
        raise NotImplementedError

    @build.register
    def _(self, query: SelectQuery) -> str:
        q = self._build_select(query)
        if query._conditions:
            q += self._build_conditions(query)
        if query._order:
            q += self._build_order(query)
        q += self._build_pagination(query)
        return q

    @build.register
    def _(self, query: GroupByQuery) -> str:
        q = self._build_select(query)
        if query._conditions:
            q += self._build_conditions(query)
        q += self._build_group_by(query)
        if query._having:
            q += self._build_having(query)
        if query._order:
            q += self._build_order(query)
        q += self._build_pagination(query)
        return q
