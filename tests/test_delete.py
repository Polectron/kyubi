import pytest

from kyubi.engines.postgres import Postgres
from kyubi.fields import OrderClause


class TestDelete:
    def test_delete_all_rows_without_where(self, t, sqlite_connection):
        query = t.delete()
        sqlite_connection.execute("CREATE TABLE test_table (id INTEGER)")
        sqlite_connection.execute("INSERT INTO test_table VALUES (1), (2)")

        assert query.build() == "DELETE FROM test_table"
        sqlite_connection.execute(query.build())
        assert sqlite_connection.execute("SELECT id FROM test_table").fetchall() == []

    def test_delete_where_keeps_false_and_null_rows(self, t, sqlite_connection):
        query = t.delete().where(t.age >= 18)
        sqlite_connection.execute("CREATE TABLE test_table (id INTEGER, age INTEGER)")
        sqlite_connection.execute(
            "INSERT INTO test_table VALUES (1, 18), (2, 17), (3, NULL)"
        )

        assert query.build() == "DELETE FROM test_table WHERE age >= 18"
        sqlite_connection.execute(query.build())
        assert sqlite_connection.execute(
            "SELECT id FROM test_table ORDER BY id"
        ).fetchall() == [
            (2,),
            (3,),
        ]

    def test_multiple_where_clauses_are_combined(self, t):
        query = t.delete().where(t.age >= 18).where(t.name == "Alice")

        assert query.build() == (
            "DELETE FROM test_table WHERE age >= 18 AND name = 'Alice'"
        )

    def test_aliased_target(self, t, sqlite_connection):
        users = t.alias("u")
        query = users.delete().where(users.id == 1)
        sqlite_connection.execute("CREATE TABLE test_table (id INTEGER)")
        sqlite_connection.execute("INSERT INTO test_table VALUES (1), (2)")

        assert query.build() == "DELETE FROM test_table AS u WHERE u.id = 1"
        sqlite_connection.execute(query.build())
        assert sqlite_connection.execute("SELECT id FROM test_table").fetchall() == [
            (2,)
        ]

    def test_optional_order_limit_offset_sql_order(self, t, engine):
        query = (
            t.delete()
            .offset(1)
            .order_by(OrderClause(t.id, "desc"))
            .limit(2)
            .where(t.age >= 18)
        )

        if isinstance(engine, Postgres):
            with pytest.raises(
                NotImplementedError, match="DELETE.*ORDER BY.*LIMIT.*OFFSET"
            ):
                query.build()
            return

        assert query.build() == (
            "DELETE FROM test_table WHERE age >= 18 ORDER BY id desc LIMIT 2 OFFSET 1"
        )

    @pytest.mark.parametrize("offset", [0, 1])
    def test_offset_requires_limit(self, t, offset, engine):
        error = NotImplementedError if isinstance(engine, Postgres) else ValueError
        with pytest.raises(error):
            t.delete().offset(offset).build()

    def test_order_by_requires_limit(self, t, engine):
        error = NotImplementedError if isinstance(engine, Postgres) else ValueError
        with pytest.raises(error):
            t.delete().order_by(OrderClause(t.id)).build()

    def test_optional_limit_and_offset_execute(self, t, sqlite_connection, engine):
        if isinstance(engine, Postgres):
            pytest.skip("PostgreSQL DELETE does not support ORDER BY, LIMIT, or OFFSET")
        if not sqlite_connection.execute(
            "SELECT sqlite_compileoption_used('ENABLE_UPDATE_DELETE_LIMIT')"
        ).fetchone()[0]:
            pytest.skip("SQLite was built without ENABLE_UPDATE_DELETE_LIMIT")
        sqlite_connection.execute("CREATE TABLE test_table (id INTEGER)")
        sqlite_connection.execute("INSERT INTO test_table VALUES (1), (2), (3), (4)")
        query = t.delete().order_by(OrderClause(t.id)).limit(2).offset(1)

        sqlite_connection.execute(query.build())
        assert sqlite_connection.execute(
            "SELECT id FROM test_table ORDER BY id"
        ).fetchall() == [
            (1,),
            (4,),
        ]

    def test_query_branches_are_independent(self, t):
        original = t.delete()
        first = original.where(t.id == 1)
        second = original.where(t.id == 2)

        assert original.build() == "DELETE FROM test_table"
        assert first.build() == "DELETE FROM test_table WHERE id = 1"
        assert second.build() == "DELETE FROM test_table WHERE id = 2"
        assert first.build() == "DELETE FROM test_table WHERE id = 1"
