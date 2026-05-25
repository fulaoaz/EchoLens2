"""Tests for DiD-based ATE estimation."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.predictor.causal import estimate_ate
from app.predictor.history import build_history


def _make_history(
    *,
    days: int = 30,
    cut_index: int,
    pre_value: float,
    post_value: float,
    metric_post_boost_for_volume: bool = False,
) -> dict:
    """Build a HistorySeries-shaped dict directly with deterministic values."""
    today = date(2026, 1, 1) + timedelta(days=days - 1)
    points = []
    for i in range(days):
        d = (date(2026, 1, 1) + timedelta(days=i)).isoformat()
        if i < cut_index:
            volume = pre_value
            sentiment = pre_value if not metric_post_boost_for_volume else 0.0
        else:
            volume = post_value if metric_post_boost_for_volume else pre_value
            sentiment = post_value if not metric_post_boost_for_volume else 0.0
        points.append(
            {
                "date": d,
                "volume": float(volume),
                "sentiment": float(sentiment),
                "gmv_synth": float(volume) * 100.0,
                "negative_ratio": 0.0,
            }
        )
    return {
        "project_id": "p1",
        "start_date": "2026-01-01",
        "end_date": today.isoformat(),
        "days": days,
        "avg_price": 100.0,
        "points": points,
    }


def test_positive_intervention_yields_positive_ate() -> None:
    history = _make_history(days=30, cut_index=15, pre_value=0.1, post_value=0.6)
    result = estimate_ate(
        history=history,
        metric="sentiment",
        intervention_start="2026-01-16",
    )
    assert result["status"] == "ok"
    assert result["ate"] > 0
    assert result["pre_mean"] == pytest.approx(0.1, abs=1e-6)
    assert result["post_mean"] == pytest.approx(0.6, abs=1e-6)
    assert result["pre_days"] == 15
    assert result["post_days"] == 15
    assert result["narrative_seed"]["direction"] == "up"


def test_negative_intervention_yields_negative_ate() -> None:
    history = _make_history(days=30, cut_index=15, pre_value=0.5, post_value=0.0)
    result = estimate_ate(
        history=history,
        metric="sentiment",
        intervention_start="2026-01-16",
    )
    assert result["ate"] < 0
    assert result["narrative_seed"]["direction"] == "down"


def test_significance_flag_for_clear_jump() -> None:
    history = _make_history(days=40, cut_index=20, pre_value=10.0, post_value=50.0,
                            metric_post_boost_for_volume=True)
    result = estimate_ate(
        history=history,
        metric="volume",
        intervention_start="2026-01-21",
    )
    assert result["narrative_seed"]["significant"] is True
    assert result["p_value"] < 0.05


def test_intervention_end_truncates_post_window() -> None:
    history = _make_history(days=30, cut_index=10, pre_value=1.0, post_value=5.0,
                            metric_post_boost_for_volume=True)
    result = estimate_ate(
        history=history,
        metric="volume",
        intervention_start="2026-01-11",
        intervention_end="2026-01-20",  # truncate to first 10 post days
    )
    assert result["post_days"] == 10
    assert result["pre_days"] == 10


def test_insufficient_pre_window_returns_status() -> None:
    history = _make_history(days=10, cut_index=2, pre_value=1.0, post_value=2.0)
    result = estimate_ate(
        history=history,
        metric="volume",
        intervention_start="2026-01-03",
    )
    assert result["status"] == "insufficient_data"
    assert result["pre_days"] == 0


def test_no_post_window_returns_status() -> None:
    history = _make_history(days=10, cut_index=10, pre_value=1.0, post_value=2.0)
    result = estimate_ate(
        history=history,
        metric="volume",
        intervention_start="2026-01-30",  # after all observed days
    )
    assert result["status"] == "no_post_window"


def test_invalid_metric_raises() -> None:
    history = _make_history(days=20, cut_index=10, pre_value=1.0, post_value=2.0)
    with pytest.raises(ValueError):
        estimate_ate(
            history=history,
            metric="bogus",  # type: ignore[arg-type]
            intervention_start="2026-01-11",
        )


def test_invalid_date_raises() -> None:
    history = _make_history(days=20, cut_index=10, pre_value=1.0, post_value=2.0)
    with pytest.raises(ValueError):
        estimate_ate(
            history=history,
            metric="volume",
            intervention_start="not-a-date",
        )


def test_counterfactual_series_aligned_with_post_dates() -> None:
    history = _make_history(days=20, cut_index=10, pre_value=1.0, post_value=2.0)
    result = estimate_ate(
        history=history,
        metric="volume",
        intervention_start="2026-01-11",
    )
    cf = result["counterfactual_series"]
    post = result["post_series"]
    assert len(cf) == len(post)
    assert [c["date"] for c in cf] == [p["date"] for p in post]


def test_real_history_integration() -> None:
    """Smoke test wiring build_history → estimate_ate."""
    today = date(2026, 1, 30)
    posts = [
        {"posted_at": (today - timedelta(days=i)).isoformat(), "sentiment": "positive"}
        for i in range(15)
    ]
    posts += [
        {"posted_at": (today - timedelta(days=i)).isoformat(), "sentiment": "negative"}
        for i in range(15, 30)
    ]
    history = build_history("p1", posts=posts, today=today, min_days=30)
    result = estimate_ate(
        history=history,
        metric="sentiment",
        intervention_start=(today - timedelta(days=14)).isoformat(),
    )
    assert result["status"] == "ok"
    assert result["pre_days"] >= 3
    assert result["post_days"] >= 1
