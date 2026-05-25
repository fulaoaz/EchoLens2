"""Synthesizer — combine simulation matrix + prediction matrix → action recommendations.

Stub — M4 will implement.
"""

from __future__ import annotations

from typing import Any


async def synthesize(
    simulation_result: dict[str, Any] | None,
    prediction_result: dict[str, Any] | None,
) -> dict[str, Any]:  # pragma: no cover
    raise NotImplementedError("M4: ReACT report-agent + Top-K action ranking")
