from kyubi.queries.mixins import (
    OrderByMixin,
    PaginationMixin,
    ReturningMixin,
    WhereMixin,
)


class DeleteQuery(WhereMixin, OrderByMixin, PaginationMixin, ReturningMixin):
    pass
