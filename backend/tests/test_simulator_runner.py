"""Simulator runner — population, network, decision, end-to-end."""

from __future__ import annotations

from typing import Any

import pytest

from app.crawler.seed_report import build_seed_report
from app.simulator.action import Action
from app.simulator.agent import Agent
from app.simulator.decision import (
    DecisionContext,
    decide_action_sync,
    update_sentiment,
)
from app.simulator.network import build_network, degree_summary
from app.simulator.population import build_population, population_summary
from app.simulator.runner import AllActionKinds, run_simulation_sync


def _seed_report(
    project_id: str = "p-test",
    *,
    n_pos: int = 6,
    n_neg: int = 2,
    n_kol: int = 2,
) -> dict[str, Any]:
    """Hand-rolled SeedReport — bypasses the DB so tests stay isolated."""
    reviews = (
        [{"platform": "jd", "id": f"r-pos-{i}", "sentiment": "positive"}
         for i in range(n_pos)]
        + [{"platform": "jd", "id": f"r-neg-{i}", "sentiment": "negative"}
           for i in range(n_neg)]
    )
    posts = [
        {
            "platform": "weibo",
            "id": f"w-{i}",
            "author_hash": f"kol_{i:02d}",
            "sentiment": "positive",
            "posted_at": "2026-02-01T10:00:00",
        }
        for i in range(n_kol)
    ]
    return build_seed_report(
        project_id,
        products=[{
            "platform": "jd",
            "id": "jd:demo-1",
            "title": "X",
            "brand": "BrandA",
            "price_current": 99,
        }],
        reviews=reviews,
        posts=posts,
    )


# ---------- population ---------------------------------------------------------


def test_population_is_deterministic_per_project() -> None:
    sr = _seed_report("p-1")
    a = build_population(sr, size=64)
    b = build_population(sr, size=64)
    assert [x.id for x in a] == [x.id for x in b]
    assert [x.persona for x in a] == [x.persona for x in b]
    # Different project → different population.
    c = build_population(_seed_report("p-2"), size=64)
    assert [x.id for x in a] != [x.id for x in c]


def test_population_persona_mix_respects_proportions() -> None:
    sr = _seed_report("p-mix")
    pop = build_population(sr, size=200)
    counts = population_summary(pop)["persona_counts"]
    # The default mix is 40/20/15/20/5 so ~80 / ~40 / ~30 / ~40 / ~10.
    assert counts.get("price_sensitive", 0) >= 60
    assert counts.get("kol", 0) >= 5
    assert counts.get("kol", 0) <= 20
    assert sum(counts.values()) == 200


def test_population_uses_kol_author_hashes() -> None:
    sr = _seed_report("p-kol", n_kol=4)
    pop = build_population(sr, size=200)
    kol_ids = [a.id for a in pop if a.persona == "kol"]
    # At least one of the seed-report KOL author_hashes shows up as a KOL agent id.
    assert any(aid.startswith("kol_") for aid in kol_ids)


def test_population_initial_sentiment_tracks_seed_distribution() -> None:
    sr = _seed_report("p-pos", n_pos=18, n_neg=2)
    pop = build_population(sr, size=200)
    avg = sum(a.initial_sentiment for a in pop) / len(pop)
    assert avg > 0.2  # heavily positive seed → positive avg


# ---------- network ------------------------------------------------------------


def test_network_is_connected_small_world() -> None:
    g = build_network(120, mean_degree=8, seed=42)
    summary = degree_summary(g)
    assert summary["nodes"] == 120
    assert 5.0 <= summary["mean_degree"] <= 10.0  # ~k for Watts-Strogatz


def test_network_handles_tiny_populations() -> None:
    assert build_network(0).number_of_nodes() == 0
    assert build_network(1).number_of_nodes() == 1
    g = build_network(3, mean_degree=8, seed=1)  # k clamped < n
    assert g.number_of_nodes() == 3


def test_network_seed_is_reproducible() -> None:
    a = build_network(80, mean_degree=6, seed=7)
    b = build_network(80, mean_degree=6, seed=7)
    assert sorted(a.edges()) == sorted(b.edges())


# ---------- decision -----------------------------------------------------------


def test_update_sentiment_clamps_within_bounds() -> None:
    agent = Agent(
        id="a", persona="kol", initial_sentiment=0.9, susceptibility=1.0,
    )
    ctx = DecisionContext(round=0, social_pressure=1.0, kol_signal=1.0, stimulus=1.0)
    s = update_sentiment(0.9, agent, ctx)
    assert -1.0 <= s <= 1.0


def test_decide_action_returns_known_kind() -> None:
    import random as _r
    rng = _r.Random(0)
    agent = Agent(id="a", persona="early_adopter")
    ctx = DecisionContext(round=0, stimulus=0.5)
    act, _ = decide_action_sync(agent, agent.initial_sentiment, ctx, rng)
    assert isinstance(act, Action)
    assert act.kind in AllActionKinds


def test_negative_stimulus_drops_purchase_rate() -> None:
    """Same population, opposite stimulus → far fewer 'buy' actions."""
    sr = _seed_report("p-stim")
    pos = run_simulation_sync(
        sr, num_agents=200, num_rounds=8, rng_seed=7,
        campaign_schedule=[{"round": 0, "stimulus": 0.6, "price_pressure": 0.3}],
    )
    neg = run_simulation_sync(
        sr, num_agents=200, num_rounds=8, rng_seed=7,
        campaign_schedule=[{"round": 0, "stimulus": -0.6, "price_pressure": 0.7}],
    )
    pos_buy = pos.final_action_totals.get("buy", 0)
    neg_buy = neg.final_action_totals.get("buy", 0)
    assert pos_buy > neg_buy


# ---------- runner end-to-end --------------------------------------------------


def test_run_simulation_basic_shape() -> None:
    sr = _seed_report("p-end")
    res = run_simulation_sync(sr, num_agents=80, num_rounds=6, rng_seed=42)
    assert res.project_id == "p-end"
    assert len(res.rounds) == 6
    assert len(res.final_sentiment) == 80
    assert all(-1.0 <= s <= 1.0 for s in res.final_sentiment)
    # Each round records all action kinds (some buckets may be 0 / missing).
    for m in res.rounds:
        total = sum(m.action_counts.values())
        assert total == 80


def test_run_simulation_is_deterministic_with_rng_seed() -> None:
    sr = _seed_report("p-det")
    a = run_simulation_sync(sr, num_agents=100, num_rounds=4, rng_seed=11)
    b = run_simulation_sync(sr, num_agents=100, num_rounds=4, rng_seed=11)
    assert a.final_sentiment == b.final_sentiment
    assert a.final_action_totals == b.final_action_totals


def test_run_simulation_metrics_progress_with_positive_stimulus() -> None:
    sr = _seed_report("p-prog")
    res = run_simulation_sync(
        sr, num_agents=200, num_rounds=10, rng_seed=3,
        campaign_schedule=[{"round": 0, "stimulus": 0.4, "price_pressure": 0.4}],
    )
    first, last = res.rounds[0], res.rounds[-1]
    # Awareness only goes up under positive stimulus.
    assert last.awareness >= first.awareness
    # Sentiment trends positive.
    assert last.avg_sentiment > first.avg_sentiment - 0.05


def test_run_simulation_zero_population_is_safe() -> None:
    sr = _seed_report("p-zero")
    with pytest.raises(Exception):
        # num_agents < 1 is rejected by the API layer; runner itself doesn't
        # have to handle it. Confirm the call path errors cleanly.
        run_simulation_sync(sr, num_agents=0, num_rounds=3)


def test_run_simulation_surfaces_kg_features_and_evidence_ids() -> None:
    """When ``kg_subgraph`` is supplied, the result carries KG features and ids.

    Wires :mod:`app.kg.search` to the runner: a project-scoped subgraph is
    summarized into ``network.kg_features`` and the union of evidence ids
    is exposed at the top level for decision/report layers to trace back
    to raw crawler records.
    """
    sr = _seed_report("p-kg")
    kg_subgraph = {
        "nodes": [
            {
                "id": "Brand:anker",
                "type": "Brand",
                "name": "Anker",
                "evidence_ids": ["jd:p1"],
            },
            {
                "id": "KOL:source_0001234",
                "type": "KOL",
                "name": "source_0001234",
                "evidence_ids": ["weibo:post1"],
            },
            {
                "id": "Topic:anker-737",
                "type": "Topic",
                "name": "Anker 737",
                "evidence_ids": ["weibo:post1", "jd:p1"],
            },
        ],
        "edges": [
            {"src": "Brand:anker", "dst": "Topic:anker-737", "type": "RELATED_TO", "weight": 0.5},
        ],
    }
    res = run_simulation_sync(
        sr, num_agents=40, num_rounds=4, rng_seed=99, kg_subgraph=kg_subgraph,
    )

    assert res.config["kg_linked"] is True
    features = res.network["kg_features"]
    assert features["node_count"] == 3
    assert features["edge_count"] == 1
    assert features["type_counts"] == {"Brand": 1, "KOL": 1, "Topic": 1}
    assert "Anker 737" in features["top_topics"]
    assert "source_0001234" in features["top_kols"]

    # Evidence ids are deduplicated and sorted across the whole subgraph.
    assert res.evidence_ids == ["jd:p1", "weibo:post1"]

    # Sanity: omitting kg_subgraph leaves the result KG-free (back-compat).
    plain = run_simulation_sync(sr, num_agents=40, num_rounds=4, rng_seed=99)
    assert plain.config["kg_linked"] is False
    assert "kg_features" not in plain.network
    assert plain.evidence_ids == []
