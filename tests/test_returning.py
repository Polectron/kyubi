
import re

import pytest

from kyubi.engines.postgres import Postgres
from kyubi.engines.sqlite import SQLite
from kyubi.fields import Field
from kyubi.table import table


@pytest.mark.parametrize(
    ("operation", "expected_sql", "returned", "remaining"),
    [
        (
            "insert",
            (
                "INSERT INTO test_table (id, name) VALUES (3, 'Cara'), (4, 'Dan') "
                "RETURNING name, id"
            ),
            [("Cara", 3), ("Dan", 4)],
            [(1, "Alice"), (2, "Bob"), (3, "Cara"), (4, "Dan")],
        ),
        (
            "update",
            "UPDATE test_table SET name = 'updated' WHERE id = 1 RETURNING name, id",
            [("updated", 1)],
            [(1, "updated"), (2, "Bob")],
        ),
        (
            "delete",
            "DELETE FROM test_table WHERE id = 1 RETURNING name, id",
            [("Alice", 1)],
            [(2, "Bob")],
        ),
    ],
)
def test_returning_rows(t, db_connection, operation, expected_sql, returned, remaining):
    db_connection.execute("CREATE TABLE test_table (id INTEGER, name TEXT)")
    db_connection.execute("INSERT INTO test_table VALUES (1, 'Alice'), (2, 'Bob')")

    if operation == "insert":
        original = t.insert({"id": 3, "name": "Cara"}, {"id": 4, "name": "Dan"})
    elif operation == "update":
        original = t.update(name="updated").where(t.id == 1)
    else:
        original = t.delete().where(t.id == 1)

    original_sql = original.build()
    query = original.returning(t.name, t.id)

    assert type(query) is type(original)
    assert original.build() == original_sql
    assert query.build() == expected_sql
    assert sorted(db_connection.execute(query.build()).fetchall()) == sorted(returned)
    assert (
        db_connection.execute("SELECT id, name FROM test_table ORDER BY id").fetchall()
        == remaining
    )


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_returning_no_matching_rows(t, db_connection, operation):
    db_connection.execute("CREATE TABLE test_table (id INTEGER, name TEXT)")
    db_connection.execute("INSERT INTO test_table VALUES (1, 'Alice')")

    if operation == "update":
        query = t.update(name="updated").where(t.id == 2)
    else:
        query = t.delete().where(t.id == 2)

    assert db_connection.execute(query.returning(t.id).build()).fetchall() == []
    assert db_connection.execute("SELECT id, name FROM test_table").fetchall() == [
        (1, "Alice")
    ]


@pytest.mark.parametrize("operation", ["insert", "update", "delete"])
def test_sqlite_returning_aliased_target(t, engine, sqlite_connection, operation):
    if not isinstance(engine, SQLite):
        pytest.skip("SQLite-specific RETURNING behavior")
    sqlite_connection.execute("CREATE TABLE test_table (id INTEGER, name TEXT)")
    sqlite_connection.execute("INSERT INTO test_table VALUES (1, 'Alice')")
    users = t.alias("u")

    if operation == "insert":
        query = users.insert({"id": 2, "name": "Bob"})
        expected = [(2, "Bob")]
    elif operation == "update":
        query = users.update(name="Bob").where(users.id == 1)
        expected = [(1, "Bob")]
    else:
        query = users.delete().where(users.id == 1)
        expected = [(1, "Alice")]

    sql = query.returning(users.id, users.name).build()
    assert sql.endswith(" RETURNING id, name")
    assert sqlite_connection.execute(sql).fetchall() == expected


def test_sqlite_returning_rejects_fields_from_another_table(t, engine):
    if not isinstance(engine, SQLite):
        pytest.skip("SQLite-specific RETURNING behavior")
    users = t.alias("u")
    other = table("other").alias("o")
    with pytest.raises(ValueError, match="RETURNING fields must belong"):
        users.update(name="Bob").returning(other.name).build()


@pytest.mark.parametrize("engine_type", [SQLite, Postgres])
@pytest.mark.parametrize("operation", ["insert", "update", "delete"])
@pytest.mark.parametrize("aliased_target", [False, True])
def test_returning_renders_target_fields(
    t, monkeypatch, engine_type, operation, aliased_target
):
    monkeypatch.setattr(t.Meta, "engine", engine_type())
    target = t.alias("u") if aliased_target else t
    fields = t.alias("u") if aliased_target else t
    if operation == "insert":
        query = target.insert({"id": 1})
    elif operation == "update":
        query = target.update(name="Bob")
    else:
        query = target.delete()

    prefix = "u." if aliased_target and engine_type is Postgres else ""
    sql = query.returning(fields.id, fields.name.alias("label")).build()
    assert sql.endswith(f" RETURNING {prefix}id, {prefix}name AS label")


@pytest.mark.parametrize("engine_type", [SQLite, Postgres])
@pytest.mark.parametrize("operation", ["insert", "update", "delete"])
@pytest.mark.parametrize("aliased_target", [False, True])
@pytest.mark.parametrize("invalid_source", ["other_table", "other_alias", "unbound"])
def test_returning_rejects_invalid_sources(
    t, monkeypatch, engine_type, operation, aliased_target, invalid_source
):
    monkeypatch.setattr(t.Meta, "engine", engine_type())
    target = t.alias("u") if aliased_target else t
    if invalid_source == "other_table":
        invalid_field = table("other").name
        source_table, source_alias = "other", None
    elif invalid_source == "other_alias":
        invalid_field = t.alias("m").name
        source_table, source_alias = "test_table", "m"
    else:
        invalid_field = Field("name")

    if operation == "insert":
        query = target.insert({"id": 1})
    elif operation == "update":
        query = target.update(name="Bob")
    else:
        query = target.delete()

    if invalid_source == "unbound":
        expected = "Unbound field.*name"
    else:
        expected = re.escape(
            f"field 'name' belongs to table {source_table!r} (alias {source_alias!r}); "
            f"expected table 'test_table' (alias {target._alias!r})"
        )
    with pytest.raises(ValueError, match=expected):
        query.returning(target.id, invalid_field).build()
