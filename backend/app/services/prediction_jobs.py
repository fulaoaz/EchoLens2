"""Prediction job runner — synchronous + LRU-cached.

Unlike simulation, prediction is fast (<2 s for a 90-day horizon) and
deterministic. We don't need APScheduler or SSE here. The runner:

1. Loads raw records from ``crawler_store``.
2. Builds the daily history series via ``predictor.history``.
3. Runs the chosen branch (forecast / causal / both).
4. Caches results by ``(project_id, params_hash)`` so a repeated request from
   the dashboard returns instantly without refitting.

Each finished run is also persisted in an in-memory registry keyed by ``id``
so the frontend can list "recent prediction runs" without re-running.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from app.kg.search import get_subgraph
from app.predictor import causal as causal_mod
from app.predictor.explainer import explain_forecast
from app.predictor.history import (
    ALL_METRICS,
    HistorySeries,
    MetricName,
    build_history,
    extract_metric,
)
from app.predictor.timeseries import ForecastResult, forecast_series
from app.services.crawler_store import get_crawler_store
from app.simulator.runner import summarize_kg

PredictionKind = Literal["forecast", "causal", "fused"]
PredictionStatus = Literal["completed", "failed"]


# ---------- params + records --------------------------------------------------


@dataclass(frozen=True)
class ForecastParams:
    project_id: str
    metric: MetricName = "gmv_synth"
    horizon_days: int = 14
    seasonality_period: int = 7
    confidence: float = 0.95

    def hash_key(self) -> str:
        payload = json.dumps(self.__dict__, sort_keys=True).encode("utf-8")
        return hashlib.sha1(payload).hexdigest()[:16]


@dataclass(frozen=True)
class CausalParams:
    project_id: str
    metric: MetricName = "sentiment"
    intervention_start: str = ""  # ISO date — required at validation time
    intervention_end: str | None = None

    def hash_key(self) -> str:
        payload = json.dumps(self.__dict__, sort_keys=True).encode("utf-8")
        return hashlib.sha1(payload).hexdigest()[:16]


@dataclass
class PredictionRun:
    """In-memory record of one finished prediction."""

    id: str
    project_id: str
    kind: PredictionKind
    status: PredictionStatus
    created_at: str
    metric: MetricName
    config: dict[str, Any]
    result: dict[str, Any]
    error: str | None = None
    evidence_ids: list[str] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)
    confidence: dict[str, Any] = field(default_factory=dict)
    kg_features: dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "kind": self.kind,
            "status": self.status,
            "created_at": self.created_at,
            "metric": self.metric,
            "config": self.config,
            "error": self.error,
            "evidence_ids": list(self.evidence_ids),
            "coverage": dict(self.coverage),
            "confidence": dict(self.confidence),
            "kg_features": dict(self.kg_features),
        }

    def full(self) -> dict[str, Any]:
        return {**self.snapshot(), "result": self.result}


# ---------- registry + cache --------------------------------------------------


class _PredictionRegistry:
    """Thread-safe in-memory registry keyed by run id."""

    _MAX_RUNS = 64

    def __init__(self) -> None:
        self._runs: OrderedDict[str, PredictionRun] = OrderedDict()
        self._lock = threading.Lock()

    def add(self, run: PredictionRun) -> None:
        with self._lock:
            self._runs[run.id] = run
            self._runs.move_to_end(run.id)
            while len(self._runs) > self._MAX_RUNS:
                self._runs.popitem(last=False)

    def get(self, run_id: str) -> PredictionRun | None:
        with self._lock:
            return self._runs.get(run_id)

    def list_for_project(self, project_id: str | None = None) -> list[PredictionRun]:
        with self._lock:
            runs = list(self._runs.values())
        if project_id is None:
            return runs
        return [r for r in runs if r.project_id == project_id]

    def clear(self) -> None:
        with self._lock:
            self._runs.clear()


class _ResultCache:
    """LRU cache for repeat queries — keys are pre-hashed by params."""

    _MAX_ENTRIES = 32

    def __init__(self) -> None:
        self._items: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            value = self._items.get(key)
            if value is not None:
                self._items.move_to_end(key)
            return value

    def put(self, key: str, value: dict[str, Any]) -> None:
        with self._lock:
            self._items[key] = value
            self._items.move_to_end(key)
            while len(self._items) > self._MAX_ENTRIES:
                self._items.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


_registry = _PredictionRegistry()
_cache = _ResultCache()


# ---------- history loading ---------------------------------------------------


def _record_evidence_ids(records: list[dict[str, Any]]) -> list[str]:
    """Pull stable record ids from a CrawlerStore record list.

    The crawler stores records keyed by ``(platform, id)``. We surface the
    raw ``id`` (without the platform prefix) to mirror the simulator's
    evidence-chain conventions, so downstream report layers can cross-link
    crawler hits, KG nodes, and simulation runs by the same id space.
    """
    ids: list[str] = []
    for rec in records:
        rid = rec.get("id")
        if isinstance(rid, str) and rid:
            ids.append(rid)
    return ids


def _load_history(project_id: str) -> tuple[HistorySeries, list[str]]:
    """Pull crawler records, derive the daily series, and return record ids."""
    store = get_crawler_store()
    products = store.list_for_project(project_id, "product")
    reviews = store.list_for_project(project_id, "review")
    posts = store.list_for_project(project_id, "post")
    history = build_history(
        project_id,
        products=products,
        reviews=reviews,
        posts=posts,
    )
    record_ids = sorted(
        set(
            _record_evidence_ids(products)
            + _record_evidence_ids(reviews)
            + _record_evidence_ids(posts)
        )
    )
    return history, record_ids


def _load_kg_context(project_id: str) -> tuple[dict[str, Any], list[str]]:
    """Project-scoped KG features + evidence ids, defensive against failures."""
    try:
        subgraph = get_subgraph(project_id)
    except Exception:  # noqa: BLE001 — KG projection must not break prediction
        subgraph = {"nodes": [], "edges": []}
    kg_subgraph: dict[str, Any] | None = subgraph if subgraph.get("nodes") else None
    features, evidence_ids = summarize_kg(kg_subgraph)
    return features, evidence_ids


def _merge_evidence_ids(*sources: list[str]) -> list[str]:
    seen: set[str] = set()
    for src in sources:
        for eid in src:
            if eid:
                seen.add(eid)
    return sorted(seen)


# ---------- public runners ----------------------------------------------------


def run_forecast(params: ForecastParams) -> PredictionRun:
    """Synchronous forecast — returns a registered ``PredictionRun``."""
    if params.metric not in ALL_METRICS:
        raise ValueError(
            f"unknown metric {params.metric!r}; expected one of {ALL_METRICS}"
        )

    cache_key = f"forecast:{params.hash_key()}"
    cached = _cache.get(cache_key)
    if cached is not None:
        run = PredictionRun(**cached)
        _registry.add(run)
        return run

    history, record_ids = _load_history(params.project_id)
    series = extract_metric(history, params.metric)
    history_dates = [p["date"] for p in history["points"]]

    floor = None if params.metric == "sentiment" else 0.0
    result: ForecastResult = forecast_series(
        series,
        horizon_days=params.horizon_days,
        history_dates=history_dates,
        seasonality_period=params.seasonality_period,
        confidence=params.confidence,
        floor=floor,
    )
    explanation = explain_forecast(
        metric=params.metric,
        history=history,
        result=result,
    )

    kg_features, kg_evidence_ids = _load_kg_context(params.project_id)
    coverage = dict(history["coverage"])
    coverage["history_days"] = history["days"]

    diag = result.diagnostics
    # Map MAPE into a 0..1 reliability — capped so high-error fits don't
    # produce negative confidence.
    reliability = max(0.0, 1.0 - min(diag.mape, 1.0))
    confidence_block: dict[str, Any] = {
        "band_level": params.confidence,
        "reliability": round(reliability, 4),
        "mape": round(diag.mape, 4),
        "smape": round(diag.smape, 4),
        "r2": round(diag.r2, 4),
        "n_observations": diag.n_observations,
        "data_observed_ratio": coverage.get("observed_ratio", 0.0),
    }

    payload = {
        "history_window": {
            "start_date": history["start_date"],
            "end_date": history["end_date"],
            "days": history["days"],
            "avg_price": history["avg_price"],
        },
        "forecast": result.to_dict(),
        "explanation": explanation,
        "coverage": coverage,
        "confidence": confidence_block,
        "kg_features": kg_features,
        "evidence_ids": _merge_evidence_ids(record_ids, kg_evidence_ids),
        "kg_linked": bool(kg_features),
    }

    run = PredictionRun(
        id=uuid4().hex,
        project_id=params.project_id,
        kind="forecast",
        status="completed",
        created_at=datetime.utcnow().isoformat(timespec="seconds"),
        metric=params.metric,
        config={
            "metric": params.metric,
            "horizon_days": params.horizon_days,
            "seasonality_period": params.seasonality_period,
            "confidence": params.confidence,
            "kg_linked": bool(kg_features),
        },
        result=payload,
        evidence_ids=payload["evidence_ids"],
        coverage=coverage,
        confidence=confidence_block,
        kg_features=kg_features,
    )
    _registry.add(run)
    _cache.put(cache_key, run.__dict__.copy())
    return run


def run_causal(params: CausalParams) -> PredictionRun:
    """Difference-in-differences ATE estimate before / after an intervention."""
    if params.metric not in ALL_METRICS:
        raise ValueError(
            f"unknown metric {params.metric!r}; expected one of {ALL_METRICS}"
        )
    if not params.intervention_start:
        raise ValueError("intervention_start (ISO date) is required for causal runs")

    cache_key = f"causal:{params.hash_key()}"
    cached = _cache.get(cache_key)
    if cached is not None:
        run = PredictionRun(**cached)
        _registry.add(run)
        return run

    history, record_ids = _load_history(params.project_id)
    estimate = causal_mod.estimate_ate(
        history=history,
        metric=params.metric,
        intervention_start=params.intervention_start,
        intervention_end=params.intervention_end,
    )

    kg_features, kg_evidence_ids = _load_kg_context(params.project_id)
    coverage = dict(history["coverage"])
    coverage["history_days"] = history["days"]
    coverage["pre_days"] = estimate.get("pre_days", 0)
    coverage["post_days"] = estimate.get("post_days", 0)

    seed = estimate.get("narrative_seed") or {}
    p_value = float(estimate.get("p_value", 1.0) or 1.0)
    confidence_block: dict[str, Any] = {
        "p_value": round(p_value, 4),
        "significant": bool(seed.get("significant", False)),
        "ci_low": estimate.get("ci_low"),
        "ci_high": estimate.get("ci_high"),
        "reliability": round(max(0.0, 1.0 - p_value), 4),
        "status": estimate.get("status", "ok"),
    }

    evidence_ids = _merge_evidence_ids(record_ids, kg_evidence_ids)
    payload = {
        **estimate,
        "coverage": coverage,
        "confidence": confidence_block,
        "kg_features": kg_features,
        "evidence_ids": evidence_ids,
        "kg_linked": bool(kg_features),
    }

    run = PredictionRun(
        id=uuid4().hex,
        project_id=params.project_id,
        kind="causal",
        status="completed",
        created_at=datetime.utcnow().isoformat(timespec="seconds"),
        metric=params.metric,
        config={
            "metric": params.metric,
            "intervention_start": params.intervention_start,
            "intervention_end": params.intervention_end,
            "kg_linked": bool(kg_features),
        },
        result=payload,
        evidence_ids=evidence_ids,
        coverage=coverage,
        confidence=confidence_block,
        kg_features=kg_features,
    )
    _registry.add(run)
    _cache.put(cache_key, run.__dict__.copy())
    return run


def get_run(run_id: str) -> PredictionRun | None:
    return _registry.get(run_id)


def list_runs(project_id: str | None = None) -> list[PredictionRun]:
    return _registry.list_for_project(project_id)


# ---------- test hook ---------------------------------------------------------


def reset_for_tests() -> None:
    _registry.clear()
    _cache.clear()


__all__ = [
    "CausalParams",
    "ForecastParams",
    "PredictionRun",
    "get_run",
    "list_runs",
    "reset_for_tests",
    "run_causal",
    "run_forecast",
]
