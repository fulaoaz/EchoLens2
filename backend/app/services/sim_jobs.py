"""In-process simulation job runner — APScheduler-backed background execution.

The runner itself (``app.simulator.runner.run_simulation_sync``) is a single
synchronous function. M2.2 wraps it in a background scheduler so the API can
return a ``job_id`` immediately and the frontend can subscribe to per-round
progress via SSE.

Design notes
------------

- Single process, single ``BackgroundScheduler`` instance. Jobs are CPU-bound
  pure-Python — APScheduler's default ThreadPoolExecutor is fine.
- Each job carries its own thread-safe ``Queue`` of ``SimEvent`` records. The
  simulation runner is patched to push events via a callback hook so we don't
  need to fork ``run_simulation_sync``.
- Jobs persist in memory only — process restart wipes them. M2.x will swap the
  registry for DuckDB if persistence becomes a requirement.
- The lifecycle is intentionally tiny: ``submit -> running -> (completed |
  failed | cancelled)``. SSE consumers receive a terminal ``done`` / ``failed``
  event then the queue closes.
"""

from __future__ import annotations

import logging
import queue
import random
import threading
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from apscheduler.schedulers.background import BackgroundScheduler

from app.simulator.action import Action
from app.simulator.decision import DecisionContext, decide_action_sync
from app.simulator.network import build_network, degree_summary
from app.simulator.population import build_population, population_summary
from app.simulator.runner import (
    AllActionKinds,
    RoundMetrics,
    SimulationResult,
    _round_metrics,
    _stimulus_for_round,
    summarize_kg,
)

log = logging.getLogger(__name__)

JobStatus = Literal["pending", "running", "completed", "failed", "cancelled"]


# ---------- event records ------------------------------------------------------


@dataclass
class SimEvent:
    """One server-sent event published to subscribers of a job."""

    type: Literal["queued", "started", "round", "done", "failed", "cancelled"]
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds"))


# ---------- job record ---------------------------------------------------------


@dataclass
class SimJob:
    """In-memory record for one queued / running / finished simulation."""

    id: str
    project_id: str
    status: JobStatus = "pending"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds"))
    started_at: str | None = None
    finished_at: str | None = None
    config: dict[str, Any] = field(default_factory=dict)
    rounds_done: int = 0
    total_rounds: int = 0
    last_round_metrics: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    event_queue: queue.Queue[SimEvent | None] = field(default_factory=queue.Queue)

    def snapshot(self) -> dict[str, Any]:
        """Return the JSON-serialisable subset for /jobs/<id> responses."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "config": self.config,
            "rounds_done": self.rounds_done,
            "total_rounds": self.total_rounds,
            "last_round_metrics": self.last_round_metrics,
            "error": self.error,
        }


# ---------- runner with per-round callback -------------------------------------


def _run_with_callback(
    seed_report: dict[str, Any],
    *,
    num_agents: int,
    num_rounds: int,
    mean_degree: int,
    target_product_id: str | None,
    campaign_schedule: Sequence[dict[str, Any]] | None,
    rng_seed: int | None,
    on_round: Callable[[RoundMetrics], None],
    is_cancelled: Callable[[], bool],
    kg_subgraph: dict[str, Any] | None = None,
) -> SimulationResult:
    """Multi-round simulation that yields metrics to ``on_round`` after each round.

    A near-mirror of ``run_simulation_sync`` — duplicated rather than refactored
    because we don't want to leak callback machinery into the synchronous path
    that tests rely on. Both share the ``_round_metrics`` and
    ``_stimulus_for_round`` helpers so the math stays in one place.
    """
    if num_agents < 1:
        raise ValueError("num_agents must be >= 1")
    if num_rounds < 1:
        raise ValueError("num_rounds must be >= 1")

    project_id = str(seed_report.get("project_id", ""))
    started = datetime.utcnow().isoformat(timespec="seconds")

    agents = build_population(seed_report, size=num_agents)
    seed = rng_seed if rng_seed is not None else hash(project_id) & 0xFFFF_FFFF
    graph = build_network(len(agents), mean_degree=mean_degree, seed=seed)

    sentiments = [a.initial_sentiment for a in agents]
    rng = random.Random(seed)
    last_round_actions: list[Action | None] = [None] * len(agents)

    kol_indices = [i for i, a in enumerate(agents) if a.persona == "kol"]
    rounds: list[RoundMetrics] = []
    action_totals: dict[str, int] = {k: 0 for k in AllActionKinds}

    for r in range(num_rounds):
        if is_cancelled():
            break
        stimulus, price_pressure = _stimulus_for_round(r, campaign_schedule)
        next_sentiments = list(sentiments)
        round_actions: list[Action] = []

        for idx, agent in enumerate(agents):
            neighbors = list(graph.neighbors(idx)) if graph.has_node(idx) else []
            pressed: list[float] = []
            for nb in neighbors:
                act = last_round_actions[nb]
                if act is not None and act.kind != "ignore":
                    pressed.append(act.sentiment_delta)
            social = sum(pressed) / len(pressed) if pressed else 0.0
            kol_signal = (
                sum(sentiments[k] for k in kol_indices) / len(kol_indices)
                if kol_indices
                else 0.0
            )
            ctx = DecisionContext(
                round=r,
                social_pressure=social,
                kol_signal=kol_signal,
                stimulus=stimulus,
                price_pressure=price_pressure,
                target_product_id=target_product_id,
            )
            action, new_s = decide_action_sync(agent, sentiments[idx], ctx, rng)
            next_sentiments[idx] = new_s
            round_actions.append(action)
            action_totals[action.kind] = action_totals.get(action.kind, 0) + 1

        sentiments = next_sentiments
        last_round_actions = list(round_actions)
        metrics = _round_metrics(r, sentiments, round_actions)
        rounds.append(metrics)
        try:
            on_round(metrics)
        except Exception:  # noqa: BLE001 — callback errors must not crash the sim
            log.exception("on_round callback failed for round %d", r)

    finished = datetime.utcnow().isoformat(timespec="seconds")
    kg_features, evidence_ids = summarize_kg(kg_subgraph)
    network_summary: dict[str, Any] = dict(degree_summary(graph))
    if kg_features:
        network_summary["kg_features"] = kg_features
    return SimulationResult(
        project_id=project_id,
        started_at=started,
        finished_at=finished,
        config={
            "num_agents": num_agents,
            "num_rounds": num_rounds,
            "mean_degree": mean_degree,
            "target_product_id": target_product_id,
            "campaign_schedule": list(campaign_schedule or []),
            "rng_seed": seed,
            "kg_linked": bool(kg_features),
        },
        population=population_summary(agents),
        network=network_summary,
        rounds=rounds,
        final_sentiment=[round(s, 4) for s in sentiments],
        final_action_totals=action_totals,
        evidence_ids=evidence_ids,
    )


# ---------- registry + scheduler -----------------------------------------------


class _JobRegistry:
    """Thread-safe in-memory registry keyed by job_id."""

    def __init__(self) -> None:
        self._jobs: dict[str, SimJob] = {}
        self._lock = threading.Lock()

    def add(self, job: SimJob) -> None:
        with self._lock:
            self._jobs[job.id] = job

    def get(self, job_id: str) -> SimJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list_for_project(self, project_id: str | None = None) -> list[SimJob]:
        with self._lock:
            jobs = list(self._jobs.values())
        if project_id is None:
            return jobs
        return [j for j in jobs if j.project_id == project_id]

    def clear(self) -> None:  # test hook
        with self._lock:
            for j in self._jobs.values():
                j.cancel_event.set()
                j.event_queue.put(None)
            self._jobs.clear()


_registry = _JobRegistry()
_scheduler: BackgroundScheduler | None = None
_scheduler_lock = threading.Lock()


def _get_scheduler() -> BackgroundScheduler:
    global _scheduler
    with _scheduler_lock:
        if _scheduler is None or not _scheduler.running:
            _scheduler = BackgroundScheduler(daemon=True)
            _scheduler.start()
    return _scheduler


def _execute(job_id: str, seed_report: dict[str, Any], params: dict[str, Any]) -> None:
    """APScheduler entrypoint — runs in a worker thread."""
    job = _registry.get(job_id)
    if job is None:
        log.warning("simulation job %s vanished before execution", job_id)
        return

    job.status = "running"
    job.started_at = datetime.utcnow().isoformat(timespec="seconds")
    job.event_queue.put(SimEvent("started", {"job_id": job_id}))

    def _on_round(m: RoundMetrics) -> None:
        job.rounds_done = m.round + 1
        job.last_round_metrics = m.__dict__
        job.event_queue.put(
            SimEvent(
                "round",
                {
                    "job_id": job_id,
                    "round": m.round,
                    "metrics": m.__dict__,
                    "rounds_done": job.rounds_done,
                    "total_rounds": job.total_rounds,
                },
            )
        )

    try:
        result = _run_with_callback(
            seed_report,
            num_agents=params["num_agents"],
            num_rounds=params["num_rounds"],
            mean_degree=params["mean_degree"],
            target_product_id=params.get("target_product_id"),
            campaign_schedule=params.get("campaign_schedule"),
            rng_seed=params.get("rng_seed"),
            kg_subgraph=params.get("kg_subgraph"),
            on_round=_on_round,
            is_cancelled=job.cancel_event.is_set,
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("simulation job %s failed", job_id)
        job.status = "failed"
        job.error = f"{type(exc).__name__}: {exc}"
        job.finished_at = datetime.utcnow().isoformat(timespec="seconds")
        job.event_queue.put(SimEvent("failed", {"job_id": job_id, "error": job.error}))
        job.event_queue.put(None)  # close stream
        return

    job.finished_at = datetime.utcnow().isoformat(timespec="seconds")
    job.result = result.to_dict()
    if job.cancel_event.is_set():
        job.status = "cancelled"
        job.event_queue.put(SimEvent("cancelled", {"job_id": job_id}))
    else:
        job.status = "completed"
        job.event_queue.put(
            SimEvent(
                "done",
                {
                    "job_id": job_id,
                    "final_action_totals": result.final_action_totals,
                    "rounds": len(result.rounds),
                    "kg_linked": bool(result.config.get("kg_linked")),
                    "evidence_ids": result.evidence_ids,
                },
            )
        )
    job.event_queue.put(None)


# ---------- public API ---------------------------------------------------------


def submit_simulation(
    project_id: str,
    seed_report: dict[str, Any],
    *,
    num_agents: int = 200,
    num_rounds: int = 20,
    mean_degree: int = 8,
    target_product_id: str | None = None,
    campaign_schedule: Sequence[dict[str, Any]] | None = None,
    rng_seed: int | None = None,
    kg_subgraph: dict[str, Any] | None = None,
    sync: bool = False,
) -> SimJob:
    """Queue a simulation job and return its handle.

    ``sync=True`` runs the job inline (used by tests to avoid race conditions).
    """
    job = SimJob(
        id=uuid4().hex,
        project_id=project_id,
        total_rounds=num_rounds,
        config={
            "num_agents": num_agents,
            "num_rounds": num_rounds,
            "mean_degree": mean_degree,
            "target_product_id": target_product_id,
            "campaign_schedule": list(campaign_schedule or []),
            "rng_seed": rng_seed,
            "kg_linked": bool(kg_subgraph),
        },
    )
    _registry.add(job)
    job.event_queue.put(SimEvent("queued", {"job_id": job.id, "project_id": project_id}))

    params = dict(job.config)
    # The KG subgraph is only needed at execution time; keep it out of the
    # public ``config`` snapshot (which is JSON-serialised for /jobs/<id>).
    params["kg_subgraph"] = kg_subgraph

    if sync:
        _execute(job.id, seed_report, params)
        return job

    scheduler = _get_scheduler()
    scheduler.add_job(_execute, args=[job.id, seed_report, params], id=job.id)
    return job


def get_job(job_id: str) -> SimJob | None:
    return _registry.get(job_id)


def list_jobs(project_id: str | None = None) -> list[SimJob]:
    return _registry.list_for_project(project_id)


def cancel_job(job_id: str) -> bool:
    job = _registry.get(job_id)
    if job is None or job.status in {"completed", "failed", "cancelled"}:
        return False
    job.cancel_event.set()
    return True


def stream_events(job_id: str, *, timeout: float = 30.0) -> Iterator[SimEvent]:
    """Yield events from the job's queue until the terminal ``None`` sentinel."""
    job = _registry.get(job_id)
    if job is None:
        return
    while True:
        try:
            ev = job.event_queue.get(timeout=timeout)
        except queue.Empty:
            # heartbeat — let SSE keep-alive itself
            yield SimEvent("round", {"heartbeat": True, "job_id": job_id})
            continue
        if ev is None:
            return
        yield ev


# ---------- test hooks ---------------------------------------------------------


def reset_for_tests() -> None:
    """Tear down scheduler + registry — used by test fixtures."""
    global _scheduler
    with _scheduler_lock:
        if _scheduler is not None and _scheduler.running:
            try:
                _scheduler.shutdown(wait=False)
            except Exception:  # noqa: BLE001
                pass
        _scheduler = None
    _registry.clear()


__all__ = [
    "JobStatus",
    "SimEvent",
    "SimJob",
    "cancel_job",
    "get_job",
    "list_jobs",
    "reset_for_tests",
    "stream_events",
    "submit_simulation",
]
