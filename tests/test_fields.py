import pytest

from kyubi.fields import Field, Literal
from tests.helpers import UserTable


class TestFieldAliases:
    def test_selects_an_aliased_field(self, t):
        query = t.select(t.name.alias("username"))

        assert query.build() == "SELECT name AS username FROM test_table"

    def test_selects_aliased_and_unaliased_fields(self, t):
        query = t.select(t.id, t.name.alias("username"), t.age)

        assert query.build() == ("SELECT id, name AS username, age FROM test_table")

    def test_alias_does_not_change_the_original_field(self, t):
        name = t.name
        aliased_name = name.alias("username")

        assert t.select(name).build() == "SELECT name FROM test_table"
        assert t.select(aliased_name).build() == (
            "SELECT name AS username FROM test_table"
        )


def test_field_build_requires_a_bound_field():
    with pytest.raises(ValueError, match="Unbound field.*name"):
        UserTable.name.build()
    with pytest.raises(ValueError, match="Unbound field.*name"):
        Field("name").alias("label").build()


def test_expression_build_modes_preserve_grouping_and_suppress_nested_aliases(t):
    users = t.alias("u")
    expression = (users.age.alias("ignored") + Literal(1).alias("ignored")).alias(
        "total"
    )

    assert expression.build() == "u.age + 1 AS total"
    assert expression.build(alias=False) == "u.age + 1"
    assert expression._as_operand() == "(u.age + 1)"
    assert expression.build(qualify="never") == "age + 1 AS total"
    assert (t.age + 1).build(qualify="always") == "test_table.age + 1"


def test_qualification_propagates_through_nested_conditions(t):
    expression = (t.age.between(t.id, t.age + 5)) & t.id.is_in(t.age, 1)

    assert expression.build(qualify="always") == (
        "test_table.age BETWEEN test_table.id AND (test_table.age + 5) "
        "AND test_table.id IN (test_table.age, 1)"
    )
