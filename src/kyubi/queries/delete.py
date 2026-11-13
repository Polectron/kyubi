from kyubi.fields import Field
from kyubi.queries.mixins import (
    OrderByMixin,
    PaginationMixin,
    ReturningMixin,
    WhereMixin,
)
from kyubi.tabledef import TableDef


class DeleteQuery(WhereMixin, OrderByMixin, PaginationMixin, ReturningMixin):
    def __init__(self, table_def: TableDef, fields: list[Field]):
        super().__init__(table_def)
        self._delete: list[Field] = fields
