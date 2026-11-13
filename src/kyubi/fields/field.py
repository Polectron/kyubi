from kyubi.fields.expression import Expression
from kyubi.tabledef import TableDef


class Field(Expression):
    def __init__(self, name: str, alias: str | None = None):
        super().__init__(alias)
        self._name = name

    def _value(self, table_def: TableDef) -> str:
        qualifier = f"{table_def.alias}." if table_def.alias else ""
        return f"{qualifier}{self._name}"
