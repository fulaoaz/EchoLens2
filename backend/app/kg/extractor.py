"""LLM-driven entity & relation extraction from crawled text. Stub."""

from __future__ import annotations

from app.kg.ontology import EntityNode, RelationEdge


async def extract(text: str) -> tuple[list[EntityNode], list[RelationEdge]]:  # pragma: no cover
    raise NotImplementedError("M1: prompt + JSON-schema extraction with LLM")
