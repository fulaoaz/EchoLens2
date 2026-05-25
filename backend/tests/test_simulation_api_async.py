"""End-to-end tests for the async simulation pipeline (M2.2).

Covers the four new HTTP surfaces:
- POST /api/simulation/<id>/run_async
- GET  /api/simulation/jobs/<id>
- GET  /api/simulation/jobs/<id>/result
- GET  /api/simulation/jobs/<id>/events  (SSE)
- POST /api/simulation/jobs/<id>/cancel

All async tests run in ``sync=True`` mode through ``submit_simulation`` to
avoid the APScheduler thread + flaky timing — the HTTP path itself is exercised
via a small monkeypatch that pins ``sync=True`` for the duration of each test.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.services import sim_jobs
from app.services.crawler_store import get_crawler_store
from app.services.project_store import get_store


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch) -> None:
    get_store().clear()
    get_crawler_store().clear()
    sim_jobs.reset_for_tests()

    # Force inline execution so /run_async finishes before we poll /jobs/<id>.
    real_submit = sim_jobs.submit_simulation

    def _sync_submit(*args: Any, **kwargs: Any) -> Any:
        kwargs["sync"] = True
        return real_submit(*args, **kwargs)

    monkeypatch.setattr("app.api.simulation.submit_simulation", _sync_submit)


def _create_project_with_seed(client: Any, name: str = "sim-async") -> str:
    pid = client.post("/api/projects", json={"name": name, "keywords": ["k"]}).get_json()["data"]["id"]
    client.post(
        f"/api/projects/{pid}/seed_data",
        json={
            "products": [
                {
                    "platform": "jd",
                    "id": "jd:demo",
                    "title": "Anker 移动电源",
                    "brand": "Anker",
                    "price_current": 599.0,
                }
            ],
            "reviews": [
                {"platform": "jd", "id": "r1", "content": "好", "sentiment": "positive"},
                {"platform": "jd", "id": "r2", "content": "差", "sentiment": "negative"},
            ],
            "posts": [
                {
                    "platform": "weibo",
                    "id": "w1",
                    "author_hash": "kol_alice_aaaaaa",
                    "content": "推荐",
                    "sentiment": "positive",
                    "posted_at": "2026-05-18T10:00:00",
                }
            ],
        },
    )
    return pid


def test_run_async_returns_202_and_job_id(client: Any) -> None:
    pid = _create_project_with_seed(client)
    resp = client.post(
        f"/api/simulation/{pid}/run_async",
        json={"num_agents": 50, "num_rounds": 3, "rng_seed": 7},
    )
    assert resp.status_code == 202, resp.get_data(as_text=True)
    body = resp.get_json()["data"]
    assert "id" in body and len(body["id"]) >= 16
    assert body["project_id"] == pid
    assert body["total_rounds"] == 3
    assert body["status"] in {"pending", "running", "completed"}


def test_run_async_404_for_missing_project(client: Any) -> None:
    resp = client.post("/api/simulation/missing/run_async", json={})
    assert resp.status_code == 404


def test_run_async_409_when_no_seed_data(client: Any) -> None:
    pid = client.post("/api/projects", json={"name": "empty"}).get_json()["data"]["id"]
    resp = client.post(f"/api/simulation/{pid}/run_async", json={})
    assert resp.status_code == 409


def test_run_async_400_for_invalid_payload(client: Any) -> None:
    pid = _create_project_with_seed(client)
    resp = client.post(
        f"/api/simulation/{pid}/run_async",
        json={"num_agents": -1},
    )
    assert resp.status_code == 400


def test_job_status_then_result(client: Any) -> None:
    pid = _create_project_with_seed(client)
    job_id = client.post(
        f"/api/simulation/{pid}/run_async",
        json={"num_agents": 40, "num_rounds": 4, "rng_seed": 11},
    ).get_json()["data"]["id"]

    snap = client.get(f"/api/simulation/jobs/{job_id}").get_json()["data"]
    assert snap["status"] == "completed"
    assert snap["rounds_done"] == 4
    assert snap["total_rounds"] == 4
    assert snap["last_round_metrics"]["round"] == 3

    full = client.get(f"/api/simulation/jobs/{job_id}/result").get_json()["data"]
    assert full["project_id"] == pid
    assert len(full["rounds"]) == 4
    assert len(full["final_sentiment"]) == 40


def test_job_status_404_for_missing_job(client: Any) -> None:
    resp = client.get("/api/simulation/jobs/nonexistent/")
    # Trailing slash is normalised; both 404 and the missing-job 404 are fine.
    assert resp.status_code in {404, 308}


def test_job_result_404(client: Any) -> None:
    resp = client.get("/api/simulation/jobs/missing/result")
    assert resp.status_code == 404


def test_project_jobs_lists_runs(client: Any) -> None:
    pid = _create_project_with_seed(client)
    for _ in range(2):
        client.post(
            f"/api/simulation/{pid}/run_async",
            json={"num_agents": 30, "num_rounds": 2, "rng_seed": 1},
        )
    listing = client.get(f"/api/simulation/{pid}/jobs").get_json()["data"]
    assert len(listing) == 2
    assert all(j["project_id"] == pid for j in listing)


def test_project_jobs_404(client: Any) -> None:
    resp = client.get("/api/simulation/missing/jobs")
    assert resp.status_code == 404


def test_sse_event_stream_emits_round_and_done(client: Any) -> None:
    pid = _create_project_with_seed(client)
    job_id = client.post(
        f"/api/simulation/{pid}/run_async",
        json={"num_agents": 20, "num_rounds": 3, "rng_seed": 5},
    ).get_json()["data"]["id"]

    resp = client.get(f"/api/simulation/jobs/{job_id}/events")
    assert resp.status_code == 200
    assert resp.mimetype == "text/event-stream"

    chunks = b"".join(resp.response).decode("utf-8")
    # Each event is "event: <type>\ndata: <json>\n\n".
    assert "event: queued" in chunks
    assert "event: started" in chunks
    assert chunks.count("event: round") == 3
    assert "event: done" in chunks

    # Parse the last 'done' record and check it carries final_action_totals.
    done_block = chunks.split("event: done", 1)[1]
    data_line = next(
        line for line in done_block.splitlines() if line.startswith("data: ")
    )
    done_payload = json.loads(data_line.removeprefix("data: "))
    assert done_payload["rounds"] == 3
    assert "final_action_totals" in done_payload


def test_cancel_job_after_completion_returns_false(client: Any) -> None:
    pid = _create_project_with_seed(client)
    job_id = client.post(
        f"/api/simulation/{pid}/run_async",
        json={"num_agents": 20, "num_rounds": 2, "rng_seed": 3},
    ).get_json()["data"]["id"]
    # Job completed inline → cancel flag has nothing to do.
    body = client.post(f"/api/simulation/jobs/{job_id}/cancel").get_json()["data"]
    assert body["cancelled"] is False
    assert body["job_id"] == job_id


def test_cancel_404_for_missing_job(client: Any) -> None:
    resp = client.post("/api/simulation/jobs/missing/cancel")
    assert resp.status_code == 404


def test_run_async_flips_project_status(client: Any) -> None:
    pid = _create_project_with_seed(client)
    client.post(
        f"/api/simulation/{pid}/run_async",
        json={"num_agents": 20, "num_rounds": 2, "rng_seed": 1},
    )
    detail = client.get(f"/api/projects/{pid}").get_json()["data"]
    assert detail["status"] == "simulating"


def test_sim_jobs_unit_round_metrics_progress() -> None:
    """Direct unit test on the runner-with-callback path."""
    from app.crawler.seed_report import build_seed_report

    sr = build_seed_report(
        "p-unit",
        products=[{"platform": "jd", "id": "x", "title": "T", "brand": "B", "price_current": 9}],
        reviews=[{"platform": "jd", "id": "r", "sentiment": "positive"}],
        posts=[],
    )
    received: list[int] = []

    job = sim_jobs.submit_simulation(
        "p-unit",
        sr,
        num_agents=15,
        num_rounds=3,
        rng_seed=42,
        sync=True,
    )
    # Drain queue.
    for ev in sim_jobs.stream_events(job.id, timeout=1.0):
        if ev.type == "round":
            received.append(ev.payload["round"])
        if ev.type in {"done", "failed"}:
            break
    assert received == [0, 1, 2]
    assert job.status == "completed"
    assert job.rounds_done == 3


def test_run_async_surfaces_kg_features_and_evidence_ids(client: Any) -> None:
    """End-to-end: KG projection from CrawlerStore reaches the async result."""
    pid = _create_project_with_seed(client, name="sim-kg")
    job_id = client.post(
        f"/api/simulation/{pid}/run_async",
        json={"num_agents": 30, "num_rounds": 3, "rng_seed": 17},
    ).get_json()["data"]["id"]

    full = client.get(f"/api/simulation/jobs/{job_id}/result").get_json()["data"]
    assert full["config"]["kg_linked"] is True
    # The seed payload above feeds product + post + review records, so the
    # KG projection must surface a non-empty kg_features block.
    features = full["network"]["kg_features"]
    assert features["node_count"] > 0
    assert features["edge_count"] > 0
    # Evidence ids carry through to the top-level field for the report layer.
    assert "jd:demo" in full["evidence_ids"]
    # Posts are seeded with raw record id "w1" (no platform prefix), so the
    # evidence chain must surface that id alongside the product.
    assert "w1" in full["evidence_ids"]

    # Done SSE event also carries the evidence chain so the frontend can
    # update the decision/report panels without re-fetching.
    chunks = b"".join(
        client.get(f"/api/simulation/jobs/{job_id}/events").response
    ).decode("utf-8")
    done_block = chunks.split("event: done", 1)[1]
    data_line = next(
        line for line in done_block.splitlines() if line.startswith("data: ")
    )
    done_payload = json.loads(data_line.removeprefix("data: "))
    assert done_payload["kg_linked"] is True
    assert "jd:demo" in done_payload["evidence_ids"]


def test_run_sync_surfaces_kg_features_and_evidence_ids(client: Any) -> None:
    """The synchronous /run path mirrors the async kg payload."""
    pid = _create_project_with_seed(client, name="sim-kg-sync")
    body = client.post(
        f"/api/simulation/{pid}/run",
        json={"num_agents": 25, "num_rounds": 2, "rng_seed": 23},
    ).get_json()["data"]
    assert body["config"]["kg_linked"] is True
    assert body["network"]["kg_features"]["node_count"] > 0
    assert body["evidence_ids"], "sync run must surface evidence ids"
