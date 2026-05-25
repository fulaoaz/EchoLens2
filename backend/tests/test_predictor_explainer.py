"""Tests for the rule-based forecast explainer."""

from __future__ import annotations

from datetime import date, timedelta

from app.predictor.explainer import explain_forecast
from app.predictor.history import build_history
from app.predictor.timeseries import forecast_series


def _build(metric: str, slope: float, intercept: float = 50.0, n: int = 30) -> dict:
    today = date(2026, 1, 30)
    posts = [
        {
            "posted_at": (today - timedelta(days=n - 1 - i)).isoformat(),
            "sentiment": "positive" if (i % 3 != 0) else "negative",
        }
        for i in range(n)
    ]
    history = build_history("p1", posts=posts, today=today, min_days=n)
    series = [intercept + slope * i for i in range(n)]
    history_dates = [p["date"] for p in history["points"]]
    floor = None if metric == "sentiment" else 0.0
    result = forecast_series(
        series, horizon_days=10, history_dates=history_dates, floor=floor
    )
    return {"history": history, "result": result}


def test_explain_returns_full_payload_shape() -> None:
    bundle = _build("volume", slope=2.0)
    out = explain_forecast(metric="volume", history=bundle["history"], result=bundle["result"])
    assert "headline" in out
    assert isinstance(out["bullets"], list) and len(out["bullets"]) >= 3
    assert "evidence_index" in out
    assert "risk_flags" in out
    assert out["model"] == "rules-v1"


def test_upward_trend_label() -> None:
    bundle = _build("volume", slope=5.0, intercept=20.0)
    out = explain_forecast(metric="volume", history=bundle["history"], result=bundle["result"])
    assert "上行" in out["labels"]["trend"] or out["labels"]["trend"] == "陡峭上行"
    assert out["delta_relative"] > 0


def test_downward_trend_label() -> None:
    bundle = _build("volume", slope=-3.0, intercept=200.0)
    out = explain_forecast(metric="volume", history=bundle["history"], result=bundle["result"])
    assert "下行" in out["labels"]["trend"]
    assert out["delta_relative"] < 0


def test_flat_trend_label() -> None:
    bundle = _build("volume", slope=0.0, intercept=100.0)
    out = explain_forecast(metric="volume", history=bundle["history"], result=bundle["result"])
    assert out["labels"]["trend"] == "持平"


def test_gmv_synth_carries_synthetic_warning() -> None:
    bundle = _build("gmv_synth", slope=10.0)
    out = explain_forecast(
        metric="gmv_synth", history=bundle["history"], result=bundle["result"]
    )
    assert any("合成" in flag for flag in out["risk_flags"])


def test_high_negative_ratio_triggers_crisis_flag() -> None:
    today = date(2026, 1, 30)
    posts = [
        {"posted_at": (today - timedelta(days=i)).isoformat(), "sentiment": "negative"}
        for i in range(20)
    ]
    history = build_history("p1", posts=posts, today=today, min_days=20)
    series = [0.5] * 20  # constant high negative_ratio
    result = forecast_series(series, horizon_days=7, floor=0.0)
    out = explain_forecast(metric="negative_ratio", history=history, result=result)
    assert any("危机" in flag or "30" in flag for flag in out["risk_flags"])


def test_short_history_warning() -> None:
    today = date(2026, 1, 8)
    posts = [
        {"posted_at": (today - timedelta(days=i)).isoformat(), "sentiment": "positive"}
        for i in range(7)
    ]
    history = build_history("p1", posts=posts, today=today, min_days=7)
    series = [1.0] * 7
    result = forecast_series(series, horizon_days=5, floor=0.0)
    out = explain_forecast(metric="volume", history=history, result=result)
    assert any("历史窗口" in flag for flag in out["risk_flags"])


def test_evidence_index_contains_diagnostics() -> None:
    bundle = _build("volume", slope=1.5)
    out = explain_forecast(metric="volume", history=bundle["history"], result=bundle["result"])
    idx = out["evidence_index"]
    for key in ("trend_slope", "seasonal_amplitude", "mape", "r2", "n_observations"):
        assert key in idx


def test_metric_label_translated() -> None:
    bundle = _build("sentiment", slope=0.01, intercept=0.1)
    out = explain_forecast(
        metric="sentiment", history=bundle["history"], result=bundle["result"]
    )
    assert out["metric_label"] == "净情感"
