"""Multi-round simulator runner — pure-Python, deterministic, in-process.

Drives one simulation: builds the network, walks the population through N rounds,
applies the decision policy per agent per round, and emits per-round metrics.

The runner is **synchronous** by design — M2.1's goal is to nail the model first.
M2.2 will wrap this in APScheduler + an SSE event stream for the frontend.

KG integration
--------------
Callers may pass an optional ``kg_subgraph`` (the dict shape returned by
:func:`app.kg.search.get_subgraph`). When supplied, the runner enriches
``SimulationResult.network`` with a ``kg_features`` block (KOL / Topic /
Product / Brand counts) and surfaces the union of evidence ids attached
to those entities as ``SimulationResult.evidence_ids``. Downstream decision
and report layers consume ``evidence_ids`` to render evidence-grounded
recommendations. When ``kg_subgraph`` is omitted the runner behaves
exactly as before — preserving determinism and backwards compatibility.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.simulator.action import Action, ActionKind
from app.simulator.decision import DecisionContext, decide_action_sync
from app.simulator.network import build_network, degree_summary
from app.simulator.population import build_population, population_summary


@dataclass
class RoundMetrics:
    """Aggregate stats for one round."""

    round: int
    avg_sentiment: float
    sentiment_std: float
    action_counts: dict[str, int]
    awareness: float          # share of agents whose |sentiment| > 0.1
    purchase_rate: float      # share that took a 'buy' action this round
    boycott_rate: float


@dataclass
class SimulationResult:
    """Final result of a single simulation."""

    project_id: str
    started_at: str
    finished_at: str
    config: dict[str, Any]
    population: dict[str, Any]
    network: dict[str, Any]
    rounds: list[RoundMetrics] = field(default_factory=list)
    final_sentiment: list[float] = field(default_factory=list)
    final_action_totals: dict[str, int] = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "config": self.config,
            "population": self.population,
            "network": self.network,
            "rounds": [m.__dict__ for m in self.rounds],
            "final_sentiment": self.final_sentiment,
            "final_action_totals": self.final_action_totals,
            "evidence_ids": self.evidence_ids,
        }


def _stimulus_for_round(
    round_idx: int, campaign_schedule: Sequence[dict[str, Any]] | None
) -> tuple[float, float]:
    """Resolve (stimulus, price_pressure) for ``round_idx`` from a schedule.

    Schedule entry shape: ``{"round": int, "stimulus": float, "price_pressure": float}``.
    The most recent entry whose ``round`` ≤ ``round_idx`` wins.
    """
    if not campaign_schedule:
        return 0.0, 0.5
    active = [e for e in campaign_schedule if e.get("round", 0) <= round_idx]
    if not active:
        return 0.0, 0.5
    e = max(active, key=lambda e: e.get("round", 0))
    return float(e.get("stimulus", 0.0)), float(e.get("price_pressure", 0.5))


def _round_metrics(
    round_idx: int,
    sentiments: Sequence[float],
    actions: Sequence[Action],
) -> RoundMetrics:
    n = len(sentiments)
    avg = sum(sentiments) / n if n else 0.0
    var = (sum((s - avg) ** 2 for s in sentiments) / n) if n else 0.0
    std = var**0.5
    counts: dict[str, int] = {}
    for a in actions:
        counts[a.kind] = counts.get(a.kind, 0) + 1
    awareness = (sum(1 for s in sentiments if abs(s) > 0.1) / n) if n else 0.0
    purchase = (counts.get("buy", 0) / n) if n else 0.0
    boycott = (counts.get("boycott", 0) / n) if n else 0.0
    return RoundMetrics(
        round=round_idx,
        avg_sentiment=round(avg, 4),
        sentiment_std=round(std, 4),
        action_counts=counts,
        awareness=round(awareness, 4),
        purchase_rate=round(purchase, 4),
        boycott_rate=round(boycott, 4),
    )


def summarize_kg(
    kg_subgraph: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    """Reduce a KG subgraph dict to a compact features block + evidence ids.

    Returns ``({}, [])`` when ``kg_subgraph`` is empty / falsy so the caller
    can preserve pre-KG behavior. The features block carries entity counts
    and the top KOL / Topic names (handy for report blurbs); the second
    element is the deduplicated, sorted union of evidence ids surfaced by
    those entities so downstream decision/report layers can trace back to
    the raw crawl records.
    """
    if not kg_subgraph:
        return {}, []
    nodes = kg_subgraph.get("nodes") or []
    if not nodes:
        return {}, []

    type_counts: dict[str, int] = {}
    kol_names: list[str] = []
    topic_names: list[str] = []
    evidence: set[str] = set()
    for node in nodes:
        node_type = str(node.get("type", "Entity"))
        type_counts[node_type] = type_counts.get(node_type, 0) + 1
        name = str(node.get("name", "")).strip()
        if name and node_type == "KOL":
            kol_names.append(name)
        elif name and node_type == "Topic":
            topic_names.append(name)
        for ev in node.get("evidence_ids") or []:
            if ev:
                evidence.add(str(ev))

    features: dict[str, Any] = {
        "node_count": len(nodes),
        "edge_count": len(kg_subgraph.get("edges") or []),
        "type_counts": type_counts,
        "top_kols": sorted(kol_names)[:5],
        "top_topics": sorted(topic_names)[:5],
    }
    return features, sorted(evidence)


def run_simulation_sync(
    seed_report: dict[str, Any],
    *,
    num_agents: int = 200,
    num_rounds: int = 20,
    mean_degree: int = 8,
    target_product_id: str | None = None,
    campaign_schedule: Sequence[dict[str, Any]] | None = None,
    rng_seed: int | None = None,
    kg_subgraph: dict[str, Any] | None = None,
) -> SimulationResult:
    """Run an end-to-end simulation in process and return aggregated metrics.

    Parameters
    ----------
    seed_report:
        The output of ``build_seed_report`` for the target project. Used both
        to seed the population and as the deterministic seed source.
    num_agents:
        Population size.
    num_rounds:
        Number of decision rounds.
    mean_degree:
        Expected node degree in the social graph.
    target_product_id:
        Optional product the simulator focuses on (passed through to actions).
    campaign_schedule:
        Optional list of marketing events: each entry can specify a starting
        ``round``, a ``stimulus`` ∈ [-1, 1] (positive = promo / hype, negative =
        scandal), and a ``price_pressure`` ∈ [0, 1] (0 = bargain, 1 = expensive).
    rng_seed:
        Override the RNG seed. Default is derived from ``seed_report.project_id``.
    """
    project_id = str(seed_report.get("project_id", ""))
    if num_agents < 1:
        raise ValueError("num_agents must be >= 1")
    if num_rounds < 1:
        raise ValueError("num_rounds must be >= 1")
    started = datetime.utcnow().isoformat(timespec="seconds")

    agents = build_population(seed_report, size=num_agents)
    seed = rng_seed if rng_seed is not None else hash(project_id) & 0xFFFF_FFFF
    graph = build_network(len(agents), mean_degree=mean_degree, seed=seed)

    sentiments = [a.initial_sentiment for a in agents]
    rng = random.Random(seed)
    last_round_actions: list[Action | None] = [None] * len(agents)

    # Index KOLs and (optionally) follower edges via graph adjacency.
    kol_indices = [i for i, a in enumerate(agents) if a.persona == "kol"]
    rounds: list[RoundMetrics] = []
    action_totals: dict[str, int] = {k: 0 for k in (
        "buy", "comment", "share", "boycott", "ignore", "search",
    )}

    for r in range(num_rounds):
        stimulus, price_pressure = _stimulus_for_round(r, campaign_schedule)
        next_sentiments = list(sentiments)
        round_actions: list[Action] = []

        # Pre-compute neighbor pressure = mean sentiment of neighbors that
        # *acted* last round (anything but ignore). Falls back to 0 when no
        # neighbor acted, which keeps round 0 quiet (cold start).
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
        rounds.append(_round_metrics(r, sentiments, round_actions))

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


# Type alias re-exports — useful for tests asserting on action kinds.
AllActionKinds: tuple[ActionKind, ...] = (
    "buy", "comment", "share", "boycott", "ignore", "search",
)


__all__ = [
    "AllActionKinds",
    "RoundMetrics",
    "SimulationResult",
    "run_simulation_sync",
    "summarize_kg",
]
