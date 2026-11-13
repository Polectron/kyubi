from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kyubi.engines.engine import Engine


@dataclass(frozen=True)
class TableDef:
    table_name: str
    engine: Engine
    alias: str | None = None
