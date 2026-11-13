import operator
import re
from typing import assert_type

import pytest

from kyubi.fields import (
    Addition,
    Condition,
    Division,
    Field,
    Literal,
    Multiplication,
    OrderClause,
    Subtraction,
)
from kyubi.fields.expression import (
    Equal,
    Greater,
    GreaterOrEqual,
    Less,
    LessOrEqual,
    NotEqual,
)


class TestFieldOperations:
    def test_native_arithmetic_executes_with_correct_operand_order(
        self, t, sqlite_connection
    ):
        users = t.alias("u")
        query = users.select(
            users.age + 1,
            1 + users.age,
            users.age - 1,
            20 - users.age,
            users.age * 2,
            2 * users.age,
            users.age / 2,
            20 / users.age,
        )

        sqlite_connection.execute("CREATE TABLE test_table (age INTEGER)")
        sqlite_connection.execute("INSERT INTO test_table VALUES (10)")
        assert sqlite_connection.execute(query.build()).fetchall() == [
            (11, 11, 9, 10, 20, 20, 5, 2)
        ]

    @pytest.mark.parametrize(
        ("expression_class", "sql_operator"),
        [
            (Addition, "+"),
            (Subtraction, "-"),
            (Multiplication, "*"),
            (Division, "/"),
            (Less, "<"),
            (LessOrEqual, "<="),
            (Equal, "="),
            (NotEqual, "!="),
            (Greater, ">"),
            (GreaterOrEqual, ">="),
        ],
    )
    @pytest.mark.parametrize("native_left", [False, True])
    def test_binary_constructor_accepts_native_operands(
        self, t, expression_class, sql_operator, native_left
    ):
        users = t.alias("u")
        left, right = (2, users.age) if native_left else (users.age, 2)
        expected_left, expected_right = (
            ("2", "u.age") if native_left else ("u.age", "2")
        )

        assert users.select(expression_class(left, right, alias="result")).build() == (
            f"SELECT {expected_left} {sql_operator} {expected_right} AS result "
            "FROM test_table AS u"
        )

    @pytest.mark.parametrize("native_left", [False, True])
    def test_binary_constructor_rejects_unsupported_operands(self, t, native_left):
        left, right = ([], t.age) if native_left else (t.age, [])
        with pytest.raises(TypeError, match="Unsupported operand type: list"):
            Addition(left, right)  # type: ignore[arg-type]

    def test_native_arithmetic_return_types(self):
        field = Field("age")

        assert_type(field + 1, Addition)
        assert_type(1 + field, Addition)
        assert_type(field - 1, Subtraction)
        assert_type(1 - field, Subtraction)
        assert_type(field * 1, Multiplication)
        assert_type(1 * field, Multiplication)
        assert_type(field / 1, Division)
        assert_type(1 / field, Division)

    @pytest.mark.parametrize(
        ("operation", "sql_operator"),
        [
            (operator.add, "+"),
            (operator.sub, "-"),
            (operator.mul, "*"),
            (operator.truediv, "/"),
        ],
    )
    @pytest.mark.parametrize(
        ("value", "sql_value"),
        [
            (1, "1"),
            (1.5, "1.5"),
            (True, "True"),
            (None, "NULL"),
            ("O'Brien", "'O''Brien'"),
        ],
    )
    @pytest.mark.parametrize("reflected", [False, True])
    def test_arithmetic_with_native_values(
        self, t, operation, sql_operator, value, sql_value, reflected
    ):
        users = t.alias("u")
        expression = (
            operation(value, users.age) if reflected else operation(users.age, value)
        )
        left, right = (sql_value, "u.age") if reflected else ("u.age", sql_value)

        assert users.select(expression.alias("result")).build() == (
            f"SELECT {left} {sql_operator} {right} AS result FROM test_table AS u"
        )

    def test_native_arithmetic_preserves_grouping_and_field_aliases(self, t):
        users = t.alias("u")
        expression = 10 - (users.age.alias("ignored") + 2)

        assert users.select(expression).build() == (
            "SELECT 10 - (u.age + 2) FROM test_table AS u"
        )

    @pytest.mark.parametrize(
        "operation", [operator.add, operator.sub, operator.mul, operator.truediv]
    )
    def test_arithmetic_rejects_unsupported_values_immediately(self, t, operation):
        with pytest.raises(TypeError, match="Unsupported operand type: list"):
            operation(t.age, [])

    @pytest.mark.parametrize(
        "method", ["__radd__", "__rsub__", "__rmul__", "__rtruediv__"]
    )
    def test_reflected_arithmetic_rejects_unsupported_values(self, t, method):
        with pytest.raises(TypeError, match="Unsupported operand type: list"):
            getattr(t.age, method)([])

    @pytest.mark.parametrize(
        ("operation", "operator"),
        [
            (lambda a, b: a + b, "+"),
            (lambda a, b: a - b, "-"),
            (lambda a, b: a * b, "*"),
            (lambda a, b: a / b, "/"),
        ],
    )
    def test_selects_arithmetic_between_fields(self, t, operation, operator):
        query = t.select(operation(t.id, t.age))
        expression = rf"id\s*{re.escape(operator)}\s*age"

        assert re.fullmatch(
            rf"SELECT (?:{expression}|\({expression}\)) FROM test_table",
            query.build(),
        )

    def test_preserves_grouping_of_operations(self, t):
        query = t.select((t.id + t.age) * t.id)
        expression = r"\(id\s*\+\s*age\)\s*\*\s*id"

        assert re.fullmatch(
            rf"SELECT (?:{expression}|\({expression}\)) FROM test_table",
            query.build(),
        )

    def test_aliases_an_arithmetic_expression(self, t):
        query = t.select((t.id + t.age).alias("total"))
        expression = r"id\s*\+\s*age"

        assert re.fullmatch(
            rf"SELECT (?:{expression}|\({expression}\)) AS total FROM test_table",
            query.build(),
        )

    def test_operates_on_fields_from_an_aliased_table(self, t):
        users = t.alias("u")
        query = users.select(users.id + users.age)
        expression = r"u\.id\s*\+\s*u\.age"

        assert re.fullmatch(
            rf"SELECT (?:{expression}|\({expression}\)) FROM test_table AS u",
            query.build(),
        )

    def test_nested_expressions_keep_grouping_and_table_alias(self, t):
        users = t.alias("u")
        query = users.select(
            ((users.id + users.age) * (users.age - users.id)).alias("total")
        )

        assert query.build() == (
            "SELECT (u.id + u.age) * (u.age - u.id) AS total FROM test_table AS u"
        )

    def test_right_nested_subtraction_keeps_grouping(self, t):
        query = t.select(t.id - (t.age - t.id))

        assert query.build() == "SELECT id - (age - id) FROM test_table"

    def test_literal_operands_and_literal_selection_are_not_qualified(self, t):
        users = t.alias("u")
        query = users.select((users.age + Literal(1)).alias("next_age"), Literal("x"))

        assert query.build() == (
            "SELECT u.age + 1 AS next_age, 'x' FROM test_table AS u"
        )

    def test_operand_aliases_are_not_rendered_inside_expression(self, t):
        query = t.select((t.id.alias("identifier") + t.age).alias("total"))

        assert query.build() == "SELECT id + age AS total FROM test_table"

    def test_literal_can_be_the_left_operand(self, t):
        users = t.alias("u")

        assert users.select(Literal(100) - users.age).build() == (
            "SELECT 100 - u.age FROM test_table AS u"
        )

    def test_expression_alias_does_not_change_original(self, t):
        expression = t.id + t.age

        assert t.select(expression.alias("total"), expression).build() == (
            "SELECT id + age AS total, id + age FROM test_table"
        )

    def test_expression_in_condition_and_order(self, t):
        users = t.alias("u")
        expression = (users.age + Literal(1)).alias("next_age")
        query = (
            users.select(users.id)
            .where(Condition(expression, ">", Literal(18)))
            .order_by(OrderClause(expression, "desc"))
        )

        assert query.build() == (
            "SELECT u.id FROM test_table AS u WHERE (u.age + 1) > 18 "
            "ORDER BY u.age + 1 desc"
        )


class TestUnaryOperations:
    def test_unary_expressions_execute_with_correct_grouping(
        self, t, sqlite_connection
    ):
        users = t.alias("u")
        negative_id = -users.id
        query = users.select(-(users.id + users.age), -Literal(-1), -negative_id).where(
            Condition(users.age, ">", Literal(18)).not_()
        )

        sqlite_connection.execute("CREATE TABLE test_table (id INTEGER, age INTEGER)")
        sqlite_connection.execute("INSERT INTO test_table VALUES (2, 10), (3, 20)")
        assert sqlite_connection.execute(query.build()).fetchall() == [(-12, 1, 2)]

    def test_numeric_unary_operations_with_table_and_output_aliases(self, t):
        users = t.alias("u")

        assert users.select((-users.age).alias("negative"), +users.id).build() == (
            "SELECT -u.age AS negative, +u.id FROM test_table AS u"
        )

    def test_unary_operation_groups_binary_operand(self, t):
        assert t.select(-(t.id + t.age)).build() == (
            "SELECT -(id + age) FROM test_table"
        )

    def test_binary_operation_groups_unary_operand(self, t):
        assert t.select(t.id - -t.age).build() == ("SELECT id - (-age) FROM test_table")

    def test_nested_unary_operations_do_not_form_sql_comment(self, t):
        negative = -t.age
        assert t.select(-negative, -Literal(-1), +Literal(-1)).build() == (
            "SELECT -(-age), -(-1), +(-1) FROM test_table"
        )

    def test_boolean_not_of_field_and_condition(self, t):
        users = t.alias("u")
        query = users.select(users.id, users.name.not_().alias("inverted")).where(
            Condition(users.age, ">", Literal(18)).not_()
        )

        assert query.build() == (
            "SELECT u.id, NOT u.name AS inverted FROM test_table AS u "
            "WHERE NOT (u.age > 18)"
        )

    def test_boolean_not_as_comparison_operand_is_grouped(self, t):
        query = t.select(t.id).where(Condition(t.name.not_(), "=", Literal(False)))

        assert query.build() == ("SELECT id FROM test_table WHERE (NOT name) = False")

    def test_unary_operand_alias_is_not_rendered_and_original_is_unchanged(self, t):
        field = t.age.alias("age_alias")
        expression = -field

        assert t.select(expression.alias("negative"), expression, field).build() == (
            "SELECT -age AS negative, -age, age AS age_alias FROM test_table"
        )

    def test_unary_expression_in_order_and_condition(self, t):
        users = t.alias("u")
        negative = -users.age
        query = (
            users.select(users.id)
            .where(Condition(negative, "<", Literal(0)))
            .order_by(OrderClause(negative, "desc"))
        )

        assert query.build() == (
            "SELECT u.id FROM test_table AS u WHERE (-u.age) < 0 ORDER BY -u.age desc"
        )

    def test_nested_not_and_condition_aliases(self, t):
        condition = Condition(t.age, ">", Literal(18)).alias("adult")
        query = t.select(condition.not_().not_()).where(
            condition.not_().alias("ignored")
        )

        assert query.build() == (
            "SELECT NOT (NOT (age > 18)) FROM test_table WHERE NOT (age > 18)"
        )
