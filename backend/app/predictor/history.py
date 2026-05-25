"""Derive daily time-series metrics from raw crawler records.

The predictor needs at least one continuous daily series before it can fit a
trend / seasonal model. We aggregate the three crawler streams into:

- ``volume``         — total posts + reviews observed on that day
- ``sentiment``      — net sentiment in [-1, 1] (positive minus negative ratio)
- ``gmv_synth``      — synthetic GMV proxy = avg_price · volume · (1 + sentiment)
- ``negative_ratio`` — share of negative-sentiment records (for early-warning)

These are derived metrics, **not** observed sales. The fact is exposed via the
``synthetic`` flag in the response so the frontend can label them honestly.

Pure-Python; no I/O. Caller passes already-loaded record dicts (same shape the
seed-report consumes), so this module stays test-friendly without DuckDB.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import date, datetime, timedelta
from statistics import mean
from typing import Any, Literal, TypedDict

MetricName = Literal["volume", "sentiment", "gmv_synth", "negative_ratio"]
ALL_METRICS: tuple[MetricName, ...] = (
    "volume",
    "sentiment",
    "gmv_synth",
    "negative_ratio",
)


class DailyPoint(TypedDict):
    """One row of the derived daily time series."""

    date: str  # ISO date "YYYY-MM-DD"
    volume: float
    sentiment: float
    gmv_synth: float
    negative_ratio: float


class CoverageInfo(TypedDict):
    """How well the observed records cover the analysis window."""

    observed_days: int
    total_days: int
    observed_ratio: float
    record_counts: dict[str, int]


class HistorySeries(TypedDict):
    """Complete derived history attached to a project."""

    project_id: str
    start_date: str
    end_date: str
    days: int
    avg_price: float | None
    points: list[DailyPoint]
    coverage: CoverageInfo


# ---------- helpers -----------------------------------------------------------


def _to_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None
    return None


def _sentiment_score(pos: int, neg: int, total: int) -> float:
    """Map (pos, neg) counts to [-1, 1].

    Empty days return 0 (neutral) rather than NaN so downstream models can fit
    a continuous series without imputation.
    """
    if total <= 0:
        return 0.0
    return round((pos - neg) / total, 4)


def _negative_ratio(neg: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(neg / total, 4)


def _avg_price(products: Sequence[dict[str, Any]]) -> float | None:
    prices = [
        p["price_current"]
        for p in products
        if isinstance(p.get("price_current"), (int, float))
        and p["price_current"] > 0
    ]
    return round(mean(prices), 2) if prices else None


# ---------- main builder ------------------------------------------------------


def build_history(
    project_id: str,
    *,
    products: Iterable[dict[str, Any]] = (),
    reviews: Iterable[dict[str, Any]] = (),
    posts: Iterable[dict[str, Any]] = (),
    today: date | None = None,
    min_days: int = 7,
) -> HistorySeries:
    """Aggregate raw records into a continuous daily series.

    Missing days between ``start_date`` and ``end_date`` are filled with zeros
    so the predictor sees a fixed-cadence series.

    ``min_days`` enforces a minimum window — if observed records span fewer
    days, we backfill with zero-volume days so trend fitting still has a
    meaningful x-axis.
    """
    products_list = list(products)
    reviews_list = list(reviews)
    posts_list = list(posts)

    # Per-day counters keyed by date object.
    pos_count: defaultdict[date, int] = defaultdict(int)
    neg_count: defaultdict[date, int] = defaultdict(int)
    neu_count: defaultdict[date, int] = defaultdict(int)
    total_count: defaultdict[date, int] = defaultdict(int)

    def _bump(d: date | None, sentiment: str) -> None:
        if d is None:
            return
        total_count[d] += 1
        if sentiment == "positive":
            pos_count[d] += 1
        elif sentiment == "negative":
            neg_count[d] += 1
        else:
            neu_count[d] += 1

    for p in posts_list:
        _bump(_to_date(p.get("posted_at") or p.get("crawled_at")), p.get("sentiment", "unknown"))
    for r in reviews_list:
        _bump(_to_date(r.get("crawled_at")), r.get("sentiment", "unknown"))

    today = today or datetime.utcnow().date()
    if total_count:
        observed_start = min(total_count)
        observed_end = max(total_count)
    else:
        observed_end = today
        observed_start = today - timedelta(days=min_days - 1)

    end_date = max(observed_end, today)
    start_date = min(observed_start, end_date - timedelta(days=min_days - 1))

    avg_price = _avg_price(products_list)
    points: list[DailyPoint] = []
    cursor = start_date
    while cursor <= end_date:
        total = total_count.get(cursor, 0)
        pos = pos_count.get(cursor, 0)
        neg = neg_count.get(cursor, 0)
        sentiment = _sentiment_score(pos, neg, total)
        volume = float(total)
        # Synthetic GMV — labeled clearly downstream as a proxy.
        if avg_price is not None and volume > 0:
            gmv = round(avg_price * volume * (1.0 + sentiment), 2)
        else:
            gmv = 0.0
        points.append(
            {
                "date": cursor.isoformat(),
                "volume": volume,
                "sentiment": sentiment,
                "gmv_synth": gmv,
                "negative_ratio": _negative_ratio(neg, total),
            }
        )
        cursor += timedelta(days=1)

    observed_days = sum(1 for p in points if p["volume"] > 0)
    total_days = len(points)
    coverage: CoverageInfo = {
        "observed_days": observed_days,
        "total_days": total_days,
        "observed_ratio": round(observed_days / total_days, 4) if total_days else 0.0,
        "record_counts": {
            "products": len(products_list),
            "reviews": len(reviews_list),
            "posts": len(posts_list),
        },
    }

    return {
        "project_id": project_id,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "days": len(points),
        "avg_price": avg_price,
        "points": points,
        "coverage": coverage,
    }


def extract_metric(history: HistorySeries, metric: MetricName) -> list[float]:
    """Pull one metric column out of a history series as a flat float list."""
    if metric not in ALL_METRICS:
        raise ValueError(f"unknown metric {metric!r}; expected one of {ALL_METRICS}")
    return [float(p[metric]) for p in history["points"]]


__all__ = [
    "ALL_METRICS",
    "CoverageInfo",
    "DailyPoint",
    "HistorySeries",
    "MetricName",
    "build_history",
    "extract_metric",
]
