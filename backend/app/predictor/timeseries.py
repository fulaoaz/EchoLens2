"""Lightweight time-series forecaster — pure numpy.

Why not Prophet / NeuralProphet?
--------------------------------

The optional ``[prediction]`` extras are kept available for users who want
production-grade forecasting with full Stan / PyTorch toolchains, but the
default path here is intentionally tiny:

- **Trend**       : ordinary least-squares linear regression on day index.
- **Seasonality** : weekly Fourier basis (sin/cos at period 7) — captures the
                    "weekend dip" most e-commerce series exhibit.
- **Residuals**   : Gaussian noise model gives a 95 % confidence band
                    (``yhat ± 1.96 σ_resid``).

This costs <10 ms for a 90-day series, runs everywhere numpy runs, and is
deterministic — perfect for a dashboard that wants a fast, explainable baseline.

The math is exposed via ``ForecastResult`` so the explanation layer can quote
slope / amplitude / fit-quality without re-running anything.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

import numpy as np

# ---------- result types ------------------------------------------------------


@dataclass
class ForecastPoint:
    ts: str  # ISO date "YYYY-MM-DD"
    yhat: float
    yhat_lower: float
    yhat_upper: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "yhat": round(self.yhat, 4),
            "yhat_lower": round(self.yhat_lower, 4),
            "yhat_upper": round(self.yhat_upper, 4),
        }


@dataclass
class FitDiagnostics:
    """Numbers the explanation layer cites verbatim — never recomputed downstream."""

    n_observations: int
    trend_slope: float
    trend_intercept: float
    seasonal_amplitude: float
    residual_std: float
    mape: float  # mean absolute percentage error on the historical fit (0..∞)
    smape: float  # symmetric MAPE in [0, 2]
    r2: float  # coefficient of determination

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_observations": self.n_observations,
            "trend_slope": round(self.trend_slope, 6),
            "trend_intercept": round(self.trend_intercept, 4),
            "seasonal_amplitude": round(self.seasonal_amplitude, 4),
            "residual_std": round(self.residual_std, 4),
            "mape": round(self.mape, 4),
            "smape": round(self.smape, 4),
            "r2": round(self.r2, 4),
        }


@dataclass
class ForecastResult:
    history: list[ForecastPoint]
    forecast: list[ForecastPoint]
    diagnostics: FitDiagnostics
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "history": [p.to_dict() for p in self.history],
            "forecast": [p.to_dict() for p in self.forecast],
            "diagnostics": self.diagnostics.to_dict(),
            "config": self.config,
        }


# ---------- model -------------------------------------------------------------


def _design_matrix(t: np.ndarray, period: int = 7) -> np.ndarray:
    """Trend (linear) + Fourier weekly seasonality (1 harmonic).

    Columns: [1, t, sin(2πt/7), cos(2πt/7)].
    """
    omega = 2 * math.pi / period
    return np.column_stack(
        (
            np.ones_like(t, dtype=float),
            t.astype(float),
            np.sin(omega * t),
            np.cos(omega * t),
        )
    )


def _fit_metrics(y: np.ndarray, yhat: np.ndarray) -> tuple[float, float, float]:
    """Return (mape, smape, r2). Robust to zeros and tiny values."""
    eps = 1e-9
    abs_err = np.abs(y - yhat)
    denom_mape = np.where(np.abs(y) > eps, np.abs(y), np.nan)
    mape_arr = abs_err / denom_mape
    mape = float(np.nanmean(mape_arr)) if np.any(~np.isnan(mape_arr)) else 0.0

    denom_s = (np.abs(y) + np.abs(yhat))
    smape_arr = np.where(denom_s > eps, 2 * abs_err / denom_s, 0.0)
    smape = float(np.mean(smape_arr))

    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > eps else 0.0
    return mape, smape, r2


def _start_date(history_dates: Sequence[str] | None) -> date:
    if history_dates:
        try:
            return datetime.fromisoformat(history_dates[-1]).date()
        except ValueError:
            pass
    return datetime.utcnow().date()


def forecast_series(
    series: Sequence[float],
    *,
    horizon_days: int = 14,
    history_dates: Sequence[str] | None = None,
    seasonality_period: int = 7,
    confidence: float = 0.95,
    floor: float | None = None,
) -> ForecastResult:
    """Fit a trend + weekly Fourier model on ``series`` and forecast forward.

    Parameters
    ----------
    series
        Observed daily values (must have at least ``seasonality_period + 1``
        points; padded with zeros if shorter).
    horizon_days
        How many future days to predict (1..200).
    history_dates
        ISO date strings aligned 1:1 with ``series``. If provided, the forecast
        anchors itself to ``history_dates[-1] + 1 day``. Otherwise it starts
        from "today + 1".
    seasonality_period
        Days per seasonal cycle. Default 7 (weekly). Set to 1 to disable
        seasonality (trend only).
    confidence
        Two-sided coverage of the prediction band (0 < c < 1). 0.95 → ±1.96σ.
    floor
        Optional non-negative floor — values clipped below this. Use 0.0 for
        volume / GMV series; ``None`` for sentiment which can be negative.
    """
    if not 1 <= horizon_days <= 200:
        raise ValueError("horizon_days must be in [1, 200]")
    if not 0.5 <= confidence < 1.0:
        raise ValueError("confidence must be in [0.5, 1.0)")
    if seasonality_period < 1:
        raise ValueError("seasonality_period must be >= 1")

    y_raw = np.array(list(series), dtype=float)
    if y_raw.size == 0:
        y_raw = np.zeros(seasonality_period + 1, dtype=float)
    elif y_raw.size < seasonality_period + 1:
        pad = np.zeros(seasonality_period + 1 - y_raw.size, dtype=float)
        y_raw = np.concatenate([pad, y_raw])

    n = y_raw.size
    t_hist = np.arange(n, dtype=float)
    use_seasonality = seasonality_period > 1
    if use_seasonality:
        x_hist = _design_matrix(t_hist, period=seasonality_period)
    else:
        x_hist = np.column_stack((np.ones_like(t_hist), t_hist))

    # OLS via lstsq — stable on near-singular designs.
    beta, *_ = np.linalg.lstsq(x_hist, y_raw, rcond=None)
    yhat_hist = x_hist @ beta
    residuals = y_raw - yhat_hist
    sigma = float(np.std(residuals, ddof=1)) if n > 2 else 0.0

    # 95 % normal band by default — small tables for common levels.
    z_table = {0.80: 1.282, 0.90: 1.645, 0.95: 1.960, 0.99: 2.576}
    z = z_table.get(round(confidence, 2), 1.960)

    seasonal_amp = (
        float(math.hypot(beta[2], beta[3])) if use_seasonality else 0.0
    )
    trend_intercept = float(beta[0])
    trend_slope = float(beta[1])

    mape, smape, r2 = _fit_metrics(y_raw, yhat_hist)

    diagnostics = FitDiagnostics(
        n_observations=n,
        trend_slope=trend_slope,
        trend_intercept=trend_intercept,
        seasonal_amplitude=seasonal_amp,
        residual_std=sigma,
        mape=mape,
        smape=smape,
        r2=r2,
    )

    anchor = _start_date(history_dates)

    def _clip(v: float) -> float:
        return v if floor is None else max(v, floor)

    history_points: list[ForecastPoint] = []
    for i, (yh, yo) in enumerate(zip(yhat_hist, y_raw, strict=False)):
        # Use the anchor as `last historical day` so dates align with input.
        d = anchor - timedelta(days=n - 1 - i)
        history_points.append(
            ForecastPoint(
                ts=d.isoformat(),
                yhat=_clip(float(yh)),
                yhat_lower=_clip(float(yh - z * sigma)),
                yhat_upper=_clip(float(yh + z * sigma)),
            )
        )

    t_future = np.arange(n, n + horizon_days, dtype=float)
    if use_seasonality:
        x_future = _design_matrix(t_future, period=seasonality_period)
    else:
        x_future = np.column_stack((np.ones_like(t_future), t_future))
    yhat_future = x_future @ beta

    forecast_points: list[ForecastPoint] = []
    for i, yh in enumerate(yhat_future, start=1):
        d = anchor + timedelta(days=i)
        forecast_points.append(
            ForecastPoint(
                ts=d.isoformat(),
                yhat=_clip(float(yh)),
                yhat_lower=_clip(float(yh - z * sigma)),
                yhat_upper=_clip(float(yh + z * sigma)),
            )
        )

    config = {
        "horizon_days": horizon_days,
        "seasonality_period": seasonality_period,
        "confidence": confidence,
        "floor": floor,
        "model": "ols-trend+fourier-weekly",
    }
    return ForecastResult(
        history=history_points,
        forecast=forecast_points,
        diagnostics=diagnostics,
        config=config,
    )


# ---------- compatibility shim ------------------------------------------------


def forecast_gmv(
    history: list[dict[str, Any]],
    horizon_days: int = 30,
) -> dict[str, Any]:
    """Backwards-compatible shim used by the original M3 stub.

    ``history`` is the daily-points list emitted by ``predictor.history``.
    Falls back gracefully if the input is empty.
    """
    series = [float(p.get("gmv_synth", 0.0)) for p in history]
    history_dates = [str(p.get("date")) for p in history if p.get("date")]
    result = forecast_series(
        series,
        horizon_days=horizon_days,
        history_dates=history_dates or None,
        floor=0.0,
    )
    return result.to_dict()


__all__ = [
    "FitDiagnostics",
    "ForecastPoint",
    "ForecastResult",
    "forecast_gmv",
    "forecast_series",
]
