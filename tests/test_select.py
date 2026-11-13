import operator
import re
from typing import assert_type

import pytest

from kyubi.fields import (
    Condition,
    Equal,
    Field,
    IsNotNull,
    IsNull,
    Literal,
    NotEqual,
    OrderClause,
)
from kyubi.fields.expression import Greater, GreaterOrEqual, Less, LessOrEqual


class TestSelect:
    def test_select_uses_configured_engine(self, t, engine):
        assert t.select(t.id)._table_def.engine is engine

    def test_selects_one_field(self, t):
        assert t.select(t.id).build() == "SELECT id FROM test_table"

    def test_selects_multiple_fields_in_order(self, t):
        assert t.select(t.age, t.id, t.name).build() == (
            "SELECT age, id, name FROM test_table"
        )

    def test_selects_fields_in_different_ways(self, t):
        assert t.select(t.id, t.name, Field("age")).build() == (
            "SELECT id, name, age FROM test_table"
        )

    def test_preserves_repeated_fields(self, t):
        assert t.select(t.id, t.id).build() == "SELECT id, id FROM test_table"


class TestWhere:
    def test_comparison_return_types(self):
        field = Field("age")

        assert_type(field < 18, Less)
        assert_type(field <= 18, LessOrEqual)
        assert_type(field > 18, Greater)
        assert_type(field >= 18, GreaterOrEqual)
        assert_type(field == 18, Equal | IsNull)
        assert_type(field != 18, NotEqual | IsNotNull)

    def test_comparisons_use_distinct_expression_types(self):
        field = Field("age")

        assert isinstance(field == 18, Equal)
        assert isinstance(field != 18, NotEqual)
        assert isinstance(field == None, IsNull)
        assert isinstance(field != None, IsNotNull)
        assert isinstance(Literal(None) == field, IsNull)
        assert isinstance(Literal(None) != field, IsNotNull)

    def test_explicit_null_comparison_classes(self, t):
        users = t.alias("u")

        assert users.select(
            IsNull(users.age + Literal(1)).alias("missing"),
            IsNotNull(users.name).alias("present"),
        ).build() == (
            "SELECT (u.age + 1) IS NULL AS missing, "
            "u.name IS NOT NULL AS present FROM test_table AS u"
        )

    def test_select_with_condition(self, t):
        query = t.select(t.id, t.name, t.age).where(t.id == 1)
        assert query.build() == ("SELECT id, name, age FROM test_table WHERE id = 1")

    @pytest.mark.parametrize(
        ("operation", "sql_operator"),
        [
            (operator.eq, "="),
            (operator.ne, r"(?:!=|<>)"),
            (operator.gt, ">"),
            (operator.ge, ">="),
            (operator.lt, "<"),
            (operator.le, "<="),
        ],
    )
    def test_comparison_operators(self, t, operation, sql_operator):
        query = t.select(t.id).where(operation(t.age, 18))

        assert re.fullmatch(
            rf"SELECT id FROM test_table WHERE age {sql_operator} 18",
            query.build(),
        )

    @pytest.mark.parametrize(
        ("value", "sql"),
        [
            (0, "0"),
            (-42, "-42"),
            (3.5, "3.5"),
            ("Alice", "'Alice'"),
            ("O'Brien", "'O''Brien'"),
        ],
    )
    def test_renders_literal_values(self, t, value, sql):
        query = t.select(t.id).where(t.name == value)
        assert query.build() == f"SELECT id FROM test_table WHERE name = {sql}"

    def test_select_with_multiple_conditions(self, t):
        query = t.select(t.id).where(
            t.age >= 18,
            t.name == "Alice",
        )
        assert query.build() == (
            "SELECT id FROM test_table WHERE age >= 18 AND name = 'Alice'"
        )

    def test_select_with_null_condition(self, t):
        query = t.select(t.id).where(t.name == None)
        assert query.build() == "SELECT id FROM test_table WHERE name IS NULL"

    def test_select_with_not_null_condition(self, t):
        query = t.select(t.id).where(t.name != None)
        assert query.build() == "SELECT id FROM test_table WHERE name IS NOT NULL"

    @pytest.mark.parametrize(
        ("operation", "sql_operator"),
        [(operator.eq, "IS"), (operator.ne, "IS NOT")],
    )
    def test_explicit_and_reflected_null_comparisons(self, t, operation, sql_operator):
        explicit_null = operation(t.name, Literal(None))
        reflected_null = operation(Literal(None), t.name)
        python_null = operation(None, t.name)

        for condition in (explicit_null, reflected_null, python_null):
            assert t.select(t.id).where(condition).build() == (
                f"SELECT id FROM test_table WHERE name {sql_operator} NULL"
            )

    @pytest.mark.parametrize(
        ("operation", "sql_operator"),
        [
            (operator.eq, "="),
            (operator.ne, "!="),
            (operator.lt, "<"),
            (operator.le, "<="),
        ],
    )
    def test_compares_expressions_and_preserves_grouping(
        self, t, operation, sql_operator
    ):
        users = t.alias("u")
        query = users.select(users.id).where(operation(users.age + users.id, users.id))

        assert query.build() == (
            f"SELECT u.id FROM test_table AS u WHERE (u.age + u.id) {sql_operator} u.id"
        )

    @pytest.mark.parametrize(
        "operation",
        [operator.eq, operator.ne, operator.lt, operator.le, operator.gt, operator.ge],
    )
    def test_rejects_unsupported_comparison_values(self, t, operation):
        with pytest.raises(TypeError, match="Unsupported operand type: list"):
            operation(t.age, [1])

    def test_compares_fields(self, t):
        query = t.select(t.id).where(t.age > t.id)

        assert query.build() == "SELECT id FROM test_table WHERE age > id"

    def test_comparison_qualifies_aliased_fields(self, t):
        users = t.alias("u")
        query = users.select(users.id).where(users.age >= users.id)

        assert query.build() == "SELECT u.id FROM test_table AS u WHERE u.age >= u.id"

    def test_is_in_with_iterable_values(self, t):
        query = t.select(t.id).where(t.name.is_in("Alice", "O'Brien"))

        assert query.build() == (
            "SELECT id FROM test_table WHERE name IN ('Alice', 'O''Brien')"
        )

    def test_between_is_inclusive(self, t):
        query = t.select(t.id).where(t.age.between(18, 65))

        assert query.build() == "SELECT id FROM test_table WHERE age BETWEEN 18 AND 65"

    def test_and_operator(self, t):
        condition = (t.age >= 18) & (t.name == "Alice")
        query = t.select(t.id).where(condition)

        assert re.fullmatch(
            r"SELECT id FROM test_table WHERE \(?\(?age >= 18\)? AND "
            r"\(?name = 'Alice'\)?\)?",
            query.build(),
        )

    def test_or_operator(self, t):
        condition = (t.id == 1) | (t.id == 2)
        query = t.select(t.id).where(condition)

        assert re.fullmatch(
            r"SELECT id FROM test_table WHERE \(?\(?id = 1\)? OR "
            r"\(?id = 2\)?\)?",
            query.build(),
        )

    def test_is_in_and_between_execute_with_table_alias(self, t, sqlite_connection):
        users = t.alias("u")
        query = users.select(users.id).where(
            users.id.is_in(1, 2, 3) & users.age.between(18, 65)
        )
        sql = query.build()

        assert "u.id IN (1, 2, 3)" in sql
        assert "u.age BETWEEN 18 AND 65" in sql
        sqlite_connection.execute("CREATE TABLE test_table (id INTEGER, age INTEGER)")
        sqlite_connection.execute(
            "INSERT INTO test_table VALUES (1, 17), (2, 18), (3, 65), (4, 30)"
        )
        assert sqlite_connection.execute(sql).fetchall() == [(2,), (3,)]

    @pytest.mark.parametrize("group_or_first", [True, False])
    def test_and_or_grouping_executes(self, t, sqlite_connection, group_or_first):
        if group_or_first:
            condition = ((t.id == 1) | (t.id == 2)) & (t.age >= 18)
            expected = [(2,)]
        else:
            condition = (t.id == 1) | ((t.id == 2) & (t.age >= 18))
            expected = [(1,), (2,)]
        query = t.select(t.id).where(condition).order_by(OrderClause(t.id))

        sqlite_connection.execute("CREATE TABLE test_table (id INTEGER, age INTEGER)")
        sqlite_connection.execute(
            "INSERT INTO test_table VALUES (1, 10), (2, 20), (3, 20)"
        )
        assert sqlite_connection.execute(query.build()).fetchall() == expected

    @pytest.mark.parametrize(
        ("condition", "expected"),
        [
            (lambda t: t.age < 18, [(1,)]),
            (lambda t: t.age <= 18, [(1,), (2,)]),
            (lambda t: t.age == 18, [(2,)]),
            (lambda t: t.age != 18, [(1,)]),
            (lambda t: t.age == None, [(3,)]),
            (lambda t: t.age != None, [(1,), (2,)]),
        ],
    )
    def test_comparison_queries_execute(
        self, t, sqlite_connection, condition, expected
    ):
        query = t.select(t.id).where(condition(t)).order_by(OrderClause(t.id))

        sqlite_connection.execute("CREATE TABLE test_table (id INTEGER, age INTEGER)")
        sqlite_connection.execute(
            "INSERT INTO test_table VALUES (1, 10), (2, 18), (3, NULL)"
        )
        assert sqlite_connection.execute(query.build()).fetchall() == expected


class TestOrderBy:
    def test_orders_ascending(self, t):
        query = t.select(t.id, t.name).order_by(OrderClause(t.id, "asc"))
        assert query.build() == "SELECT id, name FROM test_table ORDER BY id asc"

    def test_orders_descending(self, t):
        query = t.select(t.id).order_by(OrderClause(t.age, "desc"))
        assert query.build() == "SELECT id FROM test_table ORDER BY age desc"

    def test_orders_by_multiple_fields(self, t):
        query = t.select(t.id).order_by(
            OrderClause(t.age, "desc"), OrderClause(t.name, "asc")
        )
        assert query.build().replace(", ", ",") == (
            "SELECT id FROM test_table ORDER BY age desc,name asc"
        )


class TestOffset:
    @pytest.mark.parametrize("offset", [0, 2])
    def test_offset_requires_limit_in_sqlite(self, t, offset):
        query = t.select(t.id).offset(offset)

        with pytest.raises(ValueError, match="OFFSET requires a LIMIT in SQLite"):
            query.build()

    @pytest.mark.parametrize(("limit", "offset"), [(2, 0), (2, 1), (0, 1)])
    def test_offset_follows_limit_and_order(self, t, limit, offset):
        query = t.select(t.id).offset(offset).order_by(OrderClause(t.id)).limit(limit)

        assert query.build() == (
            f"SELECT id FROM test_table ORDER BY id asc LIMIT {limit} OFFSET {offset}"
        )

    @pytest.mark.parametrize(
        ("limit", "expected"), [(2, [(2,), (3,)]), (0, []), (-1, [(2,), (3,), (4,)])]
    )
    def test_offset_executes_with_limit(self, t, sqlite_connection, limit, expected):
        query = t.select(t.id).order_by(OrderClause(t.id)).limit(limit).offset(1)
        sqlite_connection.execute("CREATE TABLE test_table (id INTEGER)")
        sqlite_connection.executemany(
            "INSERT INTO test_table VALUES (?)", [(3,), (1,), (4,), (2,)]
        )

        assert sqlite_connection.execute(query.build()).fetchall() == expected

    def test_offset_keeps_query_branches_independent(self, t):
        original = t.select(t.id).limit(3)
        first = original.offset(1)
        second = first.offset(2)

        assert original.build() == "SELECT id FROM test_table LIMIT 3"
        assert first.build() == "SELECT id FROM test_table LIMIT 3 OFFSET 1"
        assert second.build() == "SELECT id FROM test_table LIMIT 3 OFFSET 2"
        assert first.build() == "SELECT id FROM test_table LIMIT 3 OFFSET 1"

    def test_limit_keeps_query_branches_independent(self, t):
        original = t.select(t.id)
        first = original.limit(2)
        second = first.limit(0)

        assert original.build() == "SELECT id FROM test_table"
        assert first.build() == "SELECT id FROM test_table LIMIT 2"
        assert second.build() == "SELECT id FROM test_table LIMIT 0"


class TestQueryComposition:
    def test_where_does_not_change_original_query(self, t):
        original = t.select(t.id)
        filtered = original.where(Condition(t.id, "=", Literal(1)))

        assert original.build() == "SELECT id FROM test_table"
        assert filtered.build() == "SELECT id FROM test_table WHERE id = 1"

    def test_order_by_does_not_change_original_query(self, t):
        original = t.select(t.id)
        ordered = original.order_by(OrderClause(t.id, "asc"))

        assert original.build() == "SELECT id FROM test_table"
        assert ordered.build() == "SELECT id FROM test_table ORDER BY id asc"

    def test_query_branches_are_independent(self, t):
        original = t.select(t.id)
        first = original.where(Condition(t.id, "=", Literal(1)))
        second = original.where(Condition(t.id, "=", Literal(2)))

        assert original.build() == "SELECT id FROM test_table"
        assert first.build() == "SELECT id FROM test_table WHERE id = 1"
        assert second.build() == "SELECT id FROM test_table WHERE id = 2"

    def test_where_and_order_by_use_sql_clause_order(self, t):
        filtered = t.select(t.id).where(Condition(t.age, ">", Literal(18)))
        ordered = filtered.order_by(OrderClause(t.name, "asc"))

        assert filtered.build() == "SELECT id FROM test_table WHERE age > 18"
        assert ordered.build() == (
            "SELECT id FROM test_table WHERE age > 18 ORDER BY name asc"
        )

    def test_order_by_before_where_uses_sql_clause_order(self, t):
        ordered = t.select(t.id).order_by(OrderClause(t.name, "desc"))
        filtered = ordered.where(Condition(t.age, ">", Literal(18)))

        assert ordered.build() == ("SELECT id FROM test_table ORDER BY name desc")
        assert filtered.build() == (
            "SELECT id FROM test_table WHERE age > 18 ORDER BY name desc"
        )

    def test_build_can_be_repeated(self, t):
        query = t.select(t.id).where(Condition(t.id, "=", Literal(1)))

        assert query.build() == "SELECT id FROM test_table WHERE id = 1"
        assert query.build() == "SELECT id FROM test_table WHERE id = 1"
