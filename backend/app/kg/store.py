"""Kuzu embedded graph DB facade — persistence + Cypher queries.

Stub — M1 will implement: connect, declare node/rel tables per ontology,
insert/upsert, read-only Cypher pass-through.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class KuzuStore:
    db_path: Path

    def __post_init__(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def init_schema(self) -> None:  # pragma: no cover - stub
        raise NotImplementedError("M1: declare Kuzu node/rel tables from ontology")

    def upsert_entity(self, node_id: str, type_: str, name: str, **attrs: str) -> None:
        raise NotImplementedError("M1")

    def upsert_relation(self, src: str, dst: str, type_: str, weight: float = 1.0) -> None:
        raise NotImplementedError("M1")

    def cypher(self, query: str, params: dict | None = None) -> list[dict]:
        raise NotImplementedError("M1: read-only Cypher passthrough")
