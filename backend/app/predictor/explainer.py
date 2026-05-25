"""Rule-based narrative layer — turn forecast numbers into a Chinese story.

Why rules and not an LLM call?
------------------------------

For a competition demo we want **deterministic, traceable, fast** explanations
that judges can verify line-by-line against the underlying numbers. An LLM
narrator would be more fluent but brings three problems:

1. **Provenance** — we'd need a separate provenance layer to prove the LLM
   didn't invent a "+12 % uplift" out of thin air.
2. **Latency** — the dashboard refreshes on every parameter change.
3. **Determinism** — competition reviews want the same input → same output.

The rule template here cites diagnostics verbatim (slope, MAPE, seasonal
amplitude, residual σ) and tags every sentence with the evidence it came from
so the frontend can highlight the source numbers.
"""

from __future__ import annotations

from typing import Any

from app.predictor.history import HistorySeries, MetricName
from app.predictor.timeseries import ForecastResult

# ---------- copy decks --------------------------------------------------------

_METRIC_LABELS: dict[MetricName, str] = {
    "volume": "舆情声量",
    "sentiment": "净情感",
    "gmv_synth": "合成 GMV",
    "negative_ratio": "负面占比",
}

_METRIC_UNITS: dict[MetricName, str] = {
    "volume": "条/天",
    "sentiment": "（-1~1）",
    "gmv_synth": "元/天",
    "negative_ratio": "%",
}

_TREND_BANDS = (
    (-1e-9, "持平", "趋势接近水平，业务进入平稳期"),
    (1e-9, "缓慢上行", "处于温和增长通道"),
    (5e-3, "稳定上行", "增长动能明显，建议加大投入"),
    (5e-2, "陡峭上行", "高速扩张，注意运力与产能瓶颈"),
)


def _classify_slope(slope: float, baseline: float) -> tuple[str, str]:
    """Return (label, sentence) for the trend slope, normalised by baseline."""
    if baseline > 1e-9:
        norm = slope / baseline
    else:
        norm = slope

    if norm < -5e-2:
        return "陡峭下行", "下滑速度较快，需要立即排查负面事件源"
    if norm < -5e-3:
        return "稳定下行", "出现持续衰减，建议提前部署挽回动作"
    if norm < -1e-9:
        return "缓慢下行", "存在轻微下行迹象，关注是否进入平台期"
    if norm < 1e-9:
        return "持平", "趋势接近水平，业务进入平稳期"
    if norm < 5e-3:
        return "缓慢上行", "处于温和增长通道"
    if norm < 5e-2:
        return "稳定上行", "增长动能明显，建议加大投入"
    return "陡峭上行", "高速扩张，注意运力与产能瓶颈"


def _classify_mape(mape: float) -> tuple[str, str]:
    if mape < 0.05:
        return "极佳", "历史拟合误差 <5 %，预测可信度高"
    if mape < 0.15:
        return "良好", "历史拟合误差在 15 % 以内，可作为决策参考"
    if mape < 0.30:
        return "中等", "误差在 30 % 之内，建议结合人工经验"
    return "偏弱", "拟合误差较大，预测仅供方向判断"


def _classify_seasonality(amp: float, baseline: float) -> tuple[str, str]:
    if baseline <= 1e-9:
        ratio = amp
    else:
        ratio = amp / baseline
    if ratio < 0.05:
        return "弱", "周内波动很小，几乎无周末效应"
    if ratio < 0.15:
        return "中", "存在可见周内波动，建议按工作日/周末错峰运营"
    return "强", "周内波动显著，营销节奏应明显区分工作日与周末"


def _format_value(metric: MetricName, value: float) -> str:
    if metric == "negative_ratio":
        return f"{value * 100:.1f}%"
    if metric == "sentiment":
        return f"{value:+.2f}"
    if metric == "gmv_synth":
        return f"¥{value:,.0f}"
    return f"{value:.0f}"


# ---------- main entry point --------------------------------------------------


def explain_forecast(
    *,
    metric: MetricName,
    history: HistorySeries,
    result: ForecastResult,
) -> dict[str, Any]:
    """Generate a structured narrative for one forecast run.

    Returns a dict with::

        headline:        one-line takeaway
        bullets:         list[{text, evidence: list[str]}]
        evidence_index:  dict mapping evidence id -> raw number
        risk_flags:      list[str]
    """
    diag = result.diagnostics
    cfg = result.config

    label = _METRIC_LABELS.get(metric, metric)
    unit = _METRIC_UNITS.get(metric, "")
    history_values = [p.yhat for p in result.history] or [0.0]
    baseline = max(abs(sum(history_values) / len(history_values)), 1e-9)

    last_obs = history_values[-1]
    horizon_last = result.forecast[-1].yhat if result.forecast else last_obs
    delta = horizon_last - last_obs
    delta_rel = delta / baseline if baseline > 1e-9 else 0.0

    trend_label, trend_sentence = _classify_slope(diag.trend_slope, baseline)
    mape_label, mape_sentence = _classify_mape(diag.mape)
    season_label, season_sentence = _classify_seasonality(diag.seasonal_amplitude, baseline)

    headline = (
        f"{label} 未来 {cfg.get('horizon_days', len(result.forecast))} 天预计为「{trend_label}」，"
        f"区间末端 {_format_value(metric, horizon_last)}{unit}，"
        f"较当前{('上升' if delta >= 0 else '下降')} {abs(delta_rel) * 100:.1f}%。"
    )

    bullets: list[dict[str, Any]] = [
        {
            "text": f"趋势：{trend_sentence}（斜率 {diag.trend_slope:+.4f}/天）。",
            "evidence": ["trend_slope"],
        },
        {
            "text": f"季节性：{season_sentence}（周内振幅 {diag.seasonal_amplitude:.2f}）。",
            "evidence": ["seasonal_amplitude"],
        },
        {
            "text": f"拟合质量：{mape_label}，MAPE={diag.mape * 100:.1f}%，R²={diag.r2:.2f}。",
            "evidence": ["mape", "r2"],
        },
    ]

    risk_flags: list[str] = []
    if diag.mape > 0.30:
        risk_flags.append("MAPE 高于 30 %，预测仅作为方向参考")
    if diag.n_observations < 14:
        risk_flags.append(f"历史窗口仅 {diag.n_observations} 天，建议持续累积数据")
    if metric == "gmv_synth":
        risk_flags.append("GMV 为合成代理（avg_price × volume × (1+sentiment)），非实际成交")
    if metric == "negative_ratio" and last_obs > 0.3:
        risk_flags.append("当前负面占比已超 30 %，建议立即触发危机响应")

    evidence_index = {
        "trend_slope": round(diag.trend_slope, 6),
        "trend_intercept": round(diag.trend_intercept, 4),
        "seasonal_amplitude": round(diag.seasonal_amplitude, 4),
        "mape": round(diag.mape, 4),
        "smape": round(diag.smape, 4),
        "r2": round(diag.r2, 4),
        "residual_std": round(diag.residual_std, 4),
        "n_observations": diag.n_observations,
        "horizon_days": cfg.get("horizon_days"),
        "history_avg_price": history.get("avg_price"),
    }

    return {
        "metric": metric,
        "metric_label": label,
        "unit": unit,
        "headline": headline,
        "bullets": bullets,
        "evidence_index": evidence_index,
        "risk_flags": risk_flags,
        "labels": {
            "trend": trend_label,
            "mape": mape_label,
            "seasonality": season_label,
        },
        "delta_relative": round(delta_rel, 4),
        "model": "rules-v1",
    }


# ---------- legacy stub -------------------------------------------------------


async def explain(prediction: dict[str, Any]) -> str:  # pragma: no cover
    """Legacy async LLM hook — superseded by :func:`explain_forecast`."""
    raise NotImplementedError(
        "explain() is deprecated; use explain_forecast(metric=..., history=..., result=...)."
    )


__all__ = ["explain", "explain_forecast"]
