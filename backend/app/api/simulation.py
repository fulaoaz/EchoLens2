"""/api/simulation blueprint — sync + async (APScheduler + SSE) simulation control.

Endpoints
---------

- POST /api/simulation/<project_id>/run
    Synchronous run — returns the full SimulationResult JSON. Useful for tests
    and for small simulations the caller is willing to block on.

- POST /api/simulation/<project_id>/run_async
    Queue a background job and return its ``job_id`` immediately.

- GET  /api/simulation/jobs/<job_id>
    Snapshot of one job (status, rounds_done/total, last_round_metrics, error).

- GET  /api/simulation/jobs/<job_id>/result
    Full SimulationResult once the job has finished. 409 while still running.

- GET  /api/simulation/jobs/<job_id>/events
    Server-Sent Events stream — emits ``queued`` / ``started`` / ``round`` *
    / ``done`` | ``failed`` | ``cancelled``. Stream closes after the terminal
    event.

- POST /api/simulation/jobs/<job_id>/cancel
    Best-effort cancel — the runner stops between rounds.

- GET  /api/simulation/<project_id>/jobs
    List jobs queued/finished for a project.

- GET  /api/simulation/ping
    Liveness check.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from flask import Blueprint, Response, jsonify, request, stream_with_context
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.crawler.seed_report import build_seed_report
from app.kg.search import get_subgraph
from app.services.crawler_store import get_crawler_store
from app.services.project_store import get_store
from app.services.sim_jobs import (
    cancel_job,
    get_job,
    list_jobs,
    stream_events,
    submit_simulation,
)
from app.simulator.runner import run_simulation_sync

bp = Blueprint("simulation", __name__, url_prefix="/api/simulation")


class CampaignEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round: int = Field(default=0, ge=0)
    stimulus: float = Field(default=0.0, ge=-1.0, le=1.0)
    price_pressure: float = Field(default=0.5, ge=0.0, le=1.0)


class RunSimulationIn(BaseModel):
    """Inbound payload for POST /api/simulation/<id>/run[_async]."""

    model_config = ConfigDict(extra="forbid")

    num_agents: int = Field(default=200, ge=1, le=10_000)
    num_rounds: int = Field(default=20, ge=1, le=200)
    mean_degree: int = Field(default=8, ge=2, le=64)
    target_product_id: str | None = None
    campaign_schedule: list[CampaignEntry] = Field(default_factory=list)
    rng_seed: int | None = None


def _ok(data: Any, status: int = 200) -> tuple[Response, int]:
    return jsonify({"success": True, "data": data}), status


def _err(message: str, status: int) -> tuple[Response, int]:
    return jsonify({"success": False, "error": message}), status


def _resolve_seed_report(
    project_id: str,
) -> tuple[
    tuple[dict[str, Any], dict[str, Any] | None] | None,
    tuple[Response, int] | None,
]:
    """Common preflight — 404 / 409 paths shared by /run and /run_async.

    Returns ``((seed_report, kg_subgraph), None)`` on success, or
    ``(None, error_response)`` on failure. ``kg_subgraph`` is ``None`` when
    the project has no usable graph projection so the runner falls back to
    pure seed-report behavior.
    """
    if not get_store().get(project_id):
        return None, _err(f"project {project_id!r} not found", 404)

    crawler = get_crawler_store()
    seed_report = build_seed_report(
        project_id,
        products=crawler.list_for_project(project_id, "product"),
        reviews=crawler.list_for_project(project_id, "review"),
        posts=crawler.list_for_project(project_id, "post"),
    )
    counts = seed_report["counts"]
    if counts["products"] + counts["reviews"] + counts["posts"] == 0:
        return None, _err(
            "project has no seed data — ingest products/reviews/posts first",
            409,
        )

    # Project-scoped KG projection — feeds the runner so simulation results
    # carry kg_features + evidence_ids automatically. If the projection is
    # empty (e.g. only-products with no usable entities) we pass ``None`` so
    # the runner stays in pre-KG behavior rather than reporting kg_linked.
    try:
        subgraph = get_subgraph(project_id)
    except Exception:  # noqa: BLE001 — KG projection must not block /run
        subgraph = {"nodes": [], "edges": []}
    kg_subgraph: dict[str, Any] | None = subgraph if subgraph.get("nodes") else None

    return (seed_report, kg_subgraph), None


def _parse_payload() -> tuple[RunSimulationIn | None, tuple[Response, int] | None]:
    raw = request.get_json(silent=True) or {}
    try:
        return RunSimulationIn.model_validate(raw), None
    except ValidationError as exc:
        return None, _err(str(exc), 400)


@bp.get("/ping")
def ping() -> tuple[Response, int]:
    return _ok({"module": "simulation", "implemented": True})


@bp.post("/<project_id>/run")
def run(project_id: str) -> tuple[Response, int]:
    """Execute one simulation synchronously (blocking)."""
    bundle, err = _resolve_seed_report(project_id)
    if err is not None:
        return err
    payload, err = _parse_payload()
    if err is not None:
        return err
    assert bundle is not None and payload is not None
    seed_report, kg_subgraph = bundle

    result = run_simulation_sync(
        seed_report,
        num_agents=payload.num_agents,
        num_rounds=payload.num_rounds,
        mean_degree=payload.mean_degree,
        target_product_id=payload.target_product_id,
        campaign_schedule=[e.model_dump() for e in payload.campaign_schedule],
        rng_seed=payload.rng_seed,
        kg_subgraph=kg_subgraph,
    )
    get_store().update(project_id, status="simulating")
    return _ok(result.to_dict())


@bp.post("/<project_id>/run_async")
def run_async(project_id: str) -> tuple[Response, int]:
    """Queue an async simulation job — returns immediately with a job_id."""
    bundle, err = _resolve_seed_report(project_id)
    if err is not None:
        return err
    payload, err = _parse_payload()
    if err is not None:
        return err
    assert bundle is not None and payload is not None
    seed_report, kg_subgraph = bundle

    job = submit_simulation(
        project_id,
        seed_report,
        num_agents=payload.num_agents,
        num_rounds=payload.num_rounds,
        mean_degree=payload.mean_degree,
        target_product_id=payload.target_product_id,
        campaign_schedule=[e.model_dump() for e in payload.campaign_schedule],
        rng_seed=payload.rng_seed,
        kg_subgraph=kg_subgraph,
    )
    get_store().update(project_id, status="simulating")
    return _ok(job.snapshot(), status=202)


@bp.get("/jobs/<job_id>")
def job_status(job_id: str) -> tuple[Response, int]:
    job = get_job(job_id)
    if job is None:
        return _err(f"job {job_id!r} not found", 404)
    return _ok(job.snapshot())


@bp.get("/jobs/<job_id>/result")
def job_result(job_id: str) -> tuple[Response, int]:
    job = get_job(job_id)
    if job is None:
        return _err(f"job {job_id!r} not found", 404)
    if job.status in {"pending", "running"}:
        return _err(f"job is still {job.status}", 409)
    if job.status == "failed":
        return _err(job.error or "simulation failed", 500)
    return _ok(job.result or {})


@bp.post("/jobs/<job_id>/cancel")
def job_cancel(job_id: str) -> tuple[Response, int]:
    if get_job(job_id) is None:
        return _err(f"job {job_id!r} not found", 404)
    cancelled = cancel_job(job_id)
    return _ok({"cancelled": cancelled, "job_id": job_id})


@bp.get("/jobs/<job_id>/events")
def job_events(job_id: str) -> Response:
    """Server-Sent Events stream of the job's progress."""
    if get_job(job_id) is None:
        return Response(
            json.dumps({"success": False, "error": f"job {job_id!r} not found"}),
            status=404,
            mimetype="application/json",
        )

    def _stream() -> Iterator[str]:
        for ev in stream_events(job_id, timeout=15.0):
            payload = {
                "type": ev.type,
                "timestamp": ev.timestamp,
                **ev.payload,
            }
            yield f"event: {ev.type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    response = Response(stream_with_context(_stream()), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@bp.get("/<project_id>/jobs")
def project_jobs(project_id: str) -> tuple[Response, int]:
    if not get_store().get(project_id):
        return _err(f"project {project_id!r} not found", 404)
    jobs = list_jobs(project_id)
    # Newest first.
    jobs.sort(key=lambda j: j.created_at, reverse=True)
    return _ok([j.snapshot() for j in jobs])
