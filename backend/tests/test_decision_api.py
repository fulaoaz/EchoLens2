"""End-to-end tests for the /api/decision blueprint (M4.3).

Covers four scenarios:
- Unknown project → 404.
- Project exists, no sim/pred data → snapshot returns with all coverage flags false
  and a "missing-sim" recommendation.
- Project with only forecast data → forecast block populated, sim/causal absent.
- Project with sim + forecast + causal → all three blocks present, risk score
  reflects fused signals.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest

from app.services import prediction_jobs, sim_jobs
from app.services.crawler_store import get_crawler_store
from app.services.prediction_jobs import CausalParams, ForecastParams
from app.services.project_store import get_store
from app.kg.search import get_subgraph


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch) -> None:
    get_store().clear()
    get_crawler_store().clear()
    prediction_jobs.reset_for_tests()
    sim_jobs.reset_for_tests()

    # Force sim_jobs.submit_simulation to run inline so we don't race with the
    # APScheduler thread when seeding test data.
    real_submit = sim_jobs.submit_simulation

    def _sync_submit(*args: Any, **kwargs: Any) -> Any:
        kwargs["sync"] = True
        return real_submit(*args, **kwargs)

    monkeypatch.setattr(sim_jobs, "submit_simulation", _sync_submit)


# ---------- helpers -----------------------------------------------------------


def _seed_project_with_history(client: Any, *, name: str = "dec", days: int = 30) -> str:
    """Create a project + crawler history sufficient for forecast/causal."""
    pid = client.post(
        "/api/projects", json={"name": name, "keywords": ["k"]}
    ).get_json()["data"]["id"]

    today = date(2026, 5, 20)
    posts = []
    for i in range(days):
        d = (today - timedelta(days=days - 1 - i)).isoformat()
        for j in range(1 + i // 3):
            posts.append(
                {
                    "platform": "weibo",
                    "id": f"w-{i}-{j}",
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


def _seed_report(pid: str) -> dict[str, Any]:
    """Minimal seed_report shape accepted by sim_jobs.submit_simulation."""
    return {
        "project_id": pid,
        "products": [
            {
                "platform": "jd",
                "id": "jd:p1",
                "title": "Demo",
                "brand": "Demo",
                "price_current": 199.0,
            }
        ],
        "reviews": [],
        "posts": [],
    }


# ---------- tests -------------------------------------------------------------


def test_ping_reports_implemented(client: Any) -> None:
    resp = client.get("/api/decision/ping")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["data"]["implemented"] is True


def test_snapshot_unknown_project_returns_404(client: Any) -> None:
    resp = client.get("/api/decision/missing/snapshot")
    assert resp.status_code == 404
    body = resp.get_json()
    assert body["success"] is False


def test_snapshot_empty_project_returns_default_recommendation(client: Any) -> None:
    pid = client.post(
        "/api/projects", json={"name": "empty", "keywords": ["k"]}
    ).get_json()["data"]["id"]

    resp = client.get(f"/api/decision/{pid}/snapshot")
    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()["data"]

    assert data["project_id"] == pid
    assert data["coverage"] == {
        "simulation": False,
        "forecast": False,
        "causal": False,
    }
    assert data["simulation"] is None
    assert data["forecast"] is None
    assert data["causal"] is None
    assert data["risk"]["score"] == 0
    assert data["risk"]["level"] == "low"

    # No sim/pred → must always have at least the "先跑仿真" prompt.
    rec_ids = [r["id"] for r in data["recommendations"]]
    assert "missing-sim" in rec_ids
    # All recommendations carry the required schema.
    for rec in data["recommendations"]:
        assert {"id", "title", "priority", "rationale", "evidence", "tags"} <= rec.keys()
    assert data["model"] == "decision-rules-v1"


def test_snapshot_with_only_forecast_populates_forecast_block(client: Any) -> None:
    pid = _seed_project_with_history(client)

    # Trigger one forecast run via the real prediction service.
    prediction_jobs.run_forecast(
        ForecastParams(project_id=pid, metric="volume", horizon_days=7)
    )

    resp = client.get(f"/api/decision/{pid}/snapshot")
    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()["data"]

    assert data["coverage"]["forecast"] is True
    assert data["coverage"]["simulation"] is False
    assert data["coverage"]["causal"] is False

    fc = data["forecast"]
    assert fc is not None
    assert fc["metric"] == "volume"
    assert "headline" in fc
    assert "diagnostics" in fc
    assert "history" in fc and isinstance(fc["history"], list)
    assert "forecast" in fc and len(fc["forecast"]) == 7
    assert isinstance(data["recommendations"], list) and data["recommendations"]


def test_snapshot_with_full_coverage_fuses_all_signals(client: Any) -> None:
    pid = _seed_project_with_history(client, days=40)

    # Run a tiny synchronous simulation so list_jobs has a completed entry.
    sim_jobs.submit_simulation(
        pid,
        _seed_report(pid),
        num_agents=20,
        num_rounds=3,
        mean_degree=4,
        rng_seed=11,
        sync=True,
    )

    # Forecast + causal runs.
    prediction_jobs.run_forecast(
        ForecastParams(project_id=pid, metric="volume", horizon_days=7)
    )
    cut = (date(2026, 5, 20) - timedelta(days=20)).isoformat()
    prediction_jobs.run_causal(
        CausalParams(project_id=pid, metric="sentiment", intervention_start=cut)
    )

    resp = client.get(f"/api/decision/{pid}/snapshot")
    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()["data"]

    assert data["coverage"] == {
        "simulation": True,
        "forecast": True,
        "causal": True,
    }
    assert data["simulation"] is not None
    assert data["forecast"] is not None
    assert data["causal"] is not None

    sim_block = data["simulation"]
    assert "last_round" in sim_block
    assert "population" in sim_block
    assert sim_block["rounds_total"] >= 1

    risk = data["risk"]
    assert 0 <= risk["score"] <= 100
    assert risk["level"] in {"low", "elevated", "high"}
    assert isinstance(risk["reasons"], list)

    # 1-5 recommendations, no "missing-sim" since simulation is present.
    recs = data["recommendations"]
    assert 1 <= len(recs) <= 5
    assert all(r["id"] != "missing-sim" for r in recs)


def test_snapshot_surfaces_evidence_chain_and_kg(client: Any) -> None:
    """The snapshot must thread evidence/kg/coverage/confidence through to the root.

    Each recommendation must also carry ``source_run_ids`` so the dashboard can
    deep-link back to the originating sim/forecast/causal run.
    """
    pid = _seed_project_with_history(client, days=40)

    sim_job = sim_jobs.submit_simulation(
        pid,
        _seed_report(pid),
        num_agents=20,
        num_rounds=3,
        mean_degree=4,
        rng_seed=11,
        kg_subgraph=get_subgraph(pid) or None,
        sync=True,
    )
    fc_run = prediction_jobs.run_forecast(
        ForecastParams(project_id=pid, metric="volume", horizon_days=7)
    )
    cut = (date(2026, 5, 20) - timedelta(days=20)).isoformat()
    causal_run = prediction_jobs.run_causal(
        CausalParams(project_id=pid, metric="sentiment", intervention_start=cut)
    )

    data = client.get(f"/api/decision/{pid}/snapshot").get_json()["data"]

    # Top-level evidence chain — union of sim + forecast + causal.
    assert "jd:p1" in data["evidence_ids"]
    assert data["kg_linked"] is True
    assert data["kg_features"]["node_count"] > 0

    # source_run_ids round-trips ids back to the underlying runs.
    assert data["source_run_ids"]["simulation"] == sim_job.id
    assert data["source_run_ids"]["forecast"] == fc_run.id
    assert data["source_run_ids"]["causal"] == causal_run.id

    # Per-block evidence + kg surfaces follow through.
    assert "jd:p1" in data["simulation"]["evidence_ids"]
    assert data["forecast"]["kg_linked"] is True
    assert data["forecast"]["kg_features"]["node_count"] > 0
    assert data["forecast"]["confidence"]["band_level"] == 0.95
    assert 0.0 <= data["forecast"]["confidence"]["reliability"] <= 1.0
    assert data["causal"]["kg_linked"] is True
    assert data["causal"]["confidence"]["status"] == "ok"

    # Confidence rollup blends forecast + causal reliabilities.
    rollup = data["confidence"]
    assert "forecast" in rollup and "causal" in rollup
    assert 0.0 <= rollup["reliability"] <= 1.0

    # Every rec has source_run_ids; recs that depend on a specific run cite it.
    recs = data["recommendations"]
    for rec in recs:
        assert "source_run_ids" in rec
        assert isinstance(rec["source_run_ids"], dict)
    by_id = {r["id"]: r for r in recs}
    if "crisis-response" in by_id or "sentiment-recovery" in by_id:
        sim_rec = by_id.get("crisis-response") or by_id["sentiment-recovery"]
        assert sim_rec["source_run_ids"].get("simulation") == sim_job.id
    if "defensive-budget" in by_id or "amplify-momentum" in by_id or "tighten-forecast" in by_id:
        fc_rec = (
            by_id.get("defensive-budget")
            or by_id.get("amplify-momentum")
            or by_id["tighten-forecast"]
        )
        assert fc_rec["source_run_ids"].get("forecast") == fc_run.id


def test_snapshot_source_run_ids_resolve_to_live_runs(client: Any) -> None:
    """Audit-trail invariant: every ``source_run_ids`` id surfaced by the
    decision snapshot — both at the root and on each recommendation — must
    resolve back to a live Run in the sim/prediction registries belonging to
    the same project.

    String equality ``snapshot.source_run_ids.simulation == sim_job.id`` is
    necessary but not sufficient: the dashboard deep-links the chips back to
    the registries via ``sim_jobs.get_job`` / ``prediction_jobs.get_run``,
    and a stale id (e.g. after a registry eviction) would silently render a
    dead chip. This test locks the round-trip resolvability so an LRU
    boundary regression fails loudly.
    """
    pid = _seed_project_with_history(client, days=40)

    sim_job = sim_jobs.submit_simulation(
        pid,
        _seed_report(pid),
        num_agents=20,
        num_rounds=3,
        mean_degree=4,
        rng_seed=11,
        kg_subgraph=get_subgraph(pid) or None,
        sync=True,
    )
    fc_run = prediction_jobs.run_forecast(
        ForecastParams(project_id=pid, metric="volume", horizon_days=7)
    )
    cut = (date(2026, 5, 20) - timedelta(days=20)).isoformat()
    causal_run = prediction_jobs.run_causal(
        CausalParams(project_id=pid, metric="sentiment", intervention_start=cut)
    )

    data = client.get(f"/api/decision/{pid}/snapshot").get_json()["data"]

    def _resolve_kind(kind: str, run_id: str) -> None:
        if kind == "simulation":
            job = sim_jobs.get_job(run_id)
            assert job is not None, f"sim run {run_id} missing from registry"
            assert job.project_id == pid, (
                f"sim run {run_id} belongs to {job.project_id}, expected {pid}"
            )
        elif kind in ("forecast", "causal"):
            run = prediction_jobs.get_run(run_id)
            assert run is not None, f"{kind} run {run_id} missing from registry"
            assert run.project_id == pid, (
                f"{kind} run {run_id} belongs to {run.project_id}, expected {pid}"
            )
            assert run.kind == kind, (
                f"{kind} run {run_id} stored as kind={run.kind}, expected {kind}"
            )
        else:
            raise AssertionError(f"unexpected source_run_ids kind {kind!r}")

    # Root-level audit trail must resolve cleanly.
    root_sources = data["source_run_ids"]
    assert root_sources["simulation"] == sim_job.id
    assert root_sources["forecast"] == fc_run.id
    assert root_sources["causal"] == causal_run.id
    for kind, rid in root_sources.items():
        if rid is None:
            continue
        _resolve_kind(kind, rid)

    # Per-recommendation audit trail: every cited id must round-trip too,
    # otherwise the UI's "open run" chip would dangle.
    for rec in data["recommendations"]:
        for kind, rid in (rec.get("source_run_ids") or {}).items():
            if rid is None:
                continue
            _resolve_kind(kind, rid)
