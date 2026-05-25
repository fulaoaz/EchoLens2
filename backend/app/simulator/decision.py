"""Decision policy — pure-Python action sampler for M2.1.

The M2.1 baseline is **rule-based + stochastic**, not LLM-driven. The interface
is shaped so an LLM-backed policy can drop in later: ``decide_action`` takes a
context dict and returns an Action.

Inputs (per round, per agent):
    - the agent itself (persona, susceptibility, current_sentiment, purchasing_power)
    - ``social_pressure``: avg sentiment of neighbors that took an action last round
    - ``kol_signal``:      avg sentiment of any KOL the agent follows
    - ``stimulus``:        external campaign event ({"type": "promo", "delta": +0.2})
    - ``rng``:             a per-round Random instance — ensures reproducibility

Output:
    - an ``Action`` (kind ∈ buy/comment/share/boycott/ignore/search) plus a
      ``sentiment_delta`` that the runner applies to the agent before next round.

The math is intentionally simple and inspectable:

    new_sentiment = clip(sentiment + α·social_pressure + β·kol_signal + γ·stimulus)
    purchase_score = σ(new_sentiment + 0.3·purchasing_power - 0.5·price_pressure)

Persona biases tweak (α, β, γ) and the action threshold curve.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any

from app.simulator.action import Action
from app.simulator.agent import Agent, Persona

# ----- Persona-specific weights (α=social, β=kol, γ=stimulus) ------------------

_PERSONA_WEIGHTS: dict[Persona, tuple[float, float, float]] = {
    "price_sensitive": (0.25, 0.20, 0.55),  # promos hit hardest
    "brand_loyal":     (0.10, 0.10, 0.20),  # noqa: E241 — sticky, ignore the world
    "early_adopter":   (0.30, 0.40, 0.40),  # noqa: E241
    "cautious":        (0.40, 0.20, 0.10),  # noqa: E241 — wait & see, peers matter
    "kol":             (0.10, 0.05, 0.30),  # noqa: E241 — drives others, less driven
}

# Per-persona bias added to the purchase score before sigmoid.
_PERSONA_PURCHASE_BIAS: dict[Persona, float] = {
    "price_sensitive": -0.10,
    "brand_loyal": +0.20,
    "early_adopter": +0.10,
    "cautious": -0.30,
    "kol": +0.05,
}


def _sigmoid(x: float) -> float:
    # Numerically stable sigmoid.
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _clip(value: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


@dataclass
class DecisionContext:
    """All non-agent inputs the policy needs for one decision."""

    round: int
    social_pressure: float = 0.0    # mean(neighbor sentiment delta) ∈ [-1, 1]
    kol_signal: float = 0.0         # mean(followed-KOL sentiment) ∈ [-1, 1]
    stimulus: float = 0.0           # campaign sentiment delta ∈ [-1, 1]
    price_pressure: float = 0.0     # 0 = bargain, 1 = overpriced
    target_product_id: str | None = None


def update_sentiment(
    current: float, agent: Agent, ctx: DecisionContext
) -> float:
    """Compute next-round sentiment for ``agent``.

    Susceptibility scales the *social* and *kol* terms — a price-sensitive but
    low-susceptibility person ignores their friends. Stimulus weight is fixed
    by persona (promo response is a personality trait, not a network trait).
    """
    alpha, beta, gamma = _PERSONA_WEIGHTS[agent.persona]
    s = agent.susceptibility
    delta = (
        alpha * s * ctx.social_pressure
        + beta * s * ctx.kol_signal
        + gamma * ctx.stimulus
    )
    return _clip(current + delta)


def _purchase_probability(
    agent: Agent, sentiment: float, ctx: DecisionContext
) -> float:
    score = (
        sentiment
        + 0.3 * agent.purchasing_power
        - 0.5 * ctx.price_pressure
        + _PERSONA_PURCHASE_BIAS[agent.persona]
    )
    return _sigmoid(score)


def decide_action_sync(
    agent: Agent,
    current_sentiment: float,
    ctx: DecisionContext,
    rng: random.Random,
) -> tuple[Action, float]:
    """Sample an action for ``agent`` given ``current_sentiment`` and ``ctx``.

    Returns (action, next_sentiment). The action's ``sentiment_delta`` field
    captures the *expressed* sentiment of the action (e.g. a "boycott" action
    has a strong negative delta) — distinct from the agent's internal sentiment
    update which is already baked into ``next_sentiment``.
    """
    next_sentiment = update_sentiment(current_sentiment, agent, ctx)
    p_buy = _purchase_probability(agent, next_sentiment, ctx)
    roll = rng.random()

    # KOLs are loud: they tend to comment / share rather than just buy/ignore.
    if agent.persona == "kol":
        if roll < 0.6:
            kind = "share" if next_sentiment >= 0 else "boycott"
            return (
                Action(
                    actor_id=agent.id,
                    kind=kind,
                    target_product_id=ctx.target_product_id,
                    sentiment_delta=next_sentiment,
                    round=ctx.round,
                ),
                next_sentiment,
            )

    # Strongly negative + moderately likely → boycott (~5–15%).
    if next_sentiment < -0.5 and roll < 0.25:
        return (
            Action(
                actor_id=agent.id,
                kind="boycott",
                target_product_id=ctx.target_product_id,
                sentiment_delta=next_sentiment,
                round=ctx.round,
            ),
            next_sentiment,
        )

    # Buy track — the headline metric.
    if roll < p_buy * 0.6:  # 0.6 dampener: not every "wants to buy" actually buys
        return (
            Action(
                actor_id=agent.id,
                kind="buy",
                target_product_id=ctx.target_product_id,
                sentiment_delta=next_sentiment,
                round=ctx.round,
            ),
            next_sentiment,
        )

    # Mid-positive sentiment → comment / share with smaller probability.
    if next_sentiment > 0.2 and roll < 0.4:
        return (
            Action(
                actor_id=agent.id,
                kind="share" if roll < 0.2 else "comment",
                target_product_id=ctx.target_product_id,
                sentiment_delta=next_sentiment,
                round=ctx.round,
            ),
            next_sentiment,
        )

    # Curious browsers — early adopters search even with neutral sentiment.
    if agent.persona == "early_adopter" and roll < 0.3:
        return (
            Action(
                actor_id=agent.id,
                kind="search",
                target_product_id=ctx.target_product_id,
                sentiment_delta=next_sentiment,
                round=ctx.round,
            ),
            next_sentiment,
        )

    return (
        Action(
            actor_id=agent.id,
            kind="ignore",
            target_product_id=ctx.target_product_id,
            sentiment_delta=next_sentiment,
            round=ctx.round,
        ),
        next_sentiment,
    )


def expose_for_tests() -> dict[str, Any]:
    """Expose internal weight tables for parameter-sensitivity tests."""
    return {
        "persona_weights": dict(_PERSONA_WEIGHTS),
        "persona_purchase_bias": dict(_PERSONA_PURCHASE_BIAS),
    }


__all__ = [
    "DecisionContext",
    "decide_action_sync",
    "expose_for_tests",
    "update_sentiment",
]
