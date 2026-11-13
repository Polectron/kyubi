from typing import assert_type

import pytest

from kyubi.table import AnonymousTable, table
from tests.helpers import UserTable


@pytest.mark.usefixtures("engine")
class TestTableAliases:
    def test_selects_a_field_from_an_aliased_table(self, t):
        users = t.alias("u")

        assert users.select(users.id).build() == ("SELECT u.id FROM test_table AS u")

    def test_aliases_table_and_field_together(self, t):
        users = t.alias("u")

        assert users.select(users.name.alias("username")).build() == (
            "SELECT u.name AS username FROM test_table AS u"
        )

    def test_alias_does_not_change_the_original_table(self, t):
        users = t.alias("u")

        assert t.select(t.id).build() == "SELECT id FROM test_table"
        assert users.select(users.id).build() == ("SELECT u.id FROM test_table AS u")

    def test_aliases_are_independent_and_queries_keep_their_alias(self, t):
        users = t.alias("u")
        query = users.select(users.id)
        managers = users.alias("m")

        assert query.build() == "SELECT u.id FROM test_table AS u"
        assert users.select(users.id).build() == "SELECT u.id FROM test_table AS u"
        assert (
            managers.select(managers.id).build() == "SELECT m.id FROM test_table AS m"
        )
        assert t.select(t.id).build() == "SELECT id FROM test_table"

    def test_alias_preserves_declared_table_type(self):
        users = UserTable()
        aliased = assert_type(users.alias("u"), UserTable)

        assert isinstance(aliased, UserTable)
        assert aliased is not users

    def test_alias_preserves_anonymous_table_type_and_name(self):
        users = table("users")
        aliased = assert_type(users.alias("u"), AnonymousTable)

        assert type(aliased) is type(users)
        assert aliased.select(aliased.id).build() == "SELECT u.id FROM users AS u"


@pytest.mark.usefixtures("engine")
class TestAnonymousTables:
    def test_multiple_tables_keep_their_own_names(self):
        users = table("users")
        users_query = users.select(users.id)
        orders = table("orders")

        assert users_query.build() == "SELECT id FROM users"
        assert users.select(users.id).build() == "SELECT id FROM users"
        assert orders.select(orders.id).build() == "SELECT id FROM orders"

    def test_dynamic_fields_use_their_attribute_names(self):
        products = table("products")

        assert products.select(products.sku, products.price).build() == (
            "SELECT sku, price FROM products"
        )
