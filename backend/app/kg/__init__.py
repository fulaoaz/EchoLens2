"""Knowledge-graph module — three-layer stack.

- store.py            : Kuzu (embedded graph DB, Cypher) — persistence + structured query
- lightrag_engine.py  : LightRAG — graph-augmented RAG (LLM-on-Graph)
- memory.py           : NetworkX — in-memory hot subgraph for simulator + visualization
- ontology.py         : Pydantic models for the e-commerce ontology
- extractor.py        : LLM-driven entity / relation extraction
- search.py           : unified, evidence-grounded query facade

Downstream features (simulator, prediction, decision, report) should depend
only on :mod:`app.kg.search`. The other modules are implementation details
that may be swapped (e.g. Kuzu/LightRAG behind the same surface) without
touching call sites.
"""

from app.kg.search import (
    EntityHit,
    EvidenceItem,
    RelationHit,
    SearchResult,
    get_subgraph,
    search,
)

__all__ = [
    "EntityHit",
    "EvidenceItem",
    "RelationHit",
    "SearchResult",
    "get_subgraph",
    "search",
]
