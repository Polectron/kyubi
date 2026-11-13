import pytest

from kyubi.fields import OrderClause


class TestGroupBy:
    def test_group_by_and_having_execute(self, t, sqlite_connection):
        users = t.alias("u")
        query = (
            users.select(users.age, users.name)
            .where(users.id > 0)
            .group_by(users.age)
            .group_by(users.name)
            .having(users.age >= 18)
            .order_by(OrderClause(users.age), OrderClause(users.name))
        )

        sqlite_connection.execute(
            "CREATE TABLE test_table (id INTEGER, age INTEGER, name TEXT)"
        )
        sqlite_connection.executemany(
            "INSERT INTO test_table VALUES (?, ?, ?)",
            [
                (1, 18, "Alice"),
                (2, 18, "Alice"),
                (3, 18, "Bob"),
                (4, 17, "Alice"),
                (5, 20, "Alice"),
                (-1, 30, "Alice"),
            ],
        )
        assert sqlite_connection.execute(query.build()).fetchall() == [
            (18, "Alice"),
            (18, "Bob"),
            (20, "Alice"),
        ]

    def test_group_by_preserves_select_where_and_order_when_executed(
        self, t, sqlite_connection
    ):
        users = t.alias("u")
        query = (
            users.select(users.age)
            .where(users.age >= 18)
            .order_by(OrderClause(users.age, "desc"))
            .group_by(users.age)
        )

        sqlite_connection.execute("CREATE TABLE test_table (age INTEGER)")
        sqlite_connection.executemany(
            "INSERT INTO test_table VALUES (?)", [(18,), (18,), (17,), (20,)]
        )
        assert sqlite_connection.execute(query.build()).fetchall() == [(20,), (18,)]

    def test_groups_by_one_field(self, t):
        query = t.select(t.age).group_by(t.age)

        assert query.build() == "SELECT age FROM test_table GROUP BY age"

    def test_groups_by_multiple_fields_in_order(self, t):
        query = t.select(t.age, t.name).group_by(t.age, t.name)

        assert query.build() == ("SELECT age, name FROM test_table GROUP BY age, name")

    def test_repeated_group_by_appends_fields(self, t):
        query = t.select(t.age, t.name).group_by(t.age).group_by(t.name)

        assert query.build() == ("SELECT age, name FROM test_table GROUP BY age, name")

    def test_group_by_preserves_original_query_and_independent_branches(self, t):
        original = t.select(t.age, t.name)
        grouped = original.group_by(t.age)
        extended = grouped.group_by(t.name)
        other = original.group_by(t.name)

        assert original.build() == "SELECT age, name FROM test_table"
        assert grouped.build() == "SELECT age, name FROM test_table GROUP BY age"
        assert extended.build() == (
            "SELECT age, name FROM test_table GROUP BY age, name"
        )
        assert other.build() == "SELECT age, name FROM test_table GROUP BY name"

    def test_group_by_preserves_select_where_order_and_table_alias(self, t):
        users = t.alias("u")
        original = (
            users.select(users.age, users.name)
            .where(users.age >= 18)
            .order_by(OrderClause(users.name, "desc"))
        )
        grouped = original.group_by(users.age, users.name)

        assert original.build() == (
            "SELECT u.age, u.name FROM test_table AS u WHERE u.age >= 18 "
            "ORDER BY u.name desc"
        )
        assert grouped.build() == (
            "SELECT u.age, u.name FROM test_table AS u WHERE u.age >= 18 "
            "GROUP BY u.age, u.name ORDER BY u.name desc"
        )

    def test_group_by_preserves_limit_state(self, t):
        original = t.select(t.age)
        original._limit = 5

        assert original.group_by(t.age).build() == (
            "SELECT age FROM test_table GROUP BY age LIMIT 5"
        )
        assert original.build() == "SELECT age FROM test_table LIMIT 5"

    def test_group_by_preserves_offset_and_executes(self, t, sqlite_connection):
        original = t.select(t.age).order_by(OrderClause(t.age)).limit(2).offset(1)
        query = original.group_by(t.age)
        sqlite_connection.execute("CREATE TABLE test_table (age INTEGER)")
        sqlite_connection.executemany(
            "INSERT INTO test_table VALUES (?)", [(20,), (18,), (18,), (19,), (21,)]
        )

        assert query.build() == (
            "SELECT age FROM test_table GROUP BY age ORDER BY age asc LIMIT 2 OFFSET 1"
        )
        assert sqlite_connection.execute(query.build()).fetchall() == [(19,), (20,)]
        assert original.build() == (
            "SELECT age FROM test_table ORDER BY age asc LIMIT 2 OFFSET 1"
        )

    @pytest.mark.parametrize("offset", [0, 1])
    def test_grouped_offset_requires_limit_in_sqlite(self, t, offset):
        query = t.select(t.age).offset(offset).group_by(t.age)

        with pytest.raises(ValueError, match="OFFSET requires a LIMIT in SQLite"):
            query.build()

    def test_limit_and_offset_after_group_by(self, t):
        original = t.select(t.age).group_by(t.age)
        paginated = original.offset(1).limit(2)

        assert original.build() == "SELECT age FROM test_table GROUP BY age"
        assert paginated.build() == (
            "SELECT age FROM test_table GROUP BY age LIMIT 2 OFFSET 1"
        )

    def test_grouped_branches_keep_select_state_independently(self, t):
        original = t.select(t.age, t.name).where(t.age >= 18)
        grouped = original.group_by(t.age)
        filtered = grouped.where(t.name == "Alice")
        ordered = grouped.order_by(OrderClause(t.age))

        assert grouped.build() == (
            "SELECT age, name FROM test_table WHERE age >= 18 GROUP BY age"
        )
        assert filtered.build() == (
            "SELECT age, name FROM test_table WHERE age >= 18 AND name = 'Alice' "
            "GROUP BY age"
        )
        assert ordered.build() == (
            "SELECT age, name FROM test_table WHERE age >= 18 "
            "GROUP BY age ORDER BY age asc"
        )

    def test_grouping_qualifies_aliased_table_fields(self, t):
        users = t.alias("u")
        query = users.select(users.age, users.name).group_by(users.age, users.name)

        assert query.build() == (
            "SELECT u.age, u.name FROM test_table AS u GROUP BY u.age, u.name"
        )

    def test_grouping_expression_omits_output_alias(self, t):
        users = t.alias("u")
        age_next_year = (users.age + 1).alias("next_age")
        query = users.select(age_next_year).group_by(age_next_year)

        assert query.build() == (
            "SELECT u.age + 1 AS next_age FROM test_table AS u GROUP BY u.age + 1"
        )

    def test_having_filters_grouped_fields(self, t):
        query = t.select(t.age).group_by(t.age).having(t.age >= 18)

        assert query.build() == (
            "SELECT age FROM test_table GROUP BY age HAVING age >= 18"
        )

    def test_having_qualifies_aliased_table_fields(self, t):
        users = t.alias("u")
        query = users.select(users.age).group_by(users.age).having(users.age >= 18)

        assert query.build() == (
            "SELECT u.age FROM test_table AS u GROUP BY u.age HAVING u.age >= 18"
        )

    def test_having_does_not_change_original_query(self, t):
        original = t.select(t.age).group_by(t.age)
        adults = original.having(t.age >= 18)
        minors = original.having(t.age < 18)

        assert original.build() == "SELECT age FROM test_table GROUP BY age"
        assert adults.build() == (
            "SELECT age FROM test_table GROUP BY age HAVING age >= 18"
        )
        assert minors.build() == (
            "SELECT age FROM test_table GROUP BY age HAVING age < 18"
        )

    def test_clauses_follow_sql_order_regardless_of_call_order(self, t):
        query = (
            t.select(t.age)
            .order_by(OrderClause(t.age, "desc"))
            .group_by(t.age)
            .having(t.age >= 18)
            .where(t.id > 0)
        )

        assert query.build() == (
            "SELECT age FROM test_table WHERE id > 0 "
            "GROUP BY age HAVING age >= 18 ORDER BY age desc"
        )

    def test_build_can_be_repeated(self, t):
        query = t.select(t.age).group_by(t.age).having(t.age >= 18)
        expected = "SELECT age FROM test_table GROUP BY age HAVING age >= 18"

        assert query.build() == expected
        assert query.build() == expected
