"""Pydantic 2 data contracts for crawled and uploaded data.

All schemas use ``ConfigDict(extra="forbid", str_strip_whitespace=True)``.
PII fields (user_hash, author_hash) MUST be pre-hashed before construction.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Sentiment = Literal["positive", "neutral", "negative", "mixed", "unknown"]
Platform = Literal[
    "taobao", "jd", "pdd", "douyin", "weibo", "xhs", "zhihu", "news", "unknown"
]


class _StrictBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class Product(_StrictBase):
    """E-commerce product snapshot."""

    id: str = Field(
        ...,
        description="Stable product id (platform-prefixed).",
        examples=["jd:100012043978"],
    )
    platform: Platform
    title: str = Field(..., min_length=1, max_length=500)
    category: str | None = None
    brand: str | None = None
    price_current: float | None = Field(default=None, ge=0)
    price_original: float | None = Field(default=None, ge=0)
    sales_count: int | None = Field(default=None, ge=0)
    rating: float | None = Field(default=None, ge=0, le=5)
    image_urls: list[str] = Field(default_factory=list)
    url: str | None = None
    crawled_at: datetime = Field(default_factory=datetime.utcnow)


class Review(_StrictBase):
    """Single product review."""

    id: str
    product_id: str
    platform: Platform
    author_hash: str = Field(..., description="Hashed user id; never store raw user id.")
    content: str = Field(..., min_length=1, max_length=10_000)
    rating: int | None = Field(default=None, ge=1, le=5)
    sentiment: Sentiment = "unknown"
    aspects: list[str] = Field(default_factory=list)
    helpful_count: int | None = Field(default=None, ge=0)
    posted_at: datetime | None = None
    crawled_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("author_hash")
    @classmethod
    def _author_hash_format(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("author_hash must look hashed (>=6 chars)")
        return v


class Post(_StrictBase):
    """Sentiment / social post."""

    id: str
    platform: Platform
    author_hash: str
    content: str = Field(..., min_length=1, max_length=20_000)
    likes: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    sentiment: Sentiment = "unknown"
    hashtags: list[str] = Field(default_factory=list)
    mentioned_brands: list[str] = Field(default_factory=list)
    posted_at: datetime | None = None
    crawled_at: datetime = Field(default_factory=datetime.utcnow)


class Order(_StrictBase):
    """Private-domain order (user-uploaded only)."""

    id: str
    user_hash: str
    sku: str
    amount: float = Field(..., ge=0)
    quantity: int = Field(default=1, ge=1)
    placed_at: datetime
    refunded: bool = False


class LiveSession(_StrictBase):
    """Public livestream session metadata."""

    id: str
    platform: Platform
    streamer_hash: str
    title: str = Field(..., min_length=1)
    duration_seconds: int = Field(..., ge=0)
    peak_viewers: int = Field(default=0, ge=0)
    average_viewers: int = Field(default=0, ge=0)
    products: list[str] = Field(default_factory=list, description="product.id list")
    started_at: datetime
    crawled_at: datetime = Field(default_factory=datetime.utcnow)


__all__ = [
    "LiveSession",
    "Order",
    "Platform",
    "Post",
    "Product",
    "Review",
    "Sentiment",
]
