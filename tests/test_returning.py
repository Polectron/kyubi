import pytest


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
