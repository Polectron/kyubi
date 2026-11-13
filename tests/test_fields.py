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
