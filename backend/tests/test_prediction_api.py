"""End-to-end tests for the /api/prediction blueprint (M3.3)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest

from app.services import prediction_jobs
from app.services.crawler_store import get_crawler_store
from app.services.project_store import get_store


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    get_store().clear()
    get_crawler_store().clear()
    prediction_jobs.reset_for_tests()


def _seed_project(client: Any, *, name: str = "pred", days: int = 30) -> str:
    pid = client.post(
        "/api/projects", json={"name": name, "keywords": ["k"]}
    ).get_json()["data"]["id"]

    today = date(2026, 5, 20)
    posts = []
    for i in range(days):
        d = (today - timedelta(days=days - 1 - i)).isoformat()
        # Trend: more posts as time advances; sentiment flips mid-window.
        for _ in range(1 + i // 3):
            posts.append(
                {
                    "platform": "weibo",
                    "id": f"w-{i}-{_}",
                    "author_hash": "kol_demo_aaaaaa",
                    "content": "demo",
                    "sentiment": "positive" if i >= days // 2 else "negative",
                    "posted_at": f"{d}T10:00:00",
                }
            )
    reviews = [
        {"platform": "jd", "id": f"r{i}", "content": "ok", "sentiment": "positive"}
        for i in range(5)
    ]
    products = [
        {
            "platform": "jd",
            "id": "jd:p1",
            "title": "Demo",
            "brand": "Demo",
            "price_current": 199.0,
        }
    ]
    client.post(
        f"/api/projects/{pid}/seed_data",
        json={"products": products, "reviews": reviews, "posts": posts},
    )
    return pid


def test_ping_reports_implemented(client: Any) -> None:
    resp = client.get("/api/prediction/ping")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["data"]["implemented"] is True


def test_forecast_returns_full_run(client: Any) -> None:
    pid = _seed_project(client)
    resp = client.post(
        f"/api/prediction/{pid}/forecast",
        json={"metric": "volume", "horizon_days": 7, "confidence": 0.95},
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    data = body["data"]
    assert data["kind"] == "forecast"
    assert data["status"] == "completed"
    assert data["metric"] == "volume"
    assert "result" in data
    fc = data["result"]["forecast"]
    assert len(fc["forecast"]) == 7
    assert "explanation" in data["result"]
    assert "headline" in data["result"]["explanation"]


def test_forecast_unknown_project_returns_404(client: Any) -> None:
    resp = client.post(
        "/api/prediction/no-such/forecast",
        json={"metric": "volume", "horizon_days": 5},
    )
    assert resp.status_code == 404


def test_forecast_unknown_metric_returns_400(client: Any) -> None:
    pid = _seed_project(client)
    resp = client.post(
        f"/api/prediction/{pid}/forecast",
        json={"metric": "bogus", "horizon_days": 5},
    )
    assert resp.status_code == 400


def test_forecast_invalid_horizon_returns_400(client: Any) -> None:
    pid = _seed_project(client)
    resp = client.post(
        f"/api/prediction/{pid}/forecast",
        json={"metric": "volume", "horizon_days": 999},
    )
    assert resp.status_code == 400


def test_causal_returns_ate_payload(client: Any) -> None:
    pid = _seed_project(client, days=40)
    cut = (date(2026, 5, 20) - timedelta(days=20)).isoformat()
    resp = client.post(
        f"/api/prediction/{pid}/causal",
        json={"metric": "sentiment", "intervention_start": cut},
    )
    assert resp.status_code == 200, resp.get_json()
    data = resp.get_json()["data"]
    assert data["kind"] == "causal"
    result = data["result"]
    assert result["status"] == "ok"
    assert "ate" in result
    assert "p_value" in result
    assert result["pre_days"] >= 3
    assert result["post_days"] >= 1


def test_causal_missing_intervention_start_returns_400(client: Any) -> None:
    pid = _seed_project(client)
    resp = client.post(
        f"/api/prediction/{pid}/causal",
        json={"metric": "sentiment"},
    )
    assert resp.status_code == 400


def test_get_run_by_id(client: Any) -> None:
    pid = _seed_project(client)
    run_id = client.post(
        f"/api/prediction/{pid}/forecast",
        json={"metric": "volume", "horizon_days": 5},
    ).get_json()["data"]["id"]
    resp = client.get(f"/api/prediction/runs/{run_id}")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["id"] == run_id


def test_get_unknown_run_returns_404(client: Any) -> None:
    resp = client.get("/api/prediction/runs/does-not-exist")
    assert resp.status_code == 404


def test_list_project_runs_newest_first(client: Any) -> None:
    pid = _seed_project(client)
    client.post(
        f"/api/prediction/{pid}/forecast",
        json={"metric": "volume", "horizon_days": 5},
    )
    client.post(
        f"/api/prediction/{pid}/forecast",
        json={"metric": "sentiment", "horizon_days": 5},
    )
    resp = client.get(f"/api/prediction/{pid}/runs")
    assert resp.status_code == 200
    runs = resp.get_json()["data"]
    assert len(runs) >= 2
    # snapshot should not include the heavy result blob
    assert "result" not in runs[0]


def test_forecast_cache_replays_same_run(client: Any) -> None:
    pid = _seed_project(client)
    body = {"metric": "volume", "horizon_days": 5, "confidence": 0.95}
    a = client.post(f"/api/prediction/{pid}/forecast", json=body).get_json()["data"]
    b = client.post(f"/api/prediction/{pid}/forecast", json=body).get_json()["data"]
    # Same hash → cache replay returns same id.
    assert a["id"] == b["id"]


def test_forecast_surfaces_evidence_ids_and_coverage(client: Any) -> None:
    """Forecast result must carry evidence ids, coverage, confidence, kg block."""
    pid = _seed_project(client, days=20)
    data = client.post(
        f"/api/prediction/{pid}/forecast",
        json={"metric": "volume", "horizon_days": 7},
    ).get_json()["data"]

    # Snapshot fields visible at the run level (no need to dive into result).
    assert isinstance(data["evidence_ids"], list)
    assert "jd:p1" in data["evidence_ids"]
    assert data["coverage"]["record_counts"]["products"] == 1
    assert data["coverage"]["record_counts"]["reviews"] == 5
    assert data["coverage"]["record_counts"]["posts"] >= 20
    assert 0.0 <= data["confidence"]["reliability"] <= 1.0
    assert data["confidence"]["band_level"] == 0.95
    assert data["confidence"]["n_observations"] >= 20

    # Same fields are mirrored inside result for the report layer.
    result = data["result"]
    assert result["evidence_ids"] == data["evidence_ids"]
    assert result["coverage"]["observed_ratio"] >= 0.0
    assert result["confidence"]["mape"] >= 0.0
    # The seed payload feeds product + KOL records, so the KG projection is
    # non-empty and kg_features must surface counts.
    assert result["kg_linked"] is True
    assert result["kg_features"]["node_count"] > 0
    assert data["kg_features"]["node_count"] == result["kg_features"]["node_count"]


def test_causal_surfaces_evidence_ids_and_confidence(client: Any) -> None:
    pid = _seed_project(client, days=40)
    cut = (date(2026, 5, 20) - timedelta(days=20)).isoformat()
    data = client.post(
        f"/api/prediction/{pid}/causal",
        json={"metric": "sentiment", "intervention_start": cut},
    ).get_json()["data"]

    assert "jd:p1" in data["evidence_ids"]
    assert data["coverage"]["pre_days"] >= 3
    assert data["coverage"]["post_days"] >= 1
    assert 0.0 <= data["confidence"]["reliability"] <= 1.0
    assert data["confidence"]["status"] == "ok"
    # The result echoes the evidence chain so report layer doesn't need a
    # second fetch.
    assert data["result"]["evidence_ids"] == data["evidence_ids"]
    assert data["result"]["kg_linked"] is True
    assert data["result"]["kg_features"]["node_count"] > 0
