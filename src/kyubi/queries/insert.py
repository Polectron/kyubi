from kyubi.fields.expression import Operand
from kyubi.queries import Query
from kyubi.tabledef import TableDef


class InsertQuery(Query):
    def __init__(self, table_def: TableDef, values: list[dict[str, Operand]]):
        super().__init__(table_def)
        if not values or not values[0]:
            raise ValueError("INSERT requires at least one row with columns")
        keys = values[0].keys()
        if any(row.keys() != keys for row in values[1:]):
            raise ValueError("All INSERT rows must have the same columns")
        self._to_insert = [row.copy() for row in values]
