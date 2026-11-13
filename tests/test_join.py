from collections import Counter

import pytest

from kyubi.fields import Field, OrderClause
from kyubi.table import Table, table


@pytest.fixture(params=["anonymous", "declared"])
def join_tables(request, engine):
    if request.param == "anonymous":
        return table("users").alias("u"), table("departments").alias("d")

    class Users(Table):
        class Meta(Table.Meta):
            table_name = "users"

        id = Field("id")
        department_id = Field("department_id")
        name = Field("name")

    class Departments(Table):
        class Meta(Table.Meta):
            table_name = "departments"

        department_id = Field("department_id")
        name = Field("name")

    Users.Meta.engine = engine
    Departments.Meta.engine = engine
    return Users().alias("u"), Departments().alias("d")


@pytest.fixture
def join_data(db_connection):
    db_connection.execute(
        "CREATE TABLE users (id INTEGER, department_id INTEGER, name TEXT)"
    )
    db_connection.execute("CREATE TABLE departments (department_id INTEGER, name TEXT)")
    db_connection.execute(
        "INSERT INTO users VALUES "
        "(1, 10, 'Alice'), (2, 20, 'Bob'), (3, 30, 'Cara'), (4, NULL, 'Dan')"
    )
    db_connection.execute(
        "INSERT INTO departments VALUES "
        "(10, 'Sales'), (20, 'Support'), (40, 'Research')"
    )
    return db_connection


@pytest.mark.parametrize(
    ("method", "sql_join", "expected"),
    [
        ("inner_join", "INNER JOIN", [(1, "Sales"), (2, "Support")]),
        (
            "left_join",
            "LEFT JOIN",
            [(1, "Sales"), (2, "Support"), (3, None), (4, None)],
        ),
        (
            "right_join",
            "RIGHT JOIN",
            [(1, "Sales"), (2, "Support"), (None, "Research")],
        ),
        (
            "full_join",
            "FULL JOIN",
            [(1, "Sales"), (2, "Support"), (3, None), (4, None), (None, "Research")],
        ),
    ],
)
@pytest.mark.parametrize("condition", ["on", "using"])
def test_join_variations_build_and_execute(
    join_tables, join_data, method, sql_join, expected, condition
):
    users, departments = join_tables
    query = users.select(users.id, departments.name)
    if condition == "on":
        query = getattr(query, method)(
            departments, on=users.department_id == departments.department_id
        )
        clause = "ON u.department_id = d.department_id"
    else:
        query = getattr(query, method)(departments, using=("department_id",))
        clause = "USING (department_id)"

    assert query.build() == (
        f"SELECT u.id, d.name FROM users AS u {sql_join} departments AS d {clause}"
    )
    assert Counter(join_data.execute(query.build()).fetchall()) == Counter(expected)


def test_cross_join_builds_and_executes(join_tables, join_data):
    users, departments = join_tables
    query = users.select(users.id, departments.name).cross_join(departments)

    assert query.build() == (
        "SELECT u.id, d.name FROM users AS u CROSS JOIN departments AS d"
    )
    assert Counter(join_data.execute(query.build()).fetchall()) == Counter(
        (user_id, name)
        for user_id in (1, 2, 3, 4)
        for name in ("Sales", "Support", "Research")
    )


def test_join_on_multiple_conditions(join_tables, join_data):
    users, departments = join_tables
    query = users.select(users.id, departments.name).inner_join(
        departments,
        on=(users.department_id == departments.department_id) & (users.id > 1),
    )

    assert query.build() in {
        (
            "SELECT u.id, d.name FROM users AS u INNER JOIN departments AS d "
            "ON (u.department_id = d.department_id AND u.id > 1)"
        ),
        (
            "SELECT u.id, d.name FROM users AS u INNER JOIN departments AS d "
            "ON (u.department_id = d.department_id) AND (u.id > 1)"
        ),
        (
            "SELECT u.id, d.name FROM users AS u INNER JOIN departments AS d "
            "ON ((u.department_id = d.department_id) AND (u.id > 1))"
        ),
    }
    assert join_data.execute(query.build()).fetchall() == [(2, "Support")]


def test_join_unaliased_tables_qualifies_fields(engine, join_data):
    users = table("users")
    departments = table("departments")
    query = users.select(users.id, departments.name).inner_join(
        departments, on=users.department_id == departments.department_id
    )

    assert query.build() == (
        "SELECT users.id, departments.name FROM users INNER JOIN departments "
        "ON users.department_id = departments.department_id"
    )
    assert Counter(join_data.execute(query.build()).fetchall()) == Counter(
        [(1, "Sales"), (2, "Support")]
    )


@pytest.mark.parametrize(
    ("aliased_table", "expected_sql"),
    [
        (
            "users",
            (
                "SELECT u.id, departments.name FROM users AS u INNER JOIN departments "
                "ON u.department_id = departments.department_id"
            ),
        ),
        (
            "departments",
            (
                "SELECT users.id, d.name FROM users INNER JOIN departments AS d "
                "ON users.department_id = d.department_id"
            ),
        ),
    ],
)
def test_join_mixed_aliased_and_unaliased_tables(
    engine, join_data, aliased_table, expected_sql
):
    users = table("users")
    departments = table("departments")
    if aliased_table == "users":
        users = users.alias("u")
    else:
        departments = departments.alias("d")
    query = users.select(users.id, departments.name).inner_join(
        departments, on=users.department_id == departments.department_id
    )

    assert query.build() == expected_sql
    assert Counter(join_data.execute(query.build()).fetchall()) == Counter(
        [(1, "Sales"), (2, "Support")]
    )


def test_join_using_multiple_columns(join_tables, join_data):
    users, departments = join_tables
    join_data.execute("INSERT INTO departments VALUES (10, 'Alice')")
    query = users.select(users.id, departments.name).inner_join(
        departments, using=("department_id", "name")
    )

    assert query.build() == (
        "SELECT u.id, d.name FROM users AS u INNER JOIN departments AS d "
        "USING (department_id, name)"
    )
    assert join_data.execute(query.build()).fetchall() == [(1, "Alice")]


def test_join_clauses_compose_with_filter_group_order_and_pagination(
    join_tables, join_data
):
    users, departments = join_tables
    query = (
        users.select(departments.name)
        .inner_join(departments, on=users.department_id == departments.department_id)
        .where(users.id > 0)
        .group_by(departments.name)
        .having(departments.name != "Sales")
        .order_by(OrderClause(departments.name))
        .limit(1)
        .offset(0)
    )

    assert query.build() == (
        "SELECT d.name FROM users AS u INNER JOIN departments AS d "
        "ON u.department_id = d.department_id WHERE u.id > 0 "
        "GROUP BY d.name HAVING d.name != 'Sales' "
        "ORDER BY d.name asc LIMIT 1 OFFSET 0"
    )
    assert join_data.execute(query.build()).fetchall() == [("Support",)]


def test_chained_joins_keep_each_table_alias(join_tables, join_data):
    users, departments = join_tables
    managers = users.alias("m")
    query = (
        users.select(users.id, departments.name, managers.name)
        .inner_join(departments, on=users.department_id == departments.department_id)
        .left_join(managers, on=users.department_id == managers.department_id)
    )

    assert query.build() == (
        "SELECT u.id, d.name, m.name FROM users AS u "
        "INNER JOIN departments AS d ON u.department_id = d.department_id "
        "LEFT JOIN users AS m ON u.department_id = m.department_id"
    )
    assert Counter(join_data.execute(query.build()).fetchall()) == Counter(
        [(1, "Sales", "Alice"), (2, "Support", "Bob")]
    )


def test_join_preserves_original_query_and_independent_branches(join_tables):
    users, departments = join_tables
    original = users.select(users.id)
    inner = original.inner_join(
        departments, on=users.department_id == departments.department_id
    )
    left = original.left_join(departments, using=("department_id",))

    assert original.build() == "SELECT u.id FROM users AS u"
    assert inner.build() == (
        "SELECT u.id FROM users AS u INNER JOIN departments AS d "
        "ON u.department_id = d.department_id"
    )
    assert left.build() == (
        "SELECT u.id FROM users AS u LEFT JOIN departments AS d USING (department_id)"
    )
