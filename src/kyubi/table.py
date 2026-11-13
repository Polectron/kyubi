from copy import copy
from typing import Self

from kyubi.engines.engine import Engine
from kyubi.fields import Expression, Field
from kyubi.queries import SelectQuery
from kyubi.queries.delete import DeleteQuery
from kyubi.tabledef import TableDef


def table(name: str) -> "AnonymousTable":
    return AnonymousTable(name)


class Table:
    class Meta:
        table_name: str
        engine: Engine
        anonymous = False

    def __init__(self, alias: str | None = None):
        self._alias = alias

    @property
    def _table_name(self) -> str:
        return self.Meta.table_name

    @property
    def _engine(self) -> Engine:
        return self.Meta.engine

    def alias(self, alias: str) -> Self:
        new_table = copy(self)
        new_table._alias = alias
        return new_table

    def select(self, *args: Expression) -> SelectQuery:
        return SelectQuery(
            self._build_table_def(),
            self._build_fields(list(args)),
        )

    def delete(self, *args: Field) -> DeleteQuery:
        return DeleteQuery(
            self._build_table_def(),
            list(args)
        )

    def _build_table_def(self) -> TableDef:
        return TableDef(
            table_name=self._table_name, engine=self._engine, alias=self._alias
        )

    def _build_fields(self, fields: list[Expression]) -> list[Expression]:
        # TODO: verify field name exists in non anonymous tables
        return fields


class AnonymousTable(Table):
    class Meta(Table.Meta):
        anonymous = True

    def __init__(self, name: str, alias: str | None = None) -> None:
        super().__init__(alias)
        self._name = name

    @property
    def _table_name(self) -> str:
        return self._name

    def __getattr__(self, name: str) -> Field:
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return Field(name)
