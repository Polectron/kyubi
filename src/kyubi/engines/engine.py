from __future__ import annotations

import abc
from functools import singledispatchmethod
from typing import TYPE_CHECKING

from kyubi.fields.expression import Qualification, as_expression
from kyubi.queries.delete import DeleteQuery
from kyubi.queries.insert import InsertQuery
from kyubi.queries.mixins import (
    JoinMixin,
    LimitMixin,
    OffsetMixin,
    OrderByMixin,
    ReturningMixin,
    WhereMixin,
)
from kyubi.queries.select import GroupByQuery, SelectQuery
from kyubi.queries.update import UpdateQuery
from kyubi.tabledef import TableDef

if TYPE_CHECKING:
    from kyubi.queries.query import Query


class Engine(abc.ABC):
    def _qualification(self, query: Query) -> Qualification:
        if isinstance(query, JoinMixin) and query._joins:
            return "always"
        return "alias"

    def _table_name(self, table_def: TableDef) -> str:
        return f"{table_def.table_name}{f' AS {table_def.alias}' if table_def.alias else ''}"

    def _build_select(self, query: SelectQuery) -> str:
        qualify = self._qualification(query)
        return f"SELECT {', '.join(field.build(qualify=qualify) for field in query._select_fields)}"

    def _build_from(self, query: Query) -> str:
        return f" FROM {self._table_name(query._table_def)}"

    def _build_into(self, query: Query) -> str:
        return f" INTO {self._table_name(query._table_def)}"

    def _build_insert(self, query: InsertQuery) -> str:
        keys = query._to_insert[0].keys()
        rows = [
            f"({', '.join(as_expression(row[key])._as_operand() for key in keys)})"
            for row in query._to_insert
        ]
        return f"INSERT{self._build_into(query)} ({', '.join(keys)}) VALUES {', '.join(rows)}"

    def _build_update(self, query: UpdateQuery) -> str:
        updates = [
            f"{k} = {as_expression(v)._as_operand()}"
            for k, v in query._to_update.items()
        ]
        q = f"UPDATE {self._table_name(query._table_def)} SET {', '.join(updates)}"
        return q

    def _build_join(self, query: JoinMixin) -> str:
        joins = []
        for join in query._joins:
            sub_query = f" {join.join_type} JOIN {self._table_name(join.table_def)}"
            if join.on:
                if len(join.on) == 1:
                    conditions = join.on[0].build(alias=False, qualify="always")
                else:
                    conditions = " AND ".join(
                        condition._as_operand(qualify="always") for condition in join.on
                    )
                sub_query += f" ON {conditions}"
            if join.using:
                sub_query += f" USING ({', '.join(join.using)})"
            joins.append(sub_query)
        return "".join(joins)

    def _build_conditions(self, query: WhereMixin) -> str:
        qualify = self._qualification(query)
        return f" WHERE {' AND '.join(condition.build(alias=False, qualify=qualify) for condition in query._conditions)}"

    def _build_order(self, query: OrderByMixin) -> str:
        qualify = self._qualification(query)
        return f" ORDER BY {', '.join(order.build(qualify=qualify) for order in query._order)}"

    def _build_limit(self, query: LimitMixin) -> str:
        return f" LIMIT {query._limit}"

    def _build_offset(self, query: OffsetMixin) -> str:
        return f" OFFSET {query._offset}"

    def _build_group_by(self, query: GroupByQuery) -> str:
        qualify = self._qualification(query)
        return f" GROUP BY {', '.join(group_by.build(alias=False, qualify=qualify) for group_by in query._group_by)}"

    def _build_having(self, query: GroupByQuery) -> str:
        qualify = self._qualification(query)
        return f" HAVING {' AND '.join(condition.build(alias=False, qualify=qualify) for condition in query._having)}"

    def _build_returning(
        self, query: ReturningMixin, *, qualify: Qualification = "alias"
    ) -> str:
        query._validate_returning()
        return f" RETURNING {', '.join(field.build(qualify=qualify) for field in query._returning)}"

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
