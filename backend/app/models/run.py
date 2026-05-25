"""Run domain model — one execution of simulation or prediction within a project."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

RunKind = Literal["simulation", "prediction", "fused"]
RunStatus = Literal["pending", "running", "completed", "failed", "cancelled"]


class Run(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(default_factory=lambda: uuid4().hex)
    project_id: str
    kind: RunKind
    status: RunStatus = "pending"
    progress: float = Field(default=0.0, ge=0, le=1)
    config: dict = Field(default_factory=dict)
    metrics: dict = Field(default_factory=dict)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
