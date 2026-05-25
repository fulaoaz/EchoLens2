"""Ensemble — combine timeseries + causal + simulation features into predictions."""

from __future__ import annotations

from typing import Any


def fuse(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    raise NotImplementedError("M3: weighted ensemble + confidence interval propagation")
