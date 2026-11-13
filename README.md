# kyubi

A python SQL query builder

## Engines

Set a table's `Meta.engine` to `kyubi.engines.sqlite.SQLite()` or
`kyubi.engines.postgres.Postgres()` to generate SQL for that database. Both
support select and grouped select queries. PostgreSQL also supports `OFFSET`
without a `LIMIT`; the SQLite engine requires a limit.

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
