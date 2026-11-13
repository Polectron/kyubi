import pytest

from kyubi.engines.sqlite import SQLite
from kyubi.fields import OrderClause
from kyubi.queries.delete import DeleteQuery
from kyubi.queries.mixins import LimitMixin, OffsetMixin, OrderByMixin, WhereMixin
from kyubi.queries.select import SelectQuery
from kyubi.tabledef import TableDef


@pytest.mark.parametrize("query_type", [SelectQuery, DeleteQuery])
def test_where_mixin_preserves_query_type_and_independent_conditions(t, query_type):
    table_def = TableDef(t._table_name, t._engine, t._alias)
    original = query_type(table_def, [])
    first = original.where(t.id == 1, True)
    second = first.where(t.age >= 18)
    sibling = original.where(t.id == 2)

    assert type(first) is query_type
    assert original._conditions == []
    assert [condition._value(table_def) for condition in first._conditions] == [
        "id = 1",
        "True",
    ]
    assert [condition._value(table_def) for condition in second._conditions] == [
        "id = 1",
        "True",
        "age >= 18",
    ]
    assert [condition._value(table_def) for condition in sibling._conditions] == [
        "id = 2"
    ]


def test_where_mixin_can_be_used_by_another_query(t):
    class OtherQuery(WhereMixin):
        pass

    table_def = TableDef(t._table_name, t._engine, t._alias)
    original = OtherQuery(table_def)
    filtered = original.where(t.id == 1)

    assert isinstance(filtered, OtherQuery)
    assert original._conditions == []
    assert filtered._conditions[0]._value(table_def) == "id = 1"


def test_delete_where_builds_with_sqlite(t):
    table_def = TableDef(t._table_name, SQLite(), t._alias)
    original = DeleteQuery(table_def, [])
    filtered = original.where(t.id == 1).where(t.age >= 18)

    assert original.build() == "DELETE FROM test_table"
    assert filtered.build() == "DELETE FROM test_table WHERE id = 1 AND age >= 18"


@pytest.mark.parametrize("query_type", [SelectQuery, DeleteQuery])
def test_order_limit_offset_keep_query_branches_independent(t, query_type):
    table_def = TableDef(t._table_name, SQLite(), t._alias)
    original = query_type(table_def, [t.id] if query_type is SelectQuery else [])
    ordered = original.order_by(OrderClause(t.id))
    first = ordered.limit(2).offset(1).order_by(OrderClause(t.age, "desc"))
    second = ordered.limit(0).offset(0)
    prefix = (
        "SELECT id FROM test_table"
        if query_type is SelectQuery
        else "DELETE FROM test_table"
    )

    assert type(first) is query_type
    assert original.build() == prefix
    if query_type is SelectQuery:
        assert ordered.build() == f"{prefix} ORDER BY id asc"
    assert first.build() == f"{prefix} ORDER BY id asc, age desc LIMIT 2 OFFSET 1"
    assert second.build() == f"{prefix} ORDER BY id asc LIMIT 0 OFFSET 0"


def test_individual_mixins_can_be_combined_on_another_query(t):
    class OtherQuery(OrderByMixin, LimitMixin, OffsetMixin):
        pass

    table_def = TableDef(t._table_name, t._engine, t._alias)
    original = OtherQuery(table_def)
    modified = original.order_by(OrderClause(t.id)).limit(2).offset(1)

    assert isinstance(modified, OtherQuery)
    assert original._order == []
    assert original._limit is None
    assert original._offset is None
    assert modified._order[0].build(table_def) == "id asc"
    assert modified._limit == 2
    assert modified._offset == 1


@pytest.mark.parametrize("offset", [0, 1])
def test_delete_offset_requires_limit(t, offset):
    table_def = TableDef(t._table_name, SQLite(), t._alias)
    with pytest.raises(ValueError, match="OFFSET requires a LIMIT in SQLite"):
        DeleteQuery(table_def, []).offset(offset).build()


def test_delete_order_requires_limit(t):
    table_def = TableDef(t._table_name, SQLite(), t._alias)
    with pytest.raises(ValueError, match="ORDER BY requires a LIMIT in SQLite DELETE"):
        DeleteQuery(table_def, []).order_by(OrderClause(t.id)).build()


def test_delete_clauses_use_sql_order_and_alias(t):
    users = t.alias("u")
    table_def = TableDef(users._table_name, SQLite(), users._alias)
    query = (
        DeleteQuery(table_def, [])
        .offset(1)
        .order_by(OrderClause(users.id, "desc"))
        .limit(2)
        .where(users.age >= 18)
    )

    assert query.build() == (
        "DELETE FROM test_table AS u WHERE u.age >= 18 "
        "ORDER BY u.id desc LIMIT 2 OFFSET 1"
    )
