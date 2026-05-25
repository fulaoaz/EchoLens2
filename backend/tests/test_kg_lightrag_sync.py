"""LightRAG ↔ NetworkX ↔ Kuzu integration smoke test.

Verifies the M0.C spike report Option (d) integration path **without an LLM**:
- LightRAG package imports and exposes its NetworkX backend
- A NetworkX graph populated by hand can be projected into Kuzu via
  ``app.kg.sync.project_networkx_to_kuzu``
- Cypher queries against the projected graph return expected rows

This is the gate that flips ``[unverified-online]`` → verified for the
LightRAG ↔ Kuzu glue. Full LightRAG end-to-end (LLM extraction → ingest →
query) is exercised separately in M1.2 once an LLM endpoint is configured.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import networkx as nx
import pytest

from app.kg.sync import cypher, project_networkx_to_kuzu


def test_lightrag_package_imports() -> None:
    """LightRAG installs cleanly and exposes its public API."""
    import lightrag  # noqa: F401
    from lightrag import LightRAG, QueryParam  # noqa: F401
    from lightrag.kg.networkx_impl import NetworkXStorage  # noqa: F401

    # Anchor on a known-good range so a wildly newer/older release fails loudly.
    assert lightrag.__version__.startswith("1."), (
        f"unexpected lightrag version: {lightrag.__version__}"
    )


def test_networkx_to_kuzu_projection_roundtrip() -> None:
    """Build a tiny ontology graph, project to Kuzu, query back."""
    g: nx.DiGraph = nx.DiGraph()
    # Three brands, two products each.
    g.add_node("b1", entity_type="Brand", name="国货品牌 X", source="seed")
    g.add_node("b2", entity_type="Brand", name="进口品牌 Y", source="seed")
    g.add_node("p1", entity_type="Product", name="面霜 A", source="seed")
    g.add_node("p2", entity_type="Product", name="精华 B", source="seed")
    g.add_node("p3", entity_type="Product", name="口红 C", source="seed")
    g.add_node("k1", entity_type="KOL", name="美妆达人 K", source="seed")
    g.add_node("t1", entity_type="Topic", name="保湿", source="seed")

    g.add_edge("p1", "b1", relation_type="MADE_BY", weight=1.0)
    g.add_edge("p2", "b1", relation_type="MADE_BY", weight=1.0)
    g.add_edge("p3", "b2", relation_type="MADE_BY", weight=1.0)
    g.add_edge("k1", "p1", relation_type="REVIEWED", weight=0.8)
    g.add_edge("p1", "t1", relation_type="ABOUT", weight=0.6)

    tmp = Path(tempfile.mkdtemp(prefix="kg_sync_"))
    try:
        db_path = tmp / "kg"
        counts = project_networkx_to_kuzu(g, db_path)
        assert counts == {"nodes": 7, "edges": 5}

        # Idempotency: re-running yields the same Kuzu state, not duplicates.
        counts2 = project_networkx_to_kuzu(g, db_path)
        assert counts2 == {"nodes": 7, "edges": 5}

        # Structured Cypher: which products belong to brand b1?
        rows = cypher(
            db_path,
            "MATCH (p:Product)-[r:RELATED_TO]->(b:Brand {id: 'b1'}) "
            "WHERE r.relation_type = 'MADE_BY' "
            "RETURN p.name ORDER BY p.name",
        )
        names = sorted(r[0] for r in rows)
        assert names == ["精华 B", "面霜 A"]

        # KOL → product reach.
        rows = cypher(
            db_path,
            "MATCH (k:KOL)-[r:RELATED_TO]->(p:Product) "
            "WHERE r.relation_type = 'REVIEWED' "
            "RETURN k.name, p.name",
        )
        assert rows == [("美妆达人 K", "面霜 A")]

        # Topic linkage.
        rows = cypher(
            db_path,
            "MATCH (p:Product)-[r:RELATED_TO]->(t:Topic) "
            "RETURN p.name, t.name, r.weight",
        )
        assert rows == [("面霜 A", "保湿", pytest.approx(0.6))]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_unknown_entity_type_falls_back_to_entity_table() -> None:
    """Nodes with an unknown ``entity_type`` go to the generic Entity table."""
    g: nx.DiGraph = nx.DiGraph()
    g.add_node("e1", entity_type="UnknownType", name="某未知实体")
    g.add_node("e2", entity_type="UnknownType", name="另一个未知实体")
    g.add_edge("e1", "e2", relation_type="LINKED")

    tmp = Path(tempfile.mkdtemp(prefix="kg_sync_unknown_"))
    try:
        counts = project_networkx_to_kuzu(g, tmp / "kg")
        assert counts == {"nodes": 2, "edges": 1}

        rows = cypher(
            tmp / "kg",
            "MATCH (a:Entity)-[r:RELATED_TO]->(b:Entity) "
            "RETURN a.name, b.name, r.relation_type",
        )
        assert rows == [("某未知实体", "另一个未知实体", "LINKED")]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
