"""Tests for the numpy time-series forecaster."""

from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from app.predictor.timeseries import (
    ForecastResult,
    forecast_gmv,
    forecast_series,
)


def _linear_series(n: int, slope: float, intercept: float = 10.0) -> list[float]:
    return [intercept + slope * i for i in range(n)]


def _seasonal_series(n: int, amp: float = 2.0, base: float = 10.0) -> list[float]:
    return [base + amp * math.sin(2 * math.pi * i / 7) for i in range(n)]


def test_forecast_returns_correct_horizon_shape() -> None:
    series = _linear_series(30, slope=0.5)
    result = forecast_series(series, horizon_days=14)
    assert isinstance(result, ForecastResult)
    assert len(result.history) == 30
    assert len(result.forecast) == 14


def test_trend_slope_recovered_within_tolerance() -> None:
    series = _linear_series(60, slope=1.0, intercept=5.0)
    result = forecast_series(series, horizon_days=10, seasonality_period=1)
    assert abs(result.diagnostics.trend_slope - 1.0) < 1e-6
    assert abs(result.diagnostics.trend_intercept - 5.0) < 1e-6


def test_seasonal_amplitude_matches_input() -> None:
    series = _seasonal_series(60, amp=3.0)
    result = forecast_series(series, horizon_days=7)
    # Fourier amplitude = sqrt(b^2 + c^2) ≈ input amplitude.
    assert abs(result.diagnostics.seasonal_amplitude - 3.0) < 0.5


def test_floor_clamps_predictions() -> None:
    series = _linear_series(20, slope=-2.0, intercept=5.0)
    result = forecast_series(series, horizon_days=10, floor=0.0)
    assert all(p.yhat >= 0.0 for p in result.history + result.forecast)
    assert all(p.yhat_lower >= 0.0 for p in result.history + result.forecast)


def test_no_floor_allows_negative_values() -> None:
    series = _linear_series(20, slope=-2.0, intercept=5.0)
    result = forecast_series(series, horizon_days=10, floor=None)
    assert any(p.yhat < 0.0 for p in result.forecast)


def test_history_dates_anchor_forecast() -> None:
    series = _linear_series(10, slope=0.1)
    history_dates = [
        (date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(10)
    ]
    result = forecast_series(series, horizon_days=3, history_dates=history_dates)
    assert result.history[-1].ts == "2026-01-10"
    assert result.forecast[0].ts == "2026-01-11"
    assert result.forecast[-1].ts == "2026-01-13"


def test_mape_low_for_perfect_linear_fit() -> None:
    series = _linear_series(30, slope=0.5, intercept=20.0)
    result = forecast_series(series, horizon_days=5, seasonality_period=1)
    assert result.diagnostics.mape < 1e-3
    assert result.diagnostics.r2 > 0.999


def test_short_series_padded_to_minimum() -> None:
    series = [1.0, 2.0]
    result = forecast_series(series, horizon_days=4, seasonality_period=7)
    # Padded to seasonality_period + 1 = 8 history points.
    assert len(result.history) == 8


def test_invalid_horizon_rejected() -> None:
    with pytest.raises(ValueError):
        forecast_series([1.0] * 10, horizon_days=0)
    with pytest.raises(ValueError):
        forecast_series([1.0] * 10, horizon_days=300)


def test_invalid_confidence_rejected() -> None:
    with pytest.raises(ValueError):
        forecast_series([1.0] * 10, horizon_days=5, confidence=0.4)
    with pytest.raises(ValueError):
        forecast_series([1.0] * 10, horizon_days=5, confidence=1.0)


def test_confidence_band_widens_with_higher_level() -> None:
    series = _linear_series(20, slope=0.5) + [0.0, 1.0, -1.0]  # add some noise
    r80 = forecast_series(series, horizon_days=5, confidence=0.80)
    r99 = forecast_series(series, horizon_days=5, confidence=0.99)
    width80 = r80.forecast[0].yhat_upper - r80.forecast[0].yhat_lower
    width99 = r99.forecast[0].yhat_upper - r99.forecast[0].yhat_lower
    assert width99 > width80


def test_to_dict_round_trip() -> None:
    series = _linear_series(15, slope=0.2)
    result = forecast_series(series, horizon_days=4)
    d = result.to_dict()
    assert "history" in d and "forecast" in d
    assert "diagnostics" in d and "config" in d
    assert d["config"]["horizon_days"] == 4
    assert d["diagnostics"]["n_observations"] == 15


def test_forecast_gmv_legacy_shim() -> None:
    history = [
        {"date": (date(2026, 1, 1) + timedelta(days=i)).isoformat(), "gmv_synth": 100 + i}
        for i in range(20)
    ]
    out = forecast_gmv(history, horizon_days=7)
    assert "history" in out and "forecast" in out
    assert len(out["forecast"]) == 7
