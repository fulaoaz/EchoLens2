"""Pydantic schema validation tests."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from app.crawler.schemas import LiveSession, Order, Post, Product, Review


def test_product_minimal() -> None:
    p = Product(id="jd:1", platform="jd", title="测试商品")
    assert p.id == "jd:1"
    assert p.crawled_at <= datetime.utcnow() + timedelta(seconds=1)


def test_product_rejects_extra() -> None:
    with pytest.raises(ValidationError):
        Product(id="jd:1", platform="jd", title="x", unknown_field="boom")  # type: ignore[call-arg]


def test_review_requires_hashed_author() -> None:
    with pytest.raises(ValidationError):
        Review(
            id="r1",
            product_id="p1",
            platform="jd",
            author_hash="ab",  # too short → fails
            content="ok",
        )


def test_review_ok() -> None:
    r = Review(
        id="r1",
        product_id="p1",
        platform="jd",
        author_hash="hashed_user_abc",
        content="质量不错",
        rating=5,
        sentiment="positive",
    )
    assert r.sentiment == "positive"


def test_post_defaults() -> None:
    p = Post(id="w1", platform="weibo", author_hash="hashed_x", content="加油")
    assert p.likes == 0
    assert p.sentiment == "unknown"


def test_order_negative_amount_rejected() -> None:
    with pytest.raises(ValidationError):
        Order(
            id="o1",
            user_hash="hashed_u",
            sku="sku1",
            amount=-1.0,
            placed_at=datetime.utcnow(),
        )


def test_live_session_ok() -> None:
    s = LiveSession(
        id="l1",
        platform="douyin",
        streamer_hash="hashed_s",
        title="新品发布",
        duration_seconds=3600,
        peak_viewers=12000,
        average_viewers=8000,
        started_at=datetime.utcnow(),
    )
    assert s.peak_viewers == 12000
