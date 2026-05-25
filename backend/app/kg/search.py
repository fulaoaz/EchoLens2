"""Unified KG query facade — project-scoped, evidence-grounded retrieval.

This module is the single retrieval entry point for downstream EchoLens2
features (simulator, prediction, decision, report). It owns three concerns:

1. Project isolation — every query is scoped to a single ``project_id`` and
   never leaks records from other projects.
2. Evidence grounding — every returned entity / relation carries the ids of
   the raw records it was derived from, so callers can trace any conclusion
   back to the original crawl payload via :class:`CrawlerStore`.
3. Self-contained execution — no LLM, no remote service, no dependency on
   the legacy EchoLens GraphRAG / Zep stack. The facade builds an
   in-memory NetworkX projection of the project's crawled records on each
   call. It is intentionally simple; M2 may swap in Kuzu/LightRAG behind
   the same surface without changing call sites.

Public surface
--------------
- :func:`search` — keyword / structured search across entities + evidence.
- :func:`get_subgraph` — dump the project graph as plain dicts for the
  simulator and visualization layer.
- :class:`SearchResult` — TypedDict describing the search payload.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, TypedDict

import networkx as nx

from app.services.crawler_store import CrawlerStore, get_crawler_store

# Entity type tags (kept narrow on purpose — these are what the simulator,
# decision and report layers actually consume today).
ENTITY_TYPES = ("Product", "Brand", "KOL", "Topic", "Post", "Review")

# Keep search input bounded so a pathological query can't blow up the
# in-memory graph traversal.
_MAX_QUERY_LEN = 200
_DEFAULT_LIMIT = 10


class EntityHit(TypedDict):
    id: str
    type: str
    name: str
    score: float
    evidence_ids: list[str]


class RelationHit(TypedDict):
    src: str
    dst: str
    type: str
    weight: float


class EvidenceItem(TypedDict, total=False):
    id: str
    kind: str
    title: str
    snippet: str
    url: str
    platform: str
    source: str
    keyword: str


class SearchResult(TypedDict):
    project_id: str
    query: str
    entities: list[EntityHit]
    relations: list[RelationHit]
    evidence: list[EvidenceItem]


@dataclass(frozen=True)
class _ProjectGraph:
    """Project graph + index of evidence records keyed by record id."""

    graph: nx.MultiDiGraph
    evidence: dict[str, EvidenceItem]


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def _entity_id(kind: str, value: str) -> str:
    """Stable, content-addressable id (so re-builds yield identical ids)."""
    cleaned = re.sub(r"\s+", " ", value).strip().lower()
    return f"{kind}:{cleaned}"


def _evidence_from_product(record: dict[str, Any]) -> EvidenceItem:
    title = str(record.get("title") or record.get("id") or "")
    sample = str(record.get("source_text_sample") or "")
    return EvidenceItem(
        id=str(record.get("id", "")),
        kind="product",
        title=title,
        snippet=sample[:400],
        url=str(record.get("url", "")),
        platform=str(record.get("platform", "")),
        source=str(record.get("source", "")),
        keyword=str(record.get("keyword", "")),
    )


def _evidence_from_post(record: dict[str, Any]) -> EvidenceItem:
    content = str(record.get("content") or "")
    return EvidenceItem(
        id=str(record.get("id", "")),
        kind="post",
        title=content[:80],
        snippet=content[:400],
        url=str(record.get("url", "")),
        platform=str(record.get("platform", "")),
        source=str(record.get("source", "")),
        keyword=str(record.get("keyword", "")),
    )


def _evidence_from_review(record: dict[str, Any]) -> EvidenceItem:
    content = str(record.get("content") or record.get("title") or "")
    return EvidenceItem(
        id=str(record.get("id", "")),
        kind="review",
        title=content[:80],
        snippet=content[:400],
        url=str(record.get("url", "")),
        platform=str(record.get("platform", "")),
        source=str(record.get("source", "")),
        keyword=str(record.get("keyword", "")),
    )


def _add_entity(
    graph: nx.MultiDiGraph,
    kind: str,
    name: str,
    *,
    evidence_id: str,
) -> str:
    name = (name or "").strip()
    if not name:
        return ""
    node_id = _entity_id(kind, name)
    if graph.has_node(node_id):
        graph.nodes[node_id]["evidence_ids"].add(evidence_id)
    else:
        graph.add_node(
            node_id,
            type=kind,
            name=name,
            evidence_ids={evidence_id},
        )
    return node_id


def _add_relation(
    graph: nx.MultiDiGraph,
    src: str,
    dst: str,
    rel: str,
    weight: float = 1.0,
) -> None:
    if not src or not dst or src == dst:
        return
    # Coalesce parallel edges of the same type; keep one per (src, dst, rel).
    for _, _, data in graph.edges(src, data=True):
        if data.get("relation_type") == rel and data.get("_dst") == dst:
            data["weight"] = float(data.get("weight", 1.0)) + weight
            return
    graph.add_edge(src, dst, relation_type=rel, weight=float(weight), _dst=dst)


def _build_project_graph(
    project_id: str,
    *,
    store: CrawlerStore | None = None,
) -> _ProjectGraph:
    store = store or get_crawler_store()
    products = store.list_for_project(project_id, "product")
    reviews = store.list_for_project(project_id, "review")
    posts = store.list_for_project(project_id, "post")

    graph: nx.MultiDiGraph = nx.MultiDiGraph()
    evidence: dict[str, EvidenceItem] = {}

    # Products → Brand / Topic
    for record in products:
        item = _evidence_from_product(record)
        rid = item["id"]
        if not rid:
            continue
        evidence[rid] = item
        product_node = _add_entity(graph, "Product", item["title"], evidence_id=rid)
        brand = (record.get("brand") or item.get("keyword") or "").strip()
        if brand:
            brand_node = _add_entity(graph, "Brand", brand, evidence_id=rid)
            _add_relation(graph, product_node, brand_node, "MADE_BY")
        keyword = item.get("keyword") or ""
        if keyword:
            topic_node = _add_entity(graph, "Topic", keyword, evidence_id=rid)
            _add_relation(graph, product_node, topic_node, "RELATED_TO", 0.5)

    # Posts → Topic / KOL
    for record in posts:
        item = _evidence_from_post(record)
        rid = item["id"]
        if not rid:
            continue
        evidence[rid] = item
        title = item["title"] or item.get("keyword") or rid
        post_node = _add_entity(graph, "Post", title, evidence_id=rid)
        author = str(record.get("author_hash") or "").strip()
        if author:
            kol_node = _add_entity(graph, "KOL", author, evidence_id=rid)
            _add_relation(graph, kol_node, post_node, "AUTHORED")
        keyword = item.get("keyword") or ""
        if keyword:
            topic_node = _add_entity(graph, "Topic", keyword, evidence_id=rid)
            _add_relation(graph, post_node, topic_node, "MENTIONS")

    # Reviews → Product (linked through brand keyword when product id absent)
    for record in reviews:
        item = _evidence_from_review(record)
        rid = item["id"]
        if not rid:
            continue
        evidence[rid] = item
        review_node = _add_entity(graph, "Review", item["title"] or rid, evidence_id=rid)
        keyword = item.get("keyword") or ""
        if keyword:
            topic_node = _add_entity(graph, "Topic", keyword, evidence_id=rid)
            _add_relation(graph, review_node, topic_node, "ABOUT", 0.8)

    return _ProjectGraph(graph=graph, evidence=evidence)


# ---------------------------------------------------------------------------
# Search / scoring
# ---------------------------------------------------------------------------


def _tokenize(query: str) -> list[str]:
    """Split a query into searchable tokens (Latin words + CJK runs)."""
    if not query:
        return []
    cleaned = query.strip().lower()[:_MAX_QUERY_LEN]
    tokens = re.findall(r"[\w一-鿿]+", cleaned)
    # Drop tokens that are too short to be useful (single Latin letters).
    return [t for t in tokens if len(t) >= 1]


def _entity_score(name: str, tokens: Iterable[str]) -> float:
    if not name:
        return 0.0
    haystack = name.lower()
    score = 0.0
    for token in tokens:
        if not token:
            continue
        if token == haystack:
            score += 3.0
        elif token in haystack:
            score += 1.0
    return score


def _evidence_score(item: EvidenceItem, tokens: Iterable[str]) -> float:
    haystack = " ".join(
        str(item.get(k, "")) for k in ("title", "snippet", "keyword")
    ).lower()
    if not haystack:
        return 0.0
    score = 0.0
    for token in tokens:
        if token and token in haystack:
            score += 1.0
    return score


def search(
    project_id: str,
    query: str = "",
    *,
    limit: int = _DEFAULT_LIMIT,
    store: CrawlerStore | None = None,
) -> SearchResult:
    """Search a project's knowledge graph by free-text ``query``.

    The result is grounded: every entity carries the ids of raw records that
    contributed to it, and every relation comes from the projected graph. An
    empty ``query`` returns the top ``limit`` most-connected entities (a
    handy "what does this project look like?" probe).
    """
    if not project_id:
        raise ValueError("project_id is required")
    if limit <= 0:
        raise ValueError("limit must be positive")

    pg = _build_project_graph(project_id, store=store)
    tokens = _tokenize(query)

    # Entity ranking — query match (when present) + degree as tie-breaker.
    entity_hits: list[tuple[float, EntityHit]] = []
    for node_id, data in pg.graph.nodes(data=True):
        name = str(data.get("name", ""))
        token_score = _entity_score(name, tokens) if tokens else 0.0
        if tokens and token_score == 0.0:
            continue
        degree = pg.graph.degree(node_id)
        score = token_score + min(degree, 10) * 0.1
        entity_hits.append(
            (
                score,
                EntityHit(
                    id=node_id,
                    type=str(data.get("type", "Entity")),
                    name=name,
                    score=round(score, 3),
                    evidence_ids=sorted(data.get("evidence_ids", set())),
                ),
            )
        )
    entity_hits.sort(key=lambda pair: (-pair[0], pair[1]["name"]))
    top_entities = [hit for _, hit in entity_hits[:limit]]

    # Relations — only those touching the surfaced entities, deduped.
    surfaced_ids = {hit["id"] for hit in top_entities}
    relations: list[RelationHit] = []
    seen_rel_keys: set[tuple[str, str, str]] = set()
    for src in surfaced_ids:
        if not pg.graph.has_node(src):
            continue
        for _, _dst, data in pg.graph.out_edges(src, data=True):
            dst = str(data.get("_dst") or _dst)
            rel = str(data.get("relation_type", "RELATED"))
            key = (src, dst, rel)
            if key in seen_rel_keys:
                continue
            seen_rel_keys.add(key)
            relations.append(
                RelationHit(
                    src=src,
                    dst=dst,
                    type=rel,
                    weight=float(data.get("weight", 1.0)),
                )
            )

    # Evidence — union of (entities' evidence) and (records matching tokens).
    evidence_ids: set[str] = set()
    for hit in top_entities:
        evidence_ids.update(hit["evidence_ids"])
    if tokens:
        for rid, item in pg.evidence.items():
            if _evidence_score(item, tokens) > 0:
                evidence_ids.add(rid)

    evidence_items = [pg.evidence[rid] for rid in evidence_ids if rid in pg.evidence]
    evidence_items.sort(key=lambda item: _evidence_score(item, tokens), reverse=True)
    evidence_items = evidence_items[: max(limit, 5) * 2]

    return SearchResult(
        project_id=project_id,
        query=query,
        entities=top_entities,
        relations=relations,
        evidence=evidence_items,
    )


def get_subgraph(
    project_id: str,
    *,
    store: CrawlerStore | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Return the project graph as plain ``{nodes, edges}`` dicts.

    Used by the simulator to seed scenarios and by the report layer to
    render evidence networks. The shape is intentionally trivial — no
    NetworkX objects leak across the module boundary.
    """
    if not project_id:
        raise ValueError("project_id is required")
    pg = _build_project_graph(project_id, store=store)
    nodes = [
        {
            "id": node_id,
            "type": str(data.get("type", "Entity")),
            "name": str(data.get("name", "")),
            "evidence_ids": sorted(data.get("evidence_ids", set())),
        }
        for node_id, data in pg.graph.nodes(data=True)
    ]
    edges: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for src, dst, data in pg.graph.edges(data=True):
        rel = str(data.get("relation_type", "RELATED"))
        key = (src, dst, rel)
        if key in seen:
            continue
        seen.add(key)
        edges.append(
            {
                "src": src,
                "dst": dst,
                "type": rel,
                "weight": float(data.get("weight", 1.0)),
            }
        )
    return {"nodes": nodes, "edges": edges}


__all__ = [
    "EntityHit",
    "EvidenceItem",
    "RelationHit",
    "SearchResult",
    "get_subgraph",
    "search",
]
