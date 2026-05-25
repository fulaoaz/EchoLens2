"""End-to-end tests for /api/projects/<id>/seed_data and /seed_report."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from app.services.crawler_store import get_crawler_store
from app.services.project_store import get_store


@pytest.fixture(autouse=True)
def _reset_stores() -> None:
    get_store().clear()
    get_crawler_store().clear()


def _create_project(client: Any, name: str = "seed-test") -> str:
    resp = client.post("/api/projects", json={"name": name, "keywords": ["k"]})
    assert resp.status_code == 201
    return resp.get_json()["data"]["id"]


def _seed_payload() -> dict[str, list[dict[str, Any]]]:
    return {
        "products": [
            {
                "platform": "jd",
                "id": "jd:1",
                "title": "Anker 737 移动电源 官方旗舰店",
                "brand": "Anker",
                "price_current": 599.0,
                "crawled_at": "2026-05-20T12:00:00",
            },
            {
                "platform": "taobao",
                "id": "tb:1",
                "title": "Anker 737 移动电源 正品包邮",
                "brand": "Anker",
                "price_current": 549.0,
                "crawled_at": "2026-05-20T12:00:00",
            },
        ],
        "reviews": [
            {
                "platform": "jd",
                "id": "r1",
                "content": "续航很好",
                "sentiment": "positive",
            },
            {
                "platform": "jd",
                "id": "r2",
                "content": "外壳掉漆",
                "sentiment": "negative",
            },
        ],
        "posts": [
            {
                "platform": "weibo",
                "id": "w1",
                "author_hash": "kol_alice_aaaaaa",
                "content": "试用感受：很顶",
                "sentiment": "positive",
                "posted_at": "2026-05-18T10:00:00",
            },
            {
                "platform": "xhs",
                "id": "x1",
                "author_hash": "kol_bob_bbbbbb",
                "content": "拔草帖：发热严重",
                "sentiment": "negative",
                "posted_at": "2026-05-19T18:00:00",
            },
        ],
    }


def test_seed_data_round_trip(client: Any) -> None:
    pid = _create_project(client)
    resp = client.post(f"/api/projects/{pid}/seed_data", json=_seed_payload())
    assert resp.status_code == 201, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["data"]["ingested"] == {"products": 2, "reviews": 2, "posts": 2}

    # Project status flipped to seed_ready.
    detail = client.get(f"/api/projects/{pid}").get_json()
    assert detail["data"]["status"] == "seed_ready"


def test_seed_report_after_ingest(client: Any) -> None:
    pid = _create_project(client)
    client.post(f"/api/projects/{pid}/seed_data", json=_seed_payload())

    resp = client.get(f"/api/projects/{pid}/seed_report")
    assert resp.status_code == 200
    report = resp.get_json()["data"]
    assert report["project_id"] == pid
    assert report["counts"]["products"] == 2
    assert report["counts"]["reviews"] == 2
    assert report["counts"]["posts"] == 2
    # Two products with the same brand+normalized title — alignment finds one group.
    assert report["counts"]["cross_platform_groups"] == 1
    # Sentiment distribution carries through.
    assert report["review_sentiment_distribution"]["positive"] == 1
    assert report["review_sentiment_distribution"]["negative"] == 1
    # Top KOL list is sorted by post count.
    assert report["top_kols"][0]["author_hash"] in {
        "kol_alice_aaaaaa",
        "kol_bob_bbbbbb",
    }


def test_seed_report_empty_project_is_safe(client: Any) -> None:
    pid = _create_project(client, "empty-proj")
    resp = client.get(f"/api/projects/{pid}/seed_report")
    assert resp.status_code == 200
    report = resp.get_json()["data"]
    assert report["counts"]["products"] == 0
    assert report["summary_text"].startswith("暂无可用数据")


def test_seed_data_404_when_project_missing(client: Any) -> None:
    resp = client.post("/api/projects/missing/seed_data", json=_seed_payload())
    assert resp.status_code == 404


def test_seed_report_404_when_project_missing(client: Any) -> None:
    resp = client.get("/api/projects/missing/seed_report")
    assert resp.status_code == 404


def test_seed_data_idempotent_overwrite(client: Any) -> None:
    """Re-ingesting same id overwrites instead of duplicating."""
    pid = _create_project(client)
    payload = _seed_payload()
    client.post(f"/api/projects/{pid}/seed_data", json=payload)
    # Mutate one product price and re-ingest — count stays the same.
    payload["products"][0]["price_current"] = 459.0
    client.post(f"/api/projects/{pid}/seed_data", json=payload)
    report = client.get(f"/api/projects/{pid}/seed_report").get_json()["data"]
    assert report["counts"]["products"] == 2


def test_delete_project_removes_seed_records(client: Any) -> None:
    pid = _create_project(client)
    client.post(f"/api/projects/{pid}/seed_data", json=_seed_payload())
    client.delete(f"/api/projects/{pid}")

    # Project gone.
    assert client.get(f"/api/projects/{pid}").status_code == 404

    # Records gone too — recreate same id (would be different uuid normally,
    # so we just verify the crawler store has zero rows for the old id).
    crawler = get_crawler_store()
    assert crawler.list_for_project(pid, "product") == []
    assert crawler.list_for_project(pid, "review") == []
    assert crawler.list_for_project(pid, "post") == []


def test_seed_data_rejects_extra_fields(client: Any) -> None:
    pid = _create_project(client)
    resp = client.post(
        f"/api/projects/{pid}/seed_data",
        json={"products": [], "reviews": [], "posts": [], "evil": True},
    )
    assert resp.status_code == 400


def test_persistence_across_app_restart(tmp_path: Any, monkeypatch: Any) -> None:
    """Data written through Flask survives losing the singleton."""
    from app import create_app
    from app.config import get_settings
    from app.services import crawler_store, project_store

    db_path = tmp_path / "restart.duckdb"
    monkeypatch.setenv("DUCKDB_PATH", str(db_path))
    get_settings.cache_clear()  # type: ignore[attr-defined]
    project_store.reset_store_singleton()
    crawler_store.reset_crawler_store_singleton()

    app = create_app({"TESTING": True})
    client_a = app.test_client()
    pid = _create_project(client_a, "restart-test")
    client_a.post(f"/api/projects/{pid}/seed_data", json=_seed_payload())

    # Drop singletons → simulate process restart.
    project_store.reset_store_singleton()
    crawler_store.reset_crawler_store_singleton()

    client_b = app.test_client()
    detail = client_b.get(f"/api/projects/{pid}").get_json()
    assert detail["success"] is True
    report = client_b.get(f"/api/projects/{pid}/seed_report").get_json()["data"]
    assert report["counts"]["products"] == 2

    # Restore conftest path so other tests still work.
    monkeypatch.undo()
    get_settings.cache_clear()  # type: ignore[attr-defined]
    project_store.reset_store_singleton()
    crawler_store.reset_crawler_store_singleton()


def test_unicode_seed_report(client: Any) -> None:
    """Non-ASCII content survives the JSON → DuckDB → JSON round trip."""
    pid = _create_project(client, "unicode-test")
    payload = _seed_payload()
    payload["products"][0]["title"] = "🎁 双11 美妆超值礼盒 官方旗舰店"
    client.post(f"/api/projects/{pid}/seed_data", json=payload)
    report = client.get(f"/api/projects/{pid}/seed_report").get_json()["data"]
    titles = {p["title"] for p in report["products"]}
    assert "🎁 双11 美妆超值礼盒 官方旗舰店" in titles


def test_summary_text_present_when_records(client: Any) -> None:
    pid = _create_project(client)
    client.post(f"/api/projects/{pid}/seed_data", json=_seed_payload())
    report = client.get(f"/api/projects/{pid}/seed_report").get_json()["data"]
    assert "覆盖" in report["summary_text"]


def test_generated_at_is_iso_string(client: Any) -> None:
    pid = _create_project(client)
    client.post(f"/api/projects/{pid}/seed_data", json=_seed_payload())
    report = client.get(f"/api/projects/{pid}/seed_report").get_json()["data"]
    # Round-trip through fromisoformat to confirm it's ISO-8601.
    parsed = datetime.fromisoformat(report["generated_at"])
    assert isinstance(parsed, datetime)
