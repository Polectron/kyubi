import pytest

from kyubi.engines.postgres import Postgres
from kyubi.fields import OrderClause
from kyubi.queries.query import Query
from kyubi.table import AnonymousTable, table
from kyubi.tabledef import TableDef


@pytest.fixture
def postgres_table(monkeypatch):
    monkeypatch.setattr(AnonymousTable.Meta, "engine", Postgres(), raising=False)
    return table("test_table")


def test_postgres_rejects_unsupported_query():
    engine = Postgres()
    query = Query(TableDef(table_name="test_table", engine=engine))

    with pytest.raises(NotImplementedError):
        query.build()


def test_postgres_select_and_group_by_include_aliased_from(postgres_table):
    users = postgres_table.alias("u")

    assert users.select(users.id).where(users.id > 1).build() == (
        "SELECT u.id FROM test_table AS u WHERE u.id > 1"
    )
    assert (
        users.select(users.age)
        .where(users.age >= 18)
        .group_by(users.age)
        .order_by(OrderClause(users.age))
        .offset(1)
        .build()
        == "SELECT u.age FROM test_table AS u WHERE u.age >= 18 "
        "GROUP BY u.age ORDER BY u.age asc OFFSET 1"
    )


def test_postgres_delete_with_and_without_conditions(postgres_table):
    users = postgres_table.alias("u")
    original = users.delete()
    filtered = original.where(users.id == 1).where(users.age >= 18)

    assert original.build() == "DELETE FROM test_table AS u"
    assert filtered.build() == (
        "DELETE FROM test_table AS u WHERE u.id = 1 AND u.age >= 18"
    )


def test_postgres_returning_keeps_target_alias(postgres_table):
    users = postgres_table.alias("u")

    assert users.update(age=20).returning(users.age).build() == (
        "UPDATE test_table AS u SET age = 20 RETURNING u.age"
    )


@pytest.mark.parametrize(
    "option", ["order", "limit", "zero_limit", "offset", "zero_offset"]
)
def test_postgres_delete_rejects_unsupported_options(postgres_table, option):
    query = postgres_table.delete()
    if option == "order":
        query = query.order_by(OrderClause(postgres_table.id))
    elif option == "limit":
        query = query.limit(2)
    elif option == "zero_limit":
        query = query.limit(0)
    elif option == "offset":
        query = query.offset(1)
    else:
        query = query.offset(0)

    with pytest.raises(NotImplementedError, match="DELETE.*ORDER BY.*LIMIT.*OFFSET"):
        query.build()


@pytest.mark.parametrize("option", ["limit", "zero_limit", "offset", "zero_offset"])
def test_postgres_update_rejects_unsupported_options(postgres_table, option):
    query = postgres_table.update(age=18)
    if option == "limit":
        query = query.limit(2)
    elif option == "zero_limit":
        query = query.limit(0)
    elif option == "offset":
        query = query.offset(1)
    else:
        query = query.offset(0)

    with pytest.raises(NotImplementedError, match="UPDATE.*LIMIT.*OFFSET"):
        query.returning(postgres_table.id).build()


@pytest.mark.parametrize("operation", ["insert", "update", "delete"])
def test_postgres_returning_aliased_target(
    postgres_table, request, db_connection, operation
):
    if request.config.getoption("--engine") != "postgres":
        pytest.skip("requires a PostgreSQL test database")

    db_connection.execute("CREATE TABLE test_table (id INTEGER, age INTEGER)")
    db_connection.execute("INSERT INTO test_table VALUES (1, 18)")
    users = postgres_table.alias("u")

    if operation == "insert":
        query = users.insert({"id": 2, "age": 20})
        expected = [(2, 20)]
    elif operation == "update":
        query = users.update(age=19).where(users.id == 1)
        expected = [(1, 19)]
    else:
        query = users.delete().where(users.id == 1)
        expected = [(1, 18)]

    returned = query.returning(users.id).returning(users.age)
    assert " RETURNING u.id, u.age" in returned.build()
    assert db_connection.execute(returned.build()).fetchall() == expected


def test_postgres_queries_execute(postgres_table, request, db_connection):
    if request.config.getoption("--engine") != "postgres":
        pytest.skip("requires a PostgreSQL test database")

    db_connection.execute("CREATE TABLE test_table (id INTEGER, age INTEGER)")
    db_connection.execute("INSERT INTO test_table VALUES (1, 18), (2, 20), (3, 20)")
    users = postgres_table.alias("u")

    query = users.select(users.age).group_by(users.age).order_by(OrderClause(users.age))
    assert db_connection.execute(query.build()).fetchall() == [(18,), (20,)]
    db_connection.execute(users.delete().where(users.age >= 20).build())
    assert db_connection.execute("SELECT id FROM test_table").fetchall() == [(1,)]
