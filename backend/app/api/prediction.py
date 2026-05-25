"""/api/prediction blueprint — synchronous forecasting + DiD causal analysis.

Endpoints
---------

- POST /api/prediction/<project_id>/forecast
    Run a time-series forecast on one metric. Returns the registered
    ``PredictionRun`` (snapshot + full result).

- POST /api/prediction/<project_id>/causal
    Run a DiD ATE estimate around an intervention date.

- GET  /api/prediction/runs/<run_id>
    Fetch the full result of one finished run.

- GET  /api/prediction/<project_id>/runs
    List recent runs for a project (newest first).

- GET  /api/prediction/ping
    Liveness check — implemented=True, kept for diagnostics.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, jsonify, request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.predictor.history import ALL_METRICS
from app.services.prediction_jobs import (
    CausalParams,
    ForecastParams,
    get_run,
    list_runs,
    run_causal,
    run_forecast,
)
from app.services.project_store import get_store

bp = Blueprint("prediction", __name__, url_prefix="/api/prediction")


# ---------- payloads ----------------------------------------------------------


class ForecastIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str = Field(default="gmv_synth")
    horizon_days: int = Field(default=14, ge=1, le=200)
    seasonality_period: int = Field(default=7, ge=1, le=30)
    confidence: float = Field(default=0.95, ge=0.5, lt=1.0)


class CausalIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str = Field(default="sentiment")
    intervention_start: str = Field(min_length=1)
    intervention_end: str | None = None


# ---------- helpers -----------------------------------------------------------


def _ok(data: Any, status: int = 200) -> tuple[Response, int]:
    return jsonify({"success": True, "data": data}), status


def _err(message: str, status: int) -> tuple[Response, int]:
    return jsonify({"success": False, "error": message}), status


def _check_project(project_id: str) -> tuple[Response, int] | None:
    if not get_store().get(project_id):
        return _err(f"project {project_id!r} not found", 404)
    return None


def _validate_metric(metric: str) -> tuple[Response, int] | None:
    if metric not in ALL_METRICS:
        return _err(
            f"unknown metric {metric!r}; expected one of {list(ALL_METRICS)}",
            400,
        )
    return None


# ---------- routes ------------------------------------------------------------


@bp.get("/ping")
def ping() -> tuple[Response, int]:
    return _ok({"module": "prediction", "implemented": True})


@bp.post("/<project_id>/forecast")
def forecast(project_id: str) -> tuple[Response, int]:
    err = _check_project(project_id)
    if err is not None:
        return err

    raw = request.get_json(silent=True) or {}
    try:
        payload = ForecastIn.model_validate(raw)
    except ValidationError as exc:
        return _err(str(exc), 400)

    err = _validate_metric(payload.metric)
    if err is not None:
        return err

    try:
        run = run_forecast(
            ForecastParams(
                project_id=project_id,
                metric=payload.metric,  # type: ignore[arg-type]
                horizon_days=payload.horizon_days,
                seasonality_period=payload.seasonality_period,
                confidence=payload.confidence,
            )
        )
    except ValueError as exc:
        return _err(str(exc), 400)
    return _ok(run.full())


@bp.post("/<project_id>/causal")
def causal(project_id: str) -> tuple[Response, int]:
    err = _check_project(project_id)
    if err is not None:
        return err

    raw = request.get_json(silent=True) or {}
    try:
        payload = CausalIn.model_validate(raw)
    except ValidationError as exc:
        return _err(str(exc), 400)

    err = _validate_metric(payload.metric)
    if err is not None:
        return err

    try:
        run = run_causal(
            CausalParams(
                project_id=project_id,
                metric=payload.metric,  # type: ignore[arg-type]
                intervention_start=payload.intervention_start,
                intervention_end=payload.intervention_end,
            )
        )
    except ValueError as exc:
        return _err(str(exc), 400)
    return _ok(run.full())


@bp.get("/runs/<run_id>")
def get_run_route(run_id: str) -> tuple[Response, int]:
    run = get_run(run_id)
    if run is None:
        return _err(f"run {run_id!r} not found", 404)
    return _ok(run.full())


@bp.get("/<project_id>/runs")
def project_runs(project_id: str) -> tuple[Response, int]:
    err = _check_project(project_id)
    if err is not None:
        return err
    runs = list_runs(project_id)
    runs.sort(key=lambda r: r.created_at, reverse=True)
    return _ok([r.snapshot() for r in runs])
