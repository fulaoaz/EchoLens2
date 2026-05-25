"""Tests for derived daily history aggregation."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.predictor.history import (
    ALL_METRICS,
    build_history,
    extract_metric,
)


def _post(date_str: str, sentiment: str = "positive") -> dict:
    return {"posted_at": date_str, "sentiment": sentiment, "platform": "weibo"}


def _review(date_str: str, sentiment: str = "negative") -> dict:
    return {"crawled_at": date_str, "sentiment": sentiment}


def _product(price: float) -> dict:
    return {"sku": f"sku-{price}", "price_current": price}


def test_empty_input_yields_min_window() -> None:
    today = date(2026, 1, 10)
    h = build_history("p1", today=today, min_days=7)
    assert h["days"] == 7
    assert h["start_date"] == "2026-01-04"
    assert h["end_date"] == "2026-01-10"
    assert all(p["volume"] == 0.0 for p in h["points"])


def test_aggregates_by_day_and_zero_fills_gaps() -> None:
    today = date(2026, 1, 10)
    posts = [_post("2026-01-05", "positive"), _post("2026-01-05", "positive")]
    reviews = [_review("2026-01-08", "negative")]
    h = build_history("p1", posts=posts, reviews=reviews, today=today, min_days=7)
    by_date = {p["date"]: p for p in h["points"]}
    assert by_date["2026-01-05"]["volume"] == 2
    assert by_date["2026-01-05"]["sentiment"] == 1.0
    assert by_date["2026-01-06"]["volume"] == 0
    assert by_date["2026-01-08"]["volume"] == 1
    assert by_date["2026-01-08"]["sentiment"] == -1.0
    assert by_date["2026-01-08"]["negative_ratio"] == 1.0


def test_synthetic_gmv_uses_avg_price_and_sentiment() -> None:
    today = date(2026, 1, 10)
    posts = [_post("2026-01-09", "positive")]
    products = [_product(100.0), _product(200.0)]
    h = build_history(
        "p1", posts=posts, products=products, today=today, min_days=2
    )
    point = next(p for p in h["points"] if p["date"] == "2026-01-09")
    # avg_price = 150, volume = 1, sentiment = 1.0 → gmv = 150 * 1 * 2 = 300
    assert point["gmv_synth"] == 300.0
    assert h["avg_price"] == 150.0


def test_avg_price_none_when_no_products() -> None:
    today = date(2026, 1, 10)
    h = build_history("p1", today=today, min_days=2)
    assert h["avg_price"] is None
    # All gmv values must be 0 in absence of price.
    assert all(p["gmv_synth"] == 0.0 for p in h["points"])


def test_extract_metric_returns_aligned_floats() -> None:
    today = date(2026, 1, 10)
    posts = [_post("2026-01-09", "positive")]
    h = build_history("p1", posts=posts, today=today, min_days=3)
    for metric in ALL_METRICS:
        series = extract_metric(h, metric)
        assert len(series) == h["days"]
        assert all(isinstance(v, float) for v in series)


def test_extract_metric_rejects_unknown() -> None:
    h = build_history("p1", today=date(2026, 1, 1), min_days=2)
    with pytest.raises(ValueError):
        extract_metric(h, "nope")  # type: ignore[arg-type]


def test_observed_window_extends_when_history_pre_dates_today() -> None:
    today = date(2026, 1, 30)
    posts = [_post("2026-01-01", "neutral")]
    h = build_history("p1", posts=posts, today=today, min_days=7)
    # Window must span from observed earliest to today.
    assert h["start_date"] == "2026-01-01"
    assert h["end_date"] == "2026-01-30"
    assert h["days"] == 30


def test_datetime_objects_are_normalised() -> None:
    today = date(2026, 1, 10)
    posts = [{"posted_at": datetime(2026, 1, 9, 14, 0), "sentiment": "positive"}]
    h = build_history("p1", posts=posts, today=today, min_days=2)
    by_date = {p["date"]: p for p in h["points"]}
    assert by_date["2026-01-09"]["volume"] == 1
