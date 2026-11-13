from functools import singledispatchmethod

from kyubi.engines.engine import Engine
from kyubi.queries.delete import DeleteQuery
from kyubi.queries.insert import InsertQuery
from kyubi.queries.mixins import PaginationMixin
from kyubi.queries.query import Query
from kyubi.queries.select import GroupByQuery, SelectQuery
from kyubi.queries.update import UpdateQuery


class Postgres(Engine):
    def _build_pagination(self, query: PaginationMixin) -> str:
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
        q += self._build_from(query)
        if query._joins:
            q += self._build_join(query)
        if query._conditions:
            q += self._build_conditions(query)
        if query._order:
            q += self._build_order(query)
        q += self._build_pagination(query)
        return q

    @build.register
    def _(self, query: GroupByQuery) -> str:
        q = self._build_select(query)
        q += self._build_from(query)
        if query._joins:
            q += self._build_join(query)
        if query._conditions:
            q += self._build_conditions(query)
        q += self._build_group_by(query)
        if query._having:
            q += self._build_having(query)
        if query._order:
            q += self._build_order(query)
        q += self._build_pagination(query)
        return q

    @build.register
    def _(self, query: DeleteQuery) -> str:
        if query._order or query._limit is not None or query._offset is not None:
            raise NotImplementedError(
                "PostgreSQL DELETE does not support ORDER BY, LIMIT, or OFFSET"
            )
        q = "DELETE"
        q += self._build_from(query)
        if query._conditions:
            q += self._build_conditions(query)
        if query._returning:
            q += self._build_returning(query)
        return q

    @build.register
    def _(self, query: InsertQuery) -> str:
        q = self._build_insert(query)
        if query._returning:
            q += self._build_returning(query)
        return q

    @build.register
    def _(self, query: UpdateQuery) -> str:
        if query._limit is not None or query._offset is not None:
            raise NotImplementedError(
                "PostgreSQL UPDATE does not support LIMIT or OFFSET"
            )
        q = self._build_update(query)
        if query._conditions:
            q += self._build_conditions(query)
        if query._returning:
            q += self._build_returning(query)
        return q
