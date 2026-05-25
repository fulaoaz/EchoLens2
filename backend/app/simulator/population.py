"""Population builder — turn a SeedReport into a deterministic Agent population.

The population is generated from the seed report's empirical signals:

- ``review_sentiment_distribution``  → initial sentiment of each agent
- ``top_kols``                        → KOL persona seeds (high susceptibility, fan-out hubs)
- ``products[*].price_current``       → market price band → tunes purchasing_power
- A deterministic mix of personas fills the remaining headcount.

We seed the RNG from ``project_id`` so the same seed report always produces the
same population — the simulator is reproducible by construction.

This module is pure-Python and has no I/O.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Sequence
from typing import Any

from app.simulator.agent import Agent, Persona

# Default persona mix when no explicit override is given. Numbers sum to 1.0 — they
# represent the long-tail of an e-commerce buyer base.
_DEFAULT_PERSONA_MIX: dict[Persona, float] = {
    "price_sensitive": 0.40,
    "brand_loyal": 0.20,
    "early_adopter": 0.15,
    "cautious": 0.20,
    "kol": 0.05,
}

_PERSONA_SUSCEPTIBILITY: dict[Persona, float] = {
    "price_sensitive": 0.55,
    "brand_loyal": 0.25,
    "early_adopter": 0.70,
    "cautious": 0.30,
    "kol": 0.85,
}

_PERSONA_PURCHASING_POWER: dict[Persona, float] = {
    "price_sensitive": 0.30,
    "brand_loyal": 0.65,
    "early_adopter": 0.75,
    "cautious": 0.50,
    "kol": 0.80,
}


def _seed_from(project_id: str, salt: str = "") -> int:
    """Stable 64-bit seed derived from project id (and optional salt)."""
    h = hashlib.sha256(f"{project_id}|{salt}".encode()).digest()
    return int.from_bytes(h[:8], "big", signed=False)


def _initial_sentiment_pool(
    sentiment_dist: dict[str, int], size: int, rng: random.Random
) -> list[float]:
    """Materialize an initial-sentiment array with the empirical sentiment ratio.

    Mapping: positive→+0.6±0.2, negative→-0.6±0.2, neutral/mixed/unknown→0.0±0.2.
    Falls back to all-zero if the seed report has no review signal.
    """
    total = sum(sentiment_dist.values())
    if total <= 0:
        return [rng.uniform(-0.1, 0.1) for _ in range(size)]

    out: list[float] = []
    remaining = size
    for label, count in sentiment_dist.items():
        share = round(size * count / total)
        if label == "positive":
            base, jitter = 0.6, 0.2
        elif label == "negative":
            base, jitter = -0.6, 0.2
        else:
            base, jitter = 0.0, 0.2
        for _ in range(min(share, remaining)):
            out.append(max(-1.0, min(1.0, base + rng.uniform(-jitter, jitter))))
        remaining -= min(share, remaining)
    # Fill any rounding gap with neutral noise.
    while remaining > 0:
        out.append(rng.uniform(-0.1, 0.1))
        remaining -= 1
    rng.shuffle(out)
    return out[:size]


def _persona_assignments(
    size: int, persona_mix: dict[Persona, float], rng: random.Random
) -> list[Persona]:
    """Assign personas to ``size`` slots according to ``persona_mix`` proportions."""
    assignments: list[Persona] = []
    remaining = size
    items = list(persona_mix.items())
    for i, (persona, share) in enumerate(items):
        n = round(size * share)
        if i == len(items) - 1:
            n = remaining  # last bucket eats the rounding gap
        n = min(n, remaining)
        assignments.extend([persona] * n)
        remaining -= n
    rng.shuffle(assignments)
    return assignments


def _interest_topics(seed_report: dict[str, Any]) -> list[str]:
    """Extract a small interest vocabulary from the seed report.

    Currently uses brand + platform tokens; the simulator only treats interests
    as opaque string tags, so any seed-derived vocabulary works.
    """
    topics: set[str] = set()
    for p in seed_report.get("products") or []:
        if p.get("brand"):
            topics.add(str(p["brand"]))
        if p.get("platform"):
            topics.add(f"@{p['platform']}")
    return sorted(topics) or ["generic"]


def build_population(
    seed_report: dict[str, Any],
    *,
    size: int = 200,
    persona_mix: dict[Persona, float] | None = None,
) -> list[Agent]:
    """Construct ``size`` Agents from a SeedReport. Deterministic per project."""
    if size <= 0:
        return []

    project_id = str(seed_report.get("project_id", ""))
    rng = random.Random(_seed_from(project_id, "population"))
    mix = persona_mix or _DEFAULT_PERSONA_MIX

    personas = _persona_assignments(size, mix, rng)
    sentiments = _initial_sentiment_pool(
        seed_report.get("review_sentiment_distribution") or {}, size, rng
    )
    interest_pool = _interest_topics(seed_report)

    # Map known KOLs onto the kol-persona slots (up to whichever is smaller).
    kol_hashes: list[str] = [
        k.get("author_hash", "") for k in (seed_report.get("top_kols") or [])
    ]

    agents: list[Agent] = []
    kol_cursor = 0
    for i, persona in enumerate(personas):
        # Pick 1–2 interests deterministically.
        topics = rng.sample(interest_pool, k=min(2, len(interest_pool)))
        suscept = max(
            0.0,
            min(1.0, _PERSONA_SUSCEPTIBILITY[persona] + rng.uniform(-0.1, 0.1)),
        )
        power = max(
            0.0,
            min(1.0, _PERSONA_PURCHASING_POWER[persona] + rng.uniform(-0.1, 0.1)),
        )
        # KOLs reuse real author_hashes when available so reports can cross-reference.
        if persona == "kol" and kol_cursor < len(kol_hashes) and kol_hashes[kol_cursor]:
            agent_id = kol_hashes[kol_cursor]
            kol_cursor += 1
        else:
            agent_id = f"agent_{i:05d}"
        agents.append(
            Agent(
                id=agent_id,
                persona=persona,
                interests=topics,
                susceptibility=suscept,
                purchasing_power=power,
                initial_sentiment=sentiments[i],
            )
        )
    return agents


def population_summary(agents: Sequence[Agent]) -> dict[str, Any]:
    """A compact summary of the population (for /api responses + tests)."""
    persona_counts: dict[str, int] = {}
    for a in agents:
        persona_counts[a.persona] = persona_counts.get(a.persona, 0) + 1
    avg_sentiment = (
        sum(a.initial_sentiment for a in agents) / len(agents) if agents else 0.0
    )
    return {
        "size": len(agents),
        "persona_counts": persona_counts,
        "avg_initial_sentiment": round(avg_sentiment, 4),
    }


__all__ = ["build_population", "population_summary"]
