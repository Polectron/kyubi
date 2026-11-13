import sqlite3
from collections.abc import Iterator

import pytest

from kyubi.engines.sqlite import SQLite
from kyubi.table import AnonymousTable, table
from tests.helpers import UserTable


@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch) -> SQLite:
    sqlite_engine = SQLite()
    monkeypatch.setattr(AnonymousTable.Meta, "engine", sqlite_engine, raising=False)
    monkeypatch.setattr(UserTable.Meta, "engine", sqlite_engine, raising=False)
    return sqlite_engine


@pytest.fixture
def sqlite_connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(":memory:")
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture(params=["anonymous", "declared"])
def t(request, engine):
    if request.param == "anonymous":
        return table("test_table")
    return UserTable()
