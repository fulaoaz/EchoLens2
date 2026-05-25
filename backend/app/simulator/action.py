"""Action set — buy / comment / share / boycott / ignore."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

ActionKind = Literal["buy", "comment", "share", "boycott", "ignore", "search"]


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_id: str
    kind: ActionKind
    target_product_id: str | None = None
    sentiment_delta: float = 0.0
    payload: dict[str, str] = {}
    round: int
