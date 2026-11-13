import os
import sqlite3
from collections.abc import Iterator
from uuid import uuid4

import psycopg
import pytest

from kyubi.engines.engine import Engine
from kyubi.engines.postgres import Postgres
from kyubi.engines.sqlite import SQLite
from kyubi.table import AnonymousTable, table
from tests.helpers import UserTable


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--engine",
        choices=("sqlite", "postgres"),
        default="sqlite",
        help="SQL engine used by the shared tests",
    )


@pytest.fixture
def engine(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Engine:
    selected_engine = (
        Postgres() if request.config.getoption("--engine") == "postgres" else SQLite()
    )
    monkeypatch.setattr(AnonymousTable.Meta, "engine", selected_engine, raising=False)
    monkeypatch.setattr(UserTable.Meta, "engine", selected_engine, raising=False)
    return selected_engine


@pytest.fixture
def sqlite_connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(":memory:")
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def db_connection(engine: Engine) -> Iterator[sqlite3.Connection | psycopg.Connection]:
    if isinstance(engine, SQLite):
        connection = sqlite3.connect(":memory:")
        try:
            yield connection
        finally:
            connection.close()
    else:
        dsn = os.environ.get("KYUBI_POSTGRES_DSN")
        if not dsn:
            pytest.fail("KYUBI_POSTGRES_DSN is required when using --engine=postgres")
        with psycopg.connect(dsn) as connection:
            schema = f"kyubi_test_{uuid4().hex}"
            connection.execute(f"CREATE SCHEMA {schema}")
            connection.execute(f"SET LOCAL search_path TO {schema}")
            try:
                yield connection
            finally:
                connection.rollback()


@pytest.fixture(params=["anonymous", "declared"])
def t(request, engine):
    if request.param == "anonymous":
        return table("test_table")
    return UserTable()
