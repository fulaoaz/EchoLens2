"""NetworkX in-memory subgraph — hot data for simulator + visualization export."""

from __future__ import annotations

from typing import Any

import networkx as nx


def new_graph() -> nx.MultiDiGraph:
    """Create an empty multi-directed graph used as the runtime hot store."""
    g: nx.MultiDiGraph = nx.MultiDiGraph()
    return g


def to_graphml(g: nx.MultiDiGraph) -> bytes:  # pragma: no cover - stub
    raise NotImplementedError("M1: serialize for visualization export")


def from_kuzu_subgraph(rows: list[dict[str, Any]]) -> nx.MultiDiGraph:  # pragma: no cover
    raise NotImplementedError("M1: hydrate hot subgraph from Kuzu Cypher result")
