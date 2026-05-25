"""Real-time event channel between simulator and frontend (SSE)."""

from __future__ import annotations

from collections.abc import AsyncIterator


async def event_stream(simulation_id: str) -> AsyncIterator[bytes]:  # pragma: no cover
    raise NotImplementedError("M2: SSE event stream")
    yield b""  # type: ignore[unreachable]
