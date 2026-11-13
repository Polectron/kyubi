# kyubi

A python SQL query builder

[!WARNING]
**Disclaimer:** This project is not intended for production use and is provided for educational purposes only. It in no way tries to provide a fully-featured or secure SQL query builder. Use at your own risk.

## Engines

Set a table's `Meta.engine` to `kyubi.engines.sqlite.SQLite()` or
`kyubi.engines.postgres.Postgres()` to generate SQL for that database.

## Query examples

Define a table and its fields, then call `build()` to generate a SQL string.
These examples use PostgreSQL; replace `Postgres()` with `SQLite()` to generate
SQLite SQL.

```python
from kyubi.engines.postgres import Postgres
from kyubi.fields import Field, OrderClause
from kyubi.table import Table


class Users(Table):
    class Meta(Table.Meta):
        table_name = "users"
        engine = Postgres()

    id = Field("id")
    name = Field("name")
    age = Field("age")


users = Users()
```

### Select, filter, and paginate

```python
query = (
    users.select(users.id, users.name)
    .where(users.age >= 18)
    .order_by(OrderClause(users.name, "asc"))
    .limit(10)
    .offset(20)
)
print(query.build())
# SELECT id, name FROM users WHERE age >= 18 ORDER BY name asc LIMIT 10 OFFSET 20
```

Multiple conditions passed to `where()`, or added by repeated calls, are
combined with `AND`. Queries can also be grouped:

```python
query = (
    users.select(users.age)
    .group_by(users.age)
    .having(users.age >= 18)
    .order_by(OrderClause(users.age))
)
print(query.build())
# SELECT age FROM users GROUP BY age HAVING age >= 18 ORDER BY age asc
```

### Insert, update, and delete

```python
query = users.insert(
    {"id": 1, "name": "Alice", "age": 20},
    {"id": 2, "name": "Bob", "age": 25},
).returning(users.id)
print(query.build())
# INSERT INTO users (id, name, age) VALUES (1, 'Alice', 20), (2, 'Bob', 25) RETURNING id

query = users.update(age=users.age + 1).where(users.id == 1).returning(users.age)
print(query.build())
# UPDATE users SET age = (age + 1) WHERE id = 1 RETURNING age

query = users.delete().where(users.id == 2).returning(users.id)
print(query.build())
# DELETE FROM users WHERE id = 2 RETURNING id
```

`build()` does not connect to a database or execute the query. Execute the
result with your database driver and manage the connection and transaction
there. The generated SQL contains literal values, not bound parameters; table
and field names should come from trusted sources.

## Tests

Run `uv run pytest --engine=sqlite` for SQLite (the default). To run the
shared tests against PostgreSQL, provide a connection string for a disposable
database and run:

```sh
KYUBI_POSTGRES_DSN=postgresql://kyubi:kyubi@localhost:5432/kyubi \
  uv run pytest --engine=postgres
```

The PostgreSQL test user needs permission to create schemas. Each test uses
an isolated schema and rolls back its changes.
