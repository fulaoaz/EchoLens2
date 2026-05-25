"""Decision engine — fuses simulation + prediction into one snapshot.

This is the M4 fusion layer. It takes the latest finished simulation and the
latest forecast/causal runs for a project and produces:

- A condensed snapshot of each data source (only the fields the dashboard needs)
- A rules-based risk score (0-100) and risk level (low / elevated / high)
- 3-5 deterministic, traceable recommendations

The engine is intentionally pure-Python and rules-based. Reasoning is in the
generated narrative — not in an LLM call — so every recommendation can be
attributed to the exact metric that triggered it (judge-friendly + fast).
"""

from __future__ import annotations

from typing import Any, Literal, cast

from app.services.prediction_jobs import PredictionRun, list_runs
from app.services.sim_jobs import SimJob, list_jobs

RiskLevel = Literal["low", "elevated", "high"]


# ---------- helpers -----------------------------------------------------------


def _latest_completed_sim(project_id: str) -> SimJob | None:
    """Return the most recently finished simulation job (by created_at)."""
    jobs = [j for j in list_jobs(project_id) if j.status == "completed" and j.result]
    if not jobs:
        return None
    jobs.sort(key=lambda j: j.created_at, reverse=True)
    return jobs[0]


def _latest_run_by_kind(project_id: str, kind: str) -> PredictionRun | None:
    runs = [
        r for r in list_runs(project_id)
        if r.kind == kind and r.status == "completed"
    ]
    if not runs:
        return None
    runs.sort(key=lambda r: r.created_at, reverse=True)
    return runs[0]


def _condense_forecast(run: PredictionRun) -> dict[str, Any]:
    """Slim forecast payload — keep only what the dashboard needs."""
    result = cast(dict[str, Any], run.result)
    fc_obj = result["forecast"]
    explanation = result["explanation"]
    diag = fc_obj["diagnostics"]
    history = fc_obj["history"]
    forecast = fc_obj["forecast"]

    # Sample at most 30 history points to keep payload small.
    if len(history) > 30:
        step = len(history) // 30
        history = history[::step][-30:]

    return {
        "run_id": run.id,
        "metric": run.metric,
        "metric_label": explanation["metric_label"],
        "unit": explanation["unit"],
        "headline": explanation["headline"],
        "delta_relative": explanation["delta_relative"],
        "history": history,
        "forecast": forecast,
        "diagnostics": {
            "mape": diag["mape"],
            "r2": diag["r2"],
            "trend_slope": diag["trend_slope"],
            "n_observations": diag["n_observations"],
        },
        "risk_flags": explanation.get("risk_flags", []),
        "evidence_ids": list(run.evidence_ids),
        "coverage": dict(run.coverage),
        "confidence": dict(run.confidence),
        "kg_features": dict(run.kg_features),
        "kg_linked": bool(run.kg_features),
        "created_at": run.created_at,
    }


def _condense_causal(run: PredictionRun) -> dict[str, Any]:
    result = cast(dict[str, Any], run.result)
    return {
        "run_id": run.id,
        "metric": run.metric,
        "status": result.get("status", "ok"),
        "intervention_start": result.get("intervention_start"),
        "intervention_end": result.get("intervention_end"),
        "ate": result.get("ate"),
        "ate_relative": result.get("ate_relative"),
        "p_value": result.get("p_value"),
        "ci_low": result.get("ci_low"),
        "ci_high": result.get("ci_high"),
        "narrative_seed": result.get("narrative_seed", {}),
        "evidence_ids": list(run.evidence_ids),
        "coverage": dict(run.coverage),
        "confidence": dict(run.confidence),
        "kg_features": dict(run.kg_features),
        "kg_linked": bool(run.kg_features),
        "created_at": run.created_at,
    }


def _condense_simulation(job: SimJob) -> dict[str, Any]:
    result = cast(dict[str, Any], job.result)
    rounds = result.get("rounds", [])
    last = rounds[-1] if rounds else {}
    network = result.get("network", {}) or {}
    kg_features = network.get("kg_features") or {}
    return {
        "job_id": job.id,
        "created_at": job.created_at,
        "config": {
            "num_agents": job.config.get("num_agents"),
            "num_rounds": job.config.get("num_rounds"),
            "rng_seed": job.config.get("rng_seed"),
            "kg_linked": bool(job.config.get("kg_linked")),
        },
        "population": result.get("population", {}),
        "network": {
            "nodes": network.get("nodes"),
            "edges": network.get("edges"),
            "mean_degree": network.get("mean_degree"),
        },
        "final_action_totals": result.get("final_action_totals", {}),
        "last_round": {
            "round": last.get("round"),
            "avg_sentiment": last.get("avg_sentiment"),
            "awareness": last.get("awareness"),
            "purchase_rate": last.get("purchase_rate"),
            "boycott_rate": last.get("boycott_rate"),
        },
        "rounds_total": len(rounds),
        "evidence_ids": list(result.get("evidence_ids", []) or []),
        "kg_features": dict(kg_features),
        "kg_linked": bool(kg_features) or bool(job.config.get("kg_linked")),
    }


# ---------- risk scoring ------------------------------------------------------


def _score_risk(
    sim: dict[str, Any] | None,
    forecast: dict[str, Any] | None,
    causal: dict[str, Any] | None,
) -> tuple[int, RiskLevel, list[str]]:
    """Aggregate rules-based 0-100 risk score with reason trail."""
    score = 0
    reasons: list[str] = []

    if sim:
        last = sim["last_round"]
        boycott = last.get("boycott_rate") or 0.0
        if boycott > 0.2:
            score += 25
            reasons.append(f"仿真抵制率 {boycott * 100:.1f}% 超过 20%")
        elif boycott > 0.1:
            score += 10
            reasons.append(f"仿真抵制率 {boycott * 100:.1f}% 偏高")

        avg_sent = last.get("avg_sentiment") or 0.0
        if avg_sent < -0.2:
            score += 20
            reasons.append(f"仿真终轮平均情感 {avg_sent:.2f} 显著负向")
        elif avg_sent < -0.05:
            score += 8
            reasons.append(f"仿真终轮平均情感 {avg_sent:.2f} 略偏负")

    if forecast:
        delta = forecast.get("delta_relative") or 0.0
        if delta < -0.1:
            score += 15
            reasons.append(f"预测窗内 {forecast['metric_label']} 相对下降 {abs(delta) * 100:.1f}%")
        mape = forecast["diagnostics"].get("mape") or 0.0
        if mape > 0.3:
            score += 15
            reasons.append(f"预测 MAPE {mape * 100:.1f}% 偏高，置信度受限")
        if forecast["metric"] == "gmv_synth":
            score += 5
            reasons.append("GMV 为合成估算，绝对值仅供参考")

    if causal and causal.get("status") == "ok":
        seed = causal.get("narrative_seed") or {}
        if seed.get("significant") and seed.get("direction") == "down":
            score += 30
            reasons.append("因果分析检测到显著负向干预效应")
        elif seed.get("significant") and seed.get("direction") == "up":
            # Significant positive effect actually reduces risk slightly; floor at 0.
            score = max(0, score - 5)
            reasons.append("因果分析检测到显著正向干预效应（已抵扣风险）")

    score = max(0, min(100, score))
    if score >= 60:
        level: RiskLevel = "high"
    elif score >= 30:
        level = "elevated"
    else:
        level = "low"
    return score, level, reasons


# ---------- recommendations ---------------------------------------------------


def _source_ids(
    sim: dict[str, Any] | None,
    forecast: dict[str, Any] | None,
    causal: dict[str, Any] | None,
) -> dict[str, str]:
    """Compose the per-recommendation `source_run_ids` map.

    Each recommendation that consumes a particular source carries the matching
    job/run id so the dashboard can deep-link from the rec card back to the
    sim/forecast/causal page.
    """
    out: dict[str, str] = {}
    if sim and sim.get("job_id"):
        out["simulation"] = sim["job_id"]
    if forecast and forecast.get("run_id"):
        out["forecast"] = forecast["run_id"]
    if causal and causal.get("run_id"):
        out["causal"] = causal["run_id"]
    return out


def _evidence_for_sim(sim: dict[str, Any]) -> list[str]:
    """Crawler+KG evidence ids attached to a sim-derived recommendation."""
    ids = list(sim.get("evidence_ids") or [])
    return sorted(set(ids))


def _evidence_for_pred(run: dict[str, Any]) -> list[str]:
    """Crawler+KG evidence ids attached to a prediction-derived recommendation."""
    ids = list(run.get("evidence_ids") or [])
    return sorted(set(ids))


def _recommend(
    sim: dict[str, Any] | None,
    forecast: dict[str, Any] | None,
    causal: dict[str, Any] | None,
    risk_level: RiskLevel,
) -> list[dict[str, Any]]:
    """Generate 3-5 deterministic, traceable recommendations.

    Every recommendation must carry:

    - ``source_run_ids`` — map of {simulation|forecast|causal: id} so the UI
      can jump back to the run that triggered the rec.
    - ``evidence`` — raw record / KG ids the rec leans on (so the report layer
      can render an evidence chain without re-fetching).
    """
    rec: list[dict[str, Any]] = []

    if sim is None:
        rec.append({
            "id": "missing-sim",
            "title": "先跑一次舆情仿真",
            "priority": "high",
            "rationale": "决策看板需要仿真终轮指标作为风险输入，建议先在「舆情仿真」选项卡运行至少一次基线 (200 agents · 12 轮)。",
            "evidence": [],
            "source_run_ids": _source_ids(sim, forecast, causal),
            "tags": ["前置依赖", "仿真"],
        })

    if sim is not None:
        last = sim["last_round"]
        boycott = last.get("boycott_rate") or 0.0
        if boycott > 0.2:
            rec.append({
                "id": "crisis-response",
                "title": "启动危机响应剧本",
                "priority": "high",
                "rationale": (
                    f"仿真终轮抵制率达 {boycott * 100:.1f}%，群体已进入对抗态势。"
                    "建议：暂停所有付费投放、发布官方致歉/事实澄清、转向客服/售后专项跟进。"
                ),
                "evidence": _evidence_for_sim(sim),
                "source_run_ids": {"simulation": sim["job_id"]},
                "metric_trace": {"boycott_rate": round(boycott, 4)},
                "tags": ["危机", "公关"],
            })
        elif (last.get("avg_sentiment") or 0.0) < -0.05 and boycott < 0.2:
            rec.append({
                "id": "sentiment-recovery",
                "title": "情感恢复：加大正向 KOL 投放",
                "priority": "medium",
                "rationale": (
                    f"仿真终轮平均情感 {last['avg_sentiment']:.2f} 偏负但抵制率仍可控，"
                    "建议增配 3-5 位中腰部 KOL 做使用场景种草，避免硬广刺激。"
                ),
                "evidence": _evidence_for_sim(sim),
                "source_run_ids": {"simulation": sim["job_id"]},
                "metric_trace": {"avg_sentiment": round(last["avg_sentiment"], 4)},
                "tags": ["投放", "KOL"],
            })

    if forecast is not None:
        delta = forecast.get("delta_relative") or 0.0
        label = forecast["metric_label"]
        if delta < -0.1:
            rec.append({
                "id": "defensive-budget",
                "title": f"防御性收缩：保护未来 {label}",
                "priority": "high",
                "rationale": (
                    f"预测显示 {label} 在窗内将下降约 {abs(delta) * 100:.1f}%。"
                    "建议：暂停新增预算、保留头部渠道、把节省下的预算转向客户挽留。"
                ),
                "evidence": _evidence_for_pred(forecast),
                "source_run_ids": {"forecast": forecast["run_id"]},
                "metric_trace": {
                    "metric": forecast["metric"],
                    "delta_relative": round(delta, 4),
                },
                "tags": ["预算", "预测"],
            })
        elif delta > 0.1:
            rec.append({
                "id": "amplify-momentum",
                "title": f"乘势扩张：放大 {label} 增长",
                "priority": "medium",
                "rationale": (
                    f"预测显示 {label} 在窗内将上升约 {delta * 100:.1f}%。"
                    "建议：补强供应链与客服承载，把营销节奏从拉新切到复购/口碑放大。"
                ),
                "evidence": _evidence_for_pred(forecast),
                "source_run_ids": {"forecast": forecast["run_id"]},
                "metric_trace": {
                    "metric": forecast["metric"],
                    "delta_relative": round(delta, 4),
                },
                "tags": ["扩张", "供应链"],
            })

        mape = forecast["diagnostics"].get("mape") or 0.0
        if mape > 0.3:
            rec.append({
                "id": "tighten-forecast",
                "title": "复跑预测：收紧置信区间",
                "priority": "low",
                "rationale": (
                    f"当前预测 MAPE = {mape * 100:.1f}%，超过 30% 阈值。"
                    "建议：补充更长历史窗口、下调置信度到 0.80、再跑一次拟合，视实际偏差再决定是否纳入决策。"
                ),
                "evidence": _evidence_for_pred(forecast),
                "source_run_ids": {"forecast": forecast["run_id"]},
                "metric_trace": {
                    "metric": forecast["metric"],
                    "mape": round(mape, 4),
                },
                "tags": ["预测", "拟合"],
            })

    if causal is not None and causal.get("status") == "ok":
        seed = causal.get("narrative_seed") or {}
        if seed.get("significant") and seed.get("direction") == "down":
            rec.append({
                "id": "halt-intervention",
                "title": "立即停止当前干预并复盘",
                "priority": "high",
                "rationale": (
                    f"DiD 因果分析显示干预后相对效应 {(causal.get('ate_relative') or 0) * 100:.1f}%（p={causal.get('p_value', 0):.3f}），"
                    "干预正在拖低指标。建议：撤回干预、留出 7 天观察窗、再做下一步。"
                ),
                "evidence": _evidence_for_pred(causal),
                "source_run_ids": {"causal": causal["run_id"]},
                "metric_trace": {
                    "metric": causal["metric"],
                    "ate": round(float(causal.get("ate") or 0.0), 4),
                    "p_value": round(float(causal.get("p_value") or 1.0), 4),
                },
                "tags": ["因果", "止损"],
            })
        elif seed.get("significant") and seed.get("direction") == "up":
            rec.append({
                "id": "scale-intervention",
                "title": "扩大当前干预的覆盖面",
                "priority": "medium",
                "rationale": (
                    f"DiD 因果分析显示干预后相对效应 +{(causal.get('ate_relative') or 0) * 100:.1f}%（p={causal.get('p_value', 0):.3f}），"
                    "干预正在显著拉升指标。建议：把当前干预策略横向复制到相邻品类/时段。"
                ),
                "evidence": _evidence_for_pred(causal),
                "source_run_ids": {"causal": causal["run_id"]},
                "metric_trace": {
                    "metric": causal["metric"],
                    "ate": round(float(causal.get("ate") or 0.0), 4),
                    "p_value": round(float(causal.get("p_value") or 1.0), 4),
                },
                "tags": ["因果", "放大"],
            })

    # Always provide at least one default recommendation.
    if not rec:
        rec.append({
            "id": "stay-the-course",
            "title": "维持现状并保持监测",
            "priority": "low",
            "rationale": "仿真、预测、因果三路信号目前均处于低风险区间，建议保持 7 天观察窗。",
            "evidence": [],
            "source_run_ids": _source_ids(sim, forecast, causal),
            "tags": ["维持", "监测"],
        })

    # Cap at 5 to keep dashboard tidy.
    return rec[:5]


# ---------- public API --------------------------------------------------------


def _aggregate_evidence(*blocks: dict[str, Any] | None) -> list[str]:
    """Union of evidence ids across the three condensed blocks (sorted, dedup)."""
    seen: set[str] = set()
    for block in blocks:
        if not block:
            continue
        for eid in block.get("evidence_ids") or []:
            if isinstance(eid, str) and eid:
                seen.add(eid)
    return sorted(seen)


def _aggregate_kg_features(*blocks: dict[str, Any] | None) -> dict[str, Any]:
    """Pick the richest non-empty kg_features block.

    The simulator and predictor both project the same project-scoped subgraph,
    so any non-empty block is representative. We prefer the largest by node
    count so the rollup reflects the strongest signal we have.
    """
    best: dict[str, Any] = {}
    best_nodes = -1
    for block in blocks:
        if not block:
            continue
        feats = block.get("kg_features") or {}
        if not feats:
            continue
        nodes = int(feats.get("node_count") or 0)
        if nodes > best_nodes:
            best = dict(feats)
            best_nodes = nodes
    return best


def _aggregate_confidence(
    forecast: dict[str, Any] | None,
    causal: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compose a top-level confidence rollup from the prediction blocks.

    The simulator does not expose a confidence score (it's deterministic given
    the rng seed), so the rollup only covers forecast + causal. ``reliability``
    is the min of the contributing reliabilities so the dashboard surfaces
    the weakest link.
    """
    parts: list[float] = []
    rollup: dict[str, Any] = {}
    if forecast and forecast.get("confidence"):
        rollup["forecast"] = dict(forecast["confidence"])
        parts.append(float(forecast["confidence"].get("reliability") or 0.0))
    if causal and causal.get("confidence"):
        rollup["causal"] = dict(causal["confidence"])
        parts.append(float(causal["confidence"].get("reliability") or 0.0))
    if parts:
        rollup["reliability"] = round(min(parts), 4)
    return rollup


def build_snapshot(project_id: str) -> dict[str, Any]:
    """Aggregate the latest sim + pred runs for one project into a decision snapshot."""
    sim_job = _latest_completed_sim(project_id)
    forecast_run = _latest_run_by_kind(project_id, "forecast")
    causal_run = _latest_run_by_kind(project_id, "causal")

    sim_block = _condense_simulation(sim_job) if sim_job else None
    forecast_block = _condense_forecast(forecast_run) if forecast_run else None
    causal_block = _condense_causal(causal_run) if causal_run else None

    score, level, reasons = _score_risk(sim_block, forecast_block, causal_block)
    recs = _recommend(sim_block, forecast_block, causal_block, level)

    coverage = {
        "simulation": sim_block is not None,
        "forecast": forecast_block is not None,
        "causal": causal_block is not None,
    }

    evidence_ids = _aggregate_evidence(sim_block, forecast_block, causal_block)
    kg_features = _aggregate_kg_features(sim_block, forecast_block, causal_block)
    confidence_rollup = _aggregate_confidence(forecast_block, causal_block)
    source_run_ids = {
        k: v for k, v in {
            "simulation": sim_block["job_id"] if sim_block else None,
            "forecast": forecast_block["run_id"] if forecast_block else None,
            "causal": causal_block["run_id"] if causal_block else None,
        }.items() if v
    }

    return {
        "project_id": project_id,
        "coverage": coverage,
        "simulation": sim_block,
        "forecast": forecast_block,
        "causal": causal_block,
        "risk": {"score": score, "level": level, "reasons": reasons},
        "recommendations": recs,
        "evidence_ids": evidence_ids,
        "kg_features": kg_features,
        "kg_linked": bool(kg_features),
        "confidence": confidence_rollup,
        "source_run_ids": source_run_ids,
        "model": "decision-rules-v1",
    }


__all__ = ["build_snapshot"]
