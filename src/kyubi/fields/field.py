from copy import copy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, overload

from kyubi.fields.expression import Expression, Qualification

if TYPE_CHECKING:
    from kyubi.table import Table
    from kyubi.tabledef import TableDef


@dataclass(frozen=True)
class _FieldSource:
    table_name: str
    alias: str | None


class Field(Expression):
    def __init__(self, name: str, alias: str | None = None):
        super().__init__(alias)
        self._name = name
        self._source: _FieldSource | None = None

    @overload
    def __get__(self, instance: None, owner: type) -> Self: ...

    @overload
    def __get__(self, instance: "Table", owner: type | None = None) -> Self: ...

    def __get__(self, instance: "Table | None", owner: type | None = None) -> Self:
        if instance is None:
            return self
        return self._bind(instance._table_name, instance._alias)

    def _bind(self, table_name: str, alias: str | None) -> Self:
        field = copy(self)
        field._source = _FieldSource(table_name, alias)
        return field

    def _bound_source(self) -> _FieldSource:
        if self._source is None:
            raise ValueError(f"Unbound field {self._name!r}, access it through a table")
        return self._source

    def _validate_source(self, target: "TableDef") -> None:
        source = self._bound_source()
        if source.table_name != target.table_name or source.alias != target.alias:
            raise ValueError(
                "RETURNING fields must belong to the target table: "
                f"field {self._name!r} belongs to table {source.table_name!r} "
                f"(alias {source.alias!r}); expected table {target.table_name!r} "
                f"(alias {target.alias!r})"
            )

    def build(self, *, alias: bool = True, qualify: Qualification = "alias") -> str:
        source = self._bound_source()
        source_name = source.alias if qualify != "never" else None
        if qualify == "always" and not source_name:
            source_name = source.table_name
        qualifier = f"{source_name}." if source_name else ""
        return f"{qualifier}{self._name}{self._build_alias() if alias else ''}"
