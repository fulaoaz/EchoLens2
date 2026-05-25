"""KG smoke test — verify Kuzu embedded graph DB works on this machine.

Removes one of the [unverified-online] tags from docs/kg-spike-report.md.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import kuzu


def test_kuzu_basic_roundtrip() -> None:
    """Create DB → declare schema → insert → query → assert."""
    tmp = Path(tempfile.mkdtemp(prefix="kuzu_smoke_"))
    try:
        db = kuzu.Database(str(tmp / "db"))
        conn = kuzu.Connection(db)

        # Declare ontology subset
        conn.execute("CREATE NODE TABLE Product(id STRING, name STRING, PRIMARY KEY(id))")
        conn.execute("CREATE NODE TABLE Brand(id STRING, name STRING, PRIMARY KEY(id))")
        conn.execute("CREATE REL TABLE MADE_BY(FROM Product TO Brand, weight DOUBLE)")

        # Insert
        conn.execute("CREATE (:Product {id: 'p1', name: '面霜 A'})")
        conn.execute("CREATE (:Product {id: 'p2', name: '精华 B'})")
        conn.execute("CREATE (:Brand   {id: 'b1', name: '国货品牌 X'})")
        conn.execute(
            "MATCH (p:Product {id: 'p1'}), (b:Brand {id: 'b1'}) "
            "CREATE (p)-[:MADE_BY {weight: 1.0}]->(b)"
        )
        conn.execute(
            "MATCH (p:Product {id: 'p2'}), (b:Brand {id: 'b1'}) "
            "CREATE (p)-[:MADE_BY {weight: 1.0}]->(b)"
        )

        # Query: which products belong to brand X?
        result = conn.execute(
            "MATCH (p:Product)-[:MADE_BY]->(b:Brand {id: 'b1'}) "
            "RETURN p.name ORDER BY p.name"
        )
        rows = []
        while result.has_next():
            rows.append(result.get_next())
        assert len(rows) == 2
        names = sorted(r[0] for r in rows)
        assert names == ["精华 B", "面霜 A"]
    finally:
        # Kuzu may keep file handles open on Windows; ignore cleanup errors.
        shutil.rmtree(tmp, ignore_errors=True)
