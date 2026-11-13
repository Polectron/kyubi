from functools import singledispatchmethod

from kyubi.engines.engine import Engine
from kyubi.queries.delete import DeleteQuery
from kyubi.queries.insert import InsertQuery
from kyubi.queries.mixins import PaginationMixin
from kyubi.queries.query import Query
from kyubi.queries.select import GroupByQuery, SelectQuery
from kyubi.queries.update import UpdateQuery


class SQLite(Engine):
    def __init__(self) -> None:
        super().__init__()

    def _build_pagination(self, query: PaginationMixin) -> str:
        if query._offset is not None and query._limit is None:
            raise ValueError("OFFSET requires a LIMIT in SQLite")

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
        q = "DELETE"
        q += self._build_from(query)
        if query._conditions:
            q += self._build_conditions(query)
        if query._order:
            if query._limit is None:
                raise ValueError("ORDER BY requires a LIMIT in SQLite DELETE")
            q += self._build_order(query)
        q += self._build_pagination(query)
        return q

    @build.register
    def _(self, query: InsertQuery) -> str:
        return self._build_insert(query)


    @build.register
    def _(self, query: UpdateQuery) -> str:
        q = self._build_update(query)
        if query._conditions:
            q += self._build_conditions(query)
        q += self._build_pagination(query)
        return q