"""LightRAG adapter — graph-augmented retrieval (dual-level: local + global).

Per the M0.C spike report (docs/kg-spike-report.md): use LightRAG's NetworkX
backend, then one-way sync to Kuzu for structured queries.

Stub — M1 will implement.
"""

from __future__ import annotations

from typing import Any


async def ingest(text: str, project_id: str) -> None:  # pragma: no cover
    raise NotImplementedError("M1: LightRAG.ainsert")


async def query(question: str, mode: str = "hybrid") -> dict[str, Any]:  # pragma: no cover
    raise NotImplementedError("M1: LightRAG.aquery (mode in {local,global,hybrid})")
