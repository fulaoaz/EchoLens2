"""E-commerce ontology — 6 entity types + 8 relation types.

Designed to be small enough to fit Kuzu schema cleanly while covering the core
narrative: 商品/品牌/品类/KOL/事件/情感.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EntityType = Literal["Product", "Brand", "Category", "KOL", "Event", "SentimentTopic"]
RelationType = Literal[
    "BELONGS_TO",        # Product -> Category
    "MADE_BY",           # Product -> Brand
    "MENTIONED_BY",      # Product/Brand -> KOL
    "COMPETES_WITH",     # Brand -> Brand
    "TRIGGERED",         # Event -> SentimentTopic
    "RELATED_TO",        # SentimentTopic -> Product/Brand
    "PROMOTED_IN",       # Product -> Event
    "DERIVED_FROM",      # SentimentTopic -> Post (provenance)
]


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EntityNode(_Base):
    id: str
    type: EntityType
    name: str = Field(..., min_length=1)
    attributes: dict[str, str] = Field(default_factory=dict)


class RelationEdge(_Base):
    src_id: str
    dst_id: str
    type: RelationType
    weight: float = Field(default=1.0, ge=0)
    attributes: dict[str, str] = Field(default_factory=dict)


__all__ = ["EntityNode", "EntityType", "RelationEdge", "RelationType"]
