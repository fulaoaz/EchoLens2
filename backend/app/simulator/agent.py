"""Agent base class — consumer persona + LLM decision policy.

The decision policy (M2) will compose: persona × current network state × KG context
× event stimulus → action distribution.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Persona = Literal["price_sensitive", "brand_loyal", "early_adopter", "cautious", "kol"]


class Agent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    persona: Persona
    interests: list[str] = Field(default_factory=list)
    susceptibility: float = Field(default=0.5, ge=0, le=1, description="social influence")
    purchasing_power: float = Field(default=0.5, ge=0, le=1)
    initial_sentiment: float = Field(default=0.0, ge=-1, le=1)


async def decide_action(agent: Agent, context: dict) -> dict:  # pragma: no cover
    raise NotImplementedError("M2: LLM-backed decision policy")
