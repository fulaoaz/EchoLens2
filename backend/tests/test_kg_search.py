"""Tests for the unified KG search facade (``app.kg.search``).

The facade is intentionally self-contained — no LLM, no external service —
so these tests run fully offline. They cover three things that downstream
features (simulator, decision, report) actually rely on:

1. Project isolation: a query against project A never returns project B's
   data, even when both are stored in the same ``CrawlerStore``.
2. Evidence grounding: every entity hit carries the raw record ids it was
   built from, so the report layer can render an evidence chain.
3. Ranking shape: token-matching entities outrank generic ones, and
   ``get_subgraph`` returns plain ``{nodes, edges}`` dicts.
"""

from __future__ import annotations

import pytest

from app.kg.search import get_subgraph, search
from app.services.crawler_store import get_crawler_store


def _seed_project(project_id: str) -> None:
    store = get_crawler_store()
    store.upsert_many(
        project_id,
        "product",
        [
            {
                "id": "jd:p1",
                "platform": "jd",
                "url": "https://item.jd.com/p1.html",
                "title": "Anker 737 移动电源 旗舰款",
                "brand": "Anker",
                "keyword": "Anker 737",
                "source": "manual_url",
                "source_text_sample": "续航实测稳定，快充表现好。",
                "crawled_at": "2026-02-20T10:00:00",
            },
        ],
    )
    store.upsert_many(
        project_id,
        "post",
        [
            {
                "id": "weibo:post1",
                "platform": "weibo",
                "url": "https://weibo.com/p/post1",
                "content": "Anker 737 旗舰款发热控制不错，续航惊喜。",
                "author_hash": "source_0001234",
                "keyword": "Anker 737",
                "source": "material_search",
                "crawled_at": "2026-02-20T10:01:00",
            },
            {
                "id": "weibo:post2",
                "platform": "weibo",
                "url": "https://weibo.com/p/post2",
                "content": "另一款无关产品的舆论。",
                "author_hash": "source_0009999",
                "keyword": "其他",
                "source": "material_search",
                "crawled_at": "2026-02-20T10:02:00",
            },
        ],
    )
    store.upsert_many(
        project_id,
        "review",
        [
            {
                "id": "jd:r1",
                "platform": "jd",
                "url": "https://item.jd.com/p1.html#r1",
                "title": "用了一周，快充很顶。",
                "content": "用了一周，快充很顶。",
                "keyword": "Anker 737",
                "source": "manual_url",
                "sentiment": "positive",
                "crawled_at": "2026-02-20T10:03:00",
            },
        ],
    )


@pytest.fixture(autouse=True)
def _reset_store() -> None:
    get_crawler_store().clear()
    yield
    get_crawler_store().clear()


def test_search_requires_project_id() -> None:
    with pytest.raises(ValueError):
        search("")


def test_search_returns_evidence_grounded_entities() -> None:
    _seed_project("proj-a")
    result = search("proj-a", "Anker 737", limit=5)

    assert result["project_id"] == "proj-a"
    assert result["query"] == "Anker 737"

    # The product entity must surface and carry the raw record id.
    products = [e for e in result["entities"] if e["type"] == "Product"]
    assert products, "expected a Product entity for the queried keyword"
    assert "jd:p1" in products[0]["evidence_ids"]
    assert products[0]["score"] > 0

    # Evidence list must include the matching post AND product, but not the
    # unrelated post about "其他".
    evidence_ids = {item["id"] for item in result["evidence"]}
    assert "jd:p1" in evidence_ids
    assert "weibo:post1" in evidence_ids
    assert "weibo:post2" not in evidence_ids

    # Relations must reference surfaced entity ids only.
    surfaced = {e["id"] for e in result["entities"]}
    for rel in result["relations"]:
        assert rel["src"] in surfaced
        assert rel["type"]
        assert rel["weight"] >= 0


def test_search_isolates_projects() -> None:
    _seed_project("proj-a")
    get_crawler_store().upsert_many(
        "proj-b",
        "product",
        [
            {
                "id": "tmall:px",
                "platform": "tmall",
                "url": "https://detail.tmall.com/px.html",
                "title": "无关品牌移动电源",
                "brand": "OtherBrand",
                "keyword": "OtherBrand",
                "source": "manual_url",
                "source_text_sample": "另一项目的产品。",
                "crawled_at": "2026-02-20T11:00:00",
            },
        ],
    )

    a = search("proj-a", "Anker", limit=10)
    b = search("proj-b", "Anker", limit=10)

    a_ids = {item["id"] for item in a["evidence"]}
    b_ids = {item["id"] for item in b["evidence"]}
    assert "jd:p1" in a_ids
    assert "tmall:px" not in a_ids
    assert b_ids == set() or b_ids.isdisjoint(a_ids)


def test_search_with_empty_query_returns_top_connected_entities() -> None:
    _seed_project("proj-a")
    result = search("proj-a", "", limit=5)
    assert result["entities"], "empty query should still surface entities"
    # No token filtering means every entity is eligible; degree breaks ties.
    assert all(entity["score"] >= 0 for entity in result["entities"])


def test_get_subgraph_returns_plain_dicts() -> None:
    _seed_project("proj-a")
    sg = get_subgraph("proj-a")
    assert isinstance(sg["nodes"], list) and sg["nodes"]
    assert isinstance(sg["edges"], list) and sg["edges"]

    node_types = {n["type"] for n in sg["nodes"]}
    # The seeded data should produce at least Product, Brand, Topic, Post,
    # KOL and Review nodes (Review is created from review records).
    assert {"Product", "Brand", "Topic", "Post", "KOL", "Review"} <= node_types

    # Every edge must reference a real node id.
    node_ids = {n["id"] for n in sg["nodes"]}
    for edge in sg["edges"]:
        assert edge["src"] in node_ids
        assert edge["dst"] in node_ids
        assert edge["type"]


def test_search_limit_validation() -> None:
    _seed_project("proj-a")
    with pytest.raises(ValueError):
        search("proj-a", "Anker", limit=0)
