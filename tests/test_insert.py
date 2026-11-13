import pytest


class TestInsert:
    def test_insert_values_and_escape_literals(self, t, sqlite_connection):
        query = t.insert({"id": 1, "name": "O'Brien", "age": None})

        assert query.build() == (
            "INSERT INTO test_table (id, name, age) VALUES (1, 'O''Brien', NULL)"
        )
        sqlite_connection.execute(
            "CREATE TABLE test_table (id INTEGER, name TEXT, age INTEGER)"
        )
        sqlite_connection.execute(query.build())
        assert sqlite_connection.execute(
            "SELECT id, name, age FROM test_table"
        ).fetchall() == [(1, "O'Brien", None)]

    def test_missing_columns_use_sqlite_defaults(self, t, sqlite_connection):
        query = t.insert({"id": 1})
        sqlite_connection.execute(
            "CREATE TABLE test_table (id INTEGER, name TEXT DEFAULT 'unknown', age INTEGER)"
        )

        assert query.build() == "INSERT INTO test_table (id) VALUES (1)"
        sqlite_connection.execute(query.build())
        assert sqlite_connection.execute("SELECT * FROM test_table").fetchall() == [
            (1, "unknown", None)
        ]

    def test_multiple_rows(self, t, sqlite_connection):
        query = t.insert({"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"})
        sqlite_connection.execute("CREATE TABLE test_table (id INTEGER, name TEXT)")

        assert query.build() == (
            "INSERT INTO test_table (id, name) VALUES (1, 'Alice'), (2, 'Bob')"
        )
        sqlite_connection.execute(query.build())
        assert sqlite_connection.execute(
            "SELECT * FROM test_table ORDER BY id"
        ).fetchall() == [
            (1, "Alice"),
            (2, "Bob"),
        ]

    def test_multiple_rows_match_columns_by_name(self, t, sqlite_connection):
        query = t.insert({"id": 1, "name": "Alice"}, {"name": "Bob", "id": 2})
        sqlite_connection.execute("CREATE TABLE test_table (id INTEGER, name TEXT)")

        sqlite_connection.execute(query.build())
        assert sqlite_connection.execute(
            "SELECT * FROM test_table ORDER BY id"
        ).fetchall() == [
            (1, "Alice"),
            (2, "Bob"),
        ]

    @pytest.mark.parametrize("row", [{"id": 2}, {"id": 2, "name": "Bob", "age": 20}])
    def test_multiple_rows_reject_different_columns(self, t, row):
        with pytest.raises(ValueError):
            t.insert({"id": 1, "name": "Alice"}, row)

    @pytest.mark.parametrize("rows", [(), ({},), ({"id": 1}, {})])
    def test_insert_rejects_empty_rows(self, t, rows):
        with pytest.raises(ValueError):
            t.insert(*rows)

    def test_insert_copies_input_rows(self, t):
        row = {"id": 1}
        query = t.insert(row)
        row["id"] = 2
        assert query.build() == "INSERT INTO test_table (id) VALUES (1)"

    def test_insert_rejects_keyword_arguments(self, t):
        with pytest.raises(TypeError):
            t.insert(id=1)
