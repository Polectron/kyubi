from kyubi.fields.expression import Operand
from kyubi.queries.mixins import PaginationMixin, WhereMixin
from kyubi.tabledef import TableDef


class UpdateQuery(WhereMixin, PaginationMixin):
    def __init__(self, table_def: TableDef, to_update: dict[str, Operand]):
        super().__init__(table_def)
        if not to_update:
            raise ValueError("UPDATE requires at least one column to be updated")
        self._to_update = to_update