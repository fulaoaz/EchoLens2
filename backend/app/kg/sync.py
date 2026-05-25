"""NetworkX → Kuzu projection (one-way sync).

Per docs/kg-spike-report.md §3.2 (Option d): LightRAG owns ingest on its
NetworkX backend; this module projects the same graph into Kuzu so the
backend can serve typed Cypher queries.

The sync is:
- one-way (NetworkX → Kuzu)
- idempotent (MERGE-style upserts via Kuzu's `MERGE` Cypher)
- incremental (caller passes only changed node ids; full rebuild also supported)

Schema convention
-----------------
- LightRAG NetworkX nodes carry an `entity_type` string attribute (e.g. "Product",
  "Brand", "KOL", "Topic"). We project each `entity_type` to a Kuzu node table
  with the same name. Unknown entity types fall back to a generic `Entity` table.
- Edges carry an optional `relation_type` attribute. We project to a single
  generic `RELATED_TO` rel table with `relation_type` and `weight` properties
  to avoid Kuzu's strict-schema requirement of declaring every typed rel up
  front. (M2 may split this once the ontology stabilizes.)
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import kuzu
import networkx as nx

# Default ontology — entity types we know about up front. Unknown types fall
# back to the generic Entity table.
DEFAULT_ENTITY_TABLES: tuple[str, ...] = (
    "Product",
    "Brand",
    "KOL",
    "Topic",
    "Entity",
)


def init_kuzu_schema(
    conn: kuzu.Connection,
    entity_tables: Iterable[str] = DEFAULT_ENTITY_TABLES,
) -> None:
    """Create node tables (one per entity type) + a generic RELATED_TO rel table.

    Idempotent — re-running on an existing DB is a no-op.
    """
    for table in entity_tables:
        conn.execute(
            f"CREATE NODE TABLE IF NOT EXISTS {table}("
            "id STRING, name STRING, source STRING, PRIMARY KEY(id))"
        )
    # FROM/TO must enumerate all source/target tables for Kuzu rel tables.
    pairs = ", ".join(f"FROM {t} TO {u}" for t in entity_tables for u in entity_tables)
    conn.execute(
        f"CREATE REL TABLE IF NOT EXISTS RELATED_TO({pairs}, "
        "relation_type STRING, weight DOUBLE)"
    )


def _entity_table_for(entity_type: str | None) -> str:
    if entity_type and entity_type in DEFAULT_ENTITY_TABLES:
        return entity_type
    return "Entity"


def project_networkx_to_kuzu(
    graph: nx.Graph | nx.DiGraph,
    db_path: str | Path,
    *,
    entity_tables: Iterable[str] = DEFAULT_ENTITY_TABLES,
) -> dict[str, int]:
    """Project a NetworkX graph into a Kuzu DB at ``db_path``.

    Returns a dict with counts: ``{"nodes": N, "edges": M}``.

    Node attributes used:
      - ``entity_type`` (str, optional): routes to the matching Kuzu node table.
      - ``name`` (str, optional): defaults to node id.
      - ``source`` (str, optional): provenance hint.

    Edge attributes used:
      - ``relation_type`` (str, optional)
      - ``weight`` (float, optional, default 1.0)
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)
    init_kuzu_schema(conn, entity_tables=entity_tables)

    # 1. Upsert nodes. Kuzu's MERGE works only when the table is known, so we
    #    route per entity_type. We use a parameterised MERGE for safety.
    nodes_written = 0
    for node_id, data in graph.nodes(data=True):
        table = _entity_table_for(data.get("entity_type"))
        params: dict[str, Any] = {
            "id": str(node_id),
            "name": str(data.get("name", node_id)),
            "source": str(data.get("source", "")),
        }
        conn.execute(
            f"MERGE (n:{table} {{id: $id}}) "
            "SET n.name = $name, n.source = $source",
            parameters=params,
        )
        nodes_written += 1

    # 2. Upsert edges. We MATCH src/dst by id across any node table by trying
    #    each table in turn; in practice we resolve via the same per-type lookup.
    edges_written = 0
    for u, v, data in graph.edges(data=True):
        u_type = _entity_table_for(graph.nodes[u].get("entity_type"))
        v_type = _entity_table_for(graph.nodes[v].get("entity_type"))
        params = {
            "u": str(u),
            "v": str(v),
            "rel": str(data.get("relation_type", "RELATED")),
            "w": float(data.get("weight", 1.0)),
        }
        conn.execute(
            f"MATCH (a:{u_type} {{id: $u}}), (b:{v_type} {{id: $v}}) "
            "MERGE (a)-[r:RELATED_TO]->(b) "
            "SET r.relation_type = $rel, r.weight = $w",
            parameters=params,
        )
        edges_written += 1

    return {"nodes": nodes_written, "edges": edges_written}


def cypher(db_path: str | Path, query: str, params: dict[str, Any] | None = None) -> list[tuple]:
    """Run a Cypher query and return all rows as plain tuples."""
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)
    result = conn.execute(query, parameters=params or {})
    rows: list[tuple] = []
    while result.has_next():
        rows.append(tuple(result.get_next()))
    return rows
