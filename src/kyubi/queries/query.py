import abc

from kyubi.tabledef import TableDef


class Query(abc.ABC):
    def __init__(self, table_def: TableDef):
        self._table_def = table_def

    def build(self) -> str:
        return self._table_def.engine.build(self)
