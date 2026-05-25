"""Project domain model."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

ProjectStatus = Literal[
    "created",
    "crawling",
    "seed_ready",
    "simulating",
    "predicting",
    "ready",
    "failed",
]


class Project(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    target_platforms: list[str] = Field(default_factory=list)
    status: ProjectStatus = "created"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
