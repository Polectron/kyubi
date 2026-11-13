import pytest

from kyubi.fields import Field, OrderClause
from kyubi.table import table


class TestUpdate:
    def test_update_all_rows_without_where(self, t, sqlite_connection):
        query = t.update(name="updated")
        sqlite_connection.execute("CREATE TABLE test_table (id INTEGER, name TEXT)")
        sqlite_connection.execute("INSERT INTO test_table VALUES (1, 'a'), (2, 'b')")

        assert query.build() == "UPDATE test_table SET name = 'updated'"
        sqlite_connection.execute(query.build())
        assert sqlite_connection.execute(
            "SELECT name FROM test_table ORDER BY id"
        ).fetchall() == [
            ("updated",),
            ("updated",),
        ]

    def test_where_and_multiple_assignments(self, t, sqlite_connection):
        query = t.update(name="O'Brien", age=None).where(t.id == 1)
        sqlite_connection.execute(
            "CREATE TABLE test_table (id INTEGER, name TEXT, age INTEGER)"
        )
        sqlite_connection.execute(
            "INSERT INTO test_table VALUES (1, 'Alice', 18), (2, 'Bob', 20)"
        )

        assert query.build() == (
            "UPDATE test_table SET name = 'O''Brien', age = NULL WHERE id = 1"
        )
        sqlite_connection.execute(query.build())
        assert sqlite_connection.execute(
            "SELECT * FROM test_table ORDER BY id"
        ).fetchall() == [
            (1, "O'Brien", None),
            (2, "Bob", 20),
        ]

    def test_update_expression_uses_original_row(self, t, sqlite_connection):
        query = t.update(age=t.age + 1).where(t.id == 1)
        sqlite_connection.execute("CREATE TABLE test_table (id INTEGER, age INTEGER)")
        sqlite_connection.execute("INSERT INTO test_table VALUES (1, 18), (2, NULL)")

        assert query.build() == "UPDATE test_table SET age = (age + 1) WHERE id = 1"
        sqlite_connection.execute(query.build())
        assert sqlite_connection.execute(
            "SELECT * FROM test_table ORDER BY id"
        ).fetchall() == [
            (1, 19),
            (2, None),
        ]

    def test_assignments_are_evaluated_before_modifying_the_row(
        self, t, sqlite_connection
    ):
        query = t.update(id=t.age, age=t.id)
        sqlite_connection.execute("CREATE TABLE test_table (id INTEGER, age INTEGER)")
        sqlite_connection.execute("INSERT INTO test_table VALUES (1, 20)")

        sqlite_connection.execute(query.build())
        assert sqlite_connection.execute("SELECT * FROM test_table").fetchall() == [
            (20, 1)
        ]

    def test_empty_update_is_rejected(self, t):
        with pytest.raises(ValueError):
            t.update().build()

    def test_where_clauses_are_combined(self, t):
        query = t.update(name="adult").where(t.age >= 18).where(t.id > 0)

        assert query.build() == (
            "UPDATE test_table SET name = 'adult' WHERE age >= 18 AND id > 0"
        )

    def test_alias_qualifies_where_but_not_assignment_target(
        self, t, sqlite_connection
    ):
        users = t.alias("u")
        query = users.update(age=users.age + 1).where(users.id == 1)
        sqlite_connection.execute("CREATE TABLE test_table (id INTEGER, age INTEGER)")
        sqlite_connection.execute("INSERT INTO test_table VALUES (1, 18)")

        assert query.build() == (
            "UPDATE test_table AS u SET age = (u.age + 1) WHERE u.id = 1"
        )
        sqlite_connection.execute(query.build())
        assert sqlite_connection.execute("SELECT age FROM test_table").fetchall() == [
            (19,)
        ]

    @pytest.mark.parametrize("offset", [0, 1])
    def test_offset_requires_limit(self, t, offset):
        with pytest.raises(ValueError):
            t.update(age=18).offset(offset).build()

    def test_optional_limit_and_offset_execute(self, t, sqlite_connection):
        if not sqlite_connection.execute(
            "SELECT sqlite_compileoption_used('ENABLE_UPDATE_DELETE_LIMIT')"
        ).fetchone()[0]:
            pytest.skip("SQLite was built without ENABLE_UPDATE_DELETE_LIMIT")
        sqlite_connection.execute("CREATE TABLE test_table (id INTEGER, age INTEGER)")
        sqlite_connection.execute(
            "INSERT INTO test_table VALUES (1, 0), (2, 0), (3, 0), (4, 0)"
        )
        query = t.update(age=1).order_by(OrderClause(t.id)).limit(2).offset(1)

        sqlite_connection.execute(query.build())
        assert sqlite_connection.execute(
            "SELECT * FROM test_table ORDER BY id"
        ).fetchall() == [
            (1, 0),
            (2, 1),
            (3, 1),
            (4, 0),
        ]

    def test_query_branches_are_independent(self, t):
        original = t.update(name="updated")
        first = original.where(t.id == 1)
        second = original.where(t.id == 2)

        assert original.build() == "UPDATE test_table SET name = 'updated'"
        assert first.build() == "UPDATE test_table SET name = 'updated' WHERE id = 1"
        assert second.build() == (
            "UPDATE test_table SET name = 'updated' WHERE id = 2"
        )
        assert first.build() == "UPDATE test_table SET name = 'updated' WHERE id = 1"
