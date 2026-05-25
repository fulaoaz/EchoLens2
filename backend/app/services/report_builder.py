"""Report builder — markdown report from a decision snapshot.

The builder is a thin renderer on top of ``decision_engine.build_snapshot``.
It does not query sim_jobs / prediction_jobs directly — keeping the snapshot
as the single source of truth ensures the dashboard and the exported report
stay in sync.

Design notes
------------

- Pure-Python, deterministic. Same input → same output.
- Markdown only (M5). PDF/print is M7.
- Reports are persisted to DuckDB (M6.1). The registry keeps at most 32
  rows: every ``add()`` inserts a new row and prunes anything beyond the
  most-recent 32 by ``seq``. ``seq`` is a monotonically-increasing BIGINT
  that guarantees stable newest-first ordering even when several reports
  are generated within the same wall-clock second.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.services.decision_engine import build_snapshot
from app.services.duckdb_store import connect
from app.services.project_store import get_store
from app.services.reliability_tier import tier_for as _tier_for

# ---------- record + registry -------------------------------------------------


@dataclass
class ReportRecord:
    """Persisted record of one generated markdown report."""

    id: str
    project_id: str
    title: str
    format: str  # "markdown" — kept as field for forward-compat with PDF
    markdown: str
    snapshot: dict[str, Any]
    generated_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds")
    )

    def summary(self) -> dict[str, Any]:
        """Lightweight view used by ``GET /api/report``."""
        return {
            "id": self.id,
            "projectId": self.project_id,
            "title": self.title,
            "format": self.format,
            "url": f"/api/report/{self.id}/download",
            "generatedAt": self.generated_at,
        }

    def full(self) -> dict[str, Any]:
        return {
            **self.summary(),
            "markdown": self.markdown,
            "snapshot": self.snapshot,
        }


_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS reports (
    id           VARCHAR PRIMARY KEY,
    project_id   VARCHAR NOT NULL,
    title        VARCHAR NOT NULL,
    format       VARCHAR NOT NULL,
    markdown     VARCHAR NOT NULL,
    snapshot     VARCHAR NOT NULL,
    generated_at VARCHAR NOT NULL,
    seq          BIGINT  NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reports_project_seq
    ON reports (project_id, seq DESC);
"""


def _row_to_record(row: tuple[Any, ...]) -> ReportRecord:
    rid, pid, title, fmt, markdown, snapshot_json, generated_at, _seq = row
    return ReportRecord(
        id=rid,
        project_id=pid,
        title=title,
        format=fmt,
        markdown=markdown,
        snapshot=json.loads(snapshot_json or "{}"),
        generated_at=generated_at,
    )


class _DuckDBReportRegistry:
    """DuckDB-backed registry, capped at 32 most-recent rows globally.

    Thread-safe via a coarse ``threading.Lock`` — DuckDB's writer is
    single-threaded per file, the lock just keeps Python-level
    read-modify-write paths honest (next-seq computation, prune step).
    """

    _MAX = 32
    _COLUMNS = (
        "id, project_id, title, format, markdown, snapshot, generated_at, seq"
    )

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with connect() as conn:
            conn.execute(_SCHEMA_DDL)

    def _next_seq(self, conn: Any) -> int:
        row = conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM reports").fetchone()
        return int(row[0]) if row else 1

    def add(self, rec: ReportRecord) -> None:
        with self._lock, connect() as conn:
            seq = self._next_seq(conn)
            conn.execute(
                f"INSERT INTO reports ({self._COLUMNS}) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    rec.id,
                    rec.project_id,
                    rec.title,
                    rec.format,
                    rec.markdown,
                    json.dumps(rec.snapshot, ensure_ascii=False),
                    rec.generated_at,
                    seq,
                ],
            )
            # Prune anything beyond the 32 most-recent rows globally.
            conn.execute(
                "DELETE FROM reports WHERE id NOT IN ("
                "  SELECT id FROM reports ORDER BY seq DESC LIMIT ?"
                ")",
                [self._MAX],
            )

    def get(self, report_id: str) -> ReportRecord | None:
        with connect() as conn:
            row = conn.execute(
                f"SELECT {self._COLUMNS} FROM reports WHERE id = ?",
                [report_id],
            ).fetchone()
        return _row_to_record(row) if row else None

    def list_for_project(self, project_id: str) -> list[ReportRecord]:
        with connect() as conn:
            rows = conn.execute(
                f"SELECT {self._COLUMNS} FROM reports "
                "WHERE project_id = ? ORDER BY seq DESC",
                [project_id],
            ).fetchall()
        return [_row_to_record(r) for r in rows]

    def clear(self) -> None:
        with self._lock, connect() as conn:
            conn.execute("DELETE FROM reports")


_registry: _DuckDBReportRegistry | None = None
_registry_lock = threading.Lock()


def _get_registry() -> _DuckDBReportRegistry:
    """Lazy singleton — created on first use so tests can patch settings first."""
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = _DuckDBReportRegistry()
    return _registry


# ---------- markdown rendering ------------------------------------------------


def _fmt_pct(v: float | int | None, digits: int = 1) -> str:
    if v is None:
        return "—"
    return f"{v * 100:.{digits}f}%"


def _fmt_num(v: float | int | None, digits: int = 2) -> str:
    if v is None:
        return "—"
    return f"{float(v):.{digits}f}"


# NOTE: This wrapper is preserved as the public name used by the existing
# tests + render code, but the threshold logic itself lives in
# ``app.services.reliability_tier`` — the single authoritative copy shared
# with ``report_html`` and the frontend's ``useReliabilityTier`` composable.
# Do NOT inline ``0.7`` / ``0.4`` here; doing so would re-introduce the four-
# way duplication that the shared module was created to remove.
def _reliability_tier(v: float | int | None) -> tuple[str, str]:
    """Map a weakest-link reliability into a printable ``(label, slug)`` tier.

    Thin alias around :func:`app.services.reliability_tier.tier_for`. Kept so
    older callers and tests reading ``report_builder._reliability_tier`` keep
    working while the threshold itself stays in one place.
    """
    return _tier_for(v)


def _fmt_evidence(ids: list[str], *, limit: int = 8) -> str:
    """Render an evidence-id chain as inline-code, capping the visible head."""
    if not ids:
        return "—"
    head = ids[:limit]
    tail = len(ids) - len(head)
    chunk = ", ".join(f"`{eid}`" for eid in head)
    if tail > 0:
        chunk += f" 等 {len(ids)} 项"
    return chunk


def _fmt_kv(mapping: dict[str, Any]) -> str:
    """Compact key=value rendering for metric_trace / kg_features blocks."""
    if not mapping:
        return "—"
    parts: list[str] = []
    for k, v in mapping.items():
        if isinstance(v, float):
            parts.append(f"`{k}={v:.4f}`")
        else:
            parts.append(f"`{k}={v}`")
    return ", ".join(parts)


def _render_coverage(coverage: dict[str, bool]) -> str:
    return (
        f"- 舆情仿真：{'✅' if coverage.get('simulation') else '⛔️ 未跑'}\n"
        f"- 预测拟合：{'✅' if coverage.get('forecast') else '⛔️ 未跑'}\n"
        f"- 因果分析：{'✅' if coverage.get('causal') else '⛔️ 未跑'}\n"
    )


_RISK_LABEL = {"low": "低风险", "elevated": "中等风险", "high": "高风险"}


def _render_risk(risk: dict[str, Any]) -> str:
    score = risk.get("score", 0)
    level = risk.get("level", "low")
    reasons = risk.get("reasons") or []
    lines = [
        f"**综合风险评分：{score} / 100 · {_RISK_LABEL.get(level, level)}**",
        "",
    ]
    if reasons:
        lines.append("触发依据：")
        for r in reasons:
            lines.append(f"- {r}")
    else:
        lines.append("- 暂无显著风险触发项")
    lines.append("")
    return "\n".join(lines)


def _render_simulation(sim: dict[str, Any] | None) -> str:
    if not sim:
        return "_未运行仿真，跳过本节。_\n"
    last = sim.get("last_round", {}) or {}
    cfg = sim.get("config", {}) or {}
    net = sim.get("network", {}) or {}
    totals = sim.get("final_action_totals", {}) or {}
    lines = [
        f"- Job ID：`{sim.get('job_id', '—')}`",
        f"- 配置：Agents = {cfg.get('num_agents', '—')} · Rounds = {cfg.get('num_rounds', '—')} · Seed = {cfg.get('rng_seed', '—')}",
        f"- 网络：节点 {net.get('nodes', '—')} · 边 {net.get('edges', '—')} · 平均度 {_fmt_num(net.get('mean_degree'))}",
        f"- 终轮抵制率：{_fmt_pct(last.get('boycott_rate'))}",
        f"- 终轮平均情感：{_fmt_num(last.get('avg_sentiment'))}",
        f"- 终轮购买率：{_fmt_pct(last.get('purchase_rate'))}",
        f"- 终轮认知率：{_fmt_pct(last.get('awareness'))}",
        f"- 总轮次：{sim.get('rounds_total', '—')}",
    ]
    if totals:
        items = ", ".join(f"{k}={v}" for k, v in totals.items())
        lines.append(f"- 行动累计：{items}")
    kg = sim.get("kg_features") or {}
    if kg:
        lines.append(
            f"- 图谱链接：✅ 节点 {kg.get('node_count', '—')} · 边 {kg.get('edge_count', '—')} ·"
            f" KOL {kg.get('kol_count', '—')} · 话题 {kg.get('topic_count', '—')}"
        )
    elif sim.get("kg_linked"):
        lines.append("- 图谱链接：✅（无可用特征统计）")
    ev = sim.get("evidence_ids") or []
    if ev:
        lines.append(f"- 证据链：{_fmt_evidence(ev)}")
    lines.append("")
    return "\n".join(lines)


def _render_forecast(fc: dict[str, Any] | None) -> str:
    if not fc:
        return "_未运行预测，跳过本节。_\n"
    diag = fc.get("diagnostics", {}) or {}
    conf = fc.get("confidence", {}) or {}
    cov = fc.get("coverage", {}) or {}
    kg = fc.get("kg_features") or {}
    lines = [
        f"- Run ID：`{fc.get('run_id', '—')}`",
        f"- 指标：{fc.get('metric_label', fc.get('metric', '—'))}",
        f"- 预测窗内相对变化：{_fmt_pct(fc.get('delta_relative'))}",
        f"- 解释：{fc.get('headline', '—')}",
        f"- MAPE：{_fmt_pct(diag.get('mape'))} · R²：{_fmt_num(diag.get('r2'))}",
        f"- 趋势斜率：{_fmt_num(diag.get('trend_slope'), 4)} · 观察点：{diag.get('n_observations', '—')}",
    ]
    if conf:
        lines.append(
            f"- 置信度：band {conf.get('band_level', '—')} · "
            f"reliability {_fmt_num(conf.get('reliability'))}"
        )
    if cov:
        lines.append(
            f"- 数据覆盖：观测天数 {cov.get('observed_days', '—')}/"
            f"{cov.get('total_days', '—')} · "
            f"观测占比 {_fmt_pct(cov.get('observed_ratio'))}"
        )
    flags = fc.get("risk_flags") or []
    if flags:
        lines.append(f"- 风险标记：{', '.join(flags)}")
    if kg:
        lines.append(
            f"- 图谱链接：✅ 节点 {kg.get('node_count', '—')} · 边 {kg.get('edge_count', '—')}"
        )
    ev = fc.get("evidence_ids") or []
    if ev:
        lines.append(f"- 证据链：{_fmt_evidence(ev)}")
    lines.append("")
    return "\n".join(lines)


def _render_causal(causal: dict[str, Any] | None) -> str:
    if not causal:
        return "_未运行因果分析，跳过本节。_\n"
    status = causal.get("status", "unknown")
    if status != "ok":
        return f"_因果分析未完成（status = {status}），跳过本节。_\n"
    seed = causal.get("narrative_seed") or {}
    conf = causal.get("confidence", {}) or {}
    cov = causal.get("coverage", {}) or {}
    kg = causal.get("kg_features") or {}
    lines = [
        f"- Run ID：`{causal.get('run_id', '—')}`",
        f"- 指标：{causal.get('metric', '—')}",
        f"- 干预窗：{causal.get('intervention_start', '—')} → {causal.get('intervention_end') or '至今'}",
        f"- ATE：{_fmt_num(causal.get('ate'), 4)} · 相对效应：{_fmt_pct(causal.get('ate_relative'))}",
        f"- p 值：{_fmt_num(causal.get('p_value'), 3)} · CI 95%：[{_fmt_num(causal.get('ci_low'), 4)}, {_fmt_num(causal.get('ci_high'), 4)}]",
        f"- 显著性：{'是' if seed.get('significant') else '否'} · 方向：{seed.get('direction', '—')}",
    ]
    if conf:
        lines.append(
            f"- 置信度：reliability {_fmt_num(conf.get('reliability'))} · "
            f"status {conf.get('status', '—')}"
        )
    if cov:
        lines.append(
            f"- 数据覆盖：干预前 {cov.get('pre_days', '—')} 天 · "
            f"干预后 {cov.get('post_days', '—')} 天 · "
            f"全窗 {cov.get('history_days', '—')} 天"
        )
    if kg:
        lines.append(
            f"- 图谱链接：✅ 节点 {kg.get('node_count', '—')} · 边 {kg.get('edge_count', '—')}"
        )
    ev = causal.get("evidence_ids") or []
    if ev:
        lines.append(f"- 证据链：{_fmt_evidence(ev)}")
    lines.append("")
    return "\n".join(lines)


_PRIORITY_LABEL = {"high": "🔴 高优先级", "medium": "🟡 中优先级", "low": "🟢 观察项"}

_SOURCE_LABEL = {"simulation": "仿真", "forecast": "预测", "causal": "因果"}


def _fmt_source_run_ids(source: dict[str, str] | None) -> str:
    if not source:
        return "—"
    return " · ".join(
        f"{_SOURCE_LABEL.get(k, k)} `{v}`" for k, v in source.items() if v
    )


def _render_recommendations(recs: list[dict[str, Any]]) -> str:
    if not recs:
        return "_暂无可执行建议。_\n"
    lines: list[str] = []
    for idx, rec in enumerate(recs, 1):
        priority = _PRIORITY_LABEL.get(rec.get("priority", "low"), rec.get("priority", "—"))
        lines.append(f"### {idx}. {rec.get('title', '—')}")
        lines.append("")
        lines.append(f"- 优先级：{priority}")
        tags = rec.get("tags") or []
        if tags:
            lines.append("- 标签：" + ", ".join(f"`{t}`" for t in tags))
        sources = rec.get("source_run_ids") or {}
        if sources:
            lines.append("- 来源 Run：" + _fmt_source_run_ids(sources))
        trace = rec.get("metric_trace") or {}
        if trace:
            lines.append("- 指标依据：" + _fmt_kv(trace))
        evidence = rec.get("evidence") or []
        if evidence:
            lines.append("- 证据链：" + _fmt_evidence(evidence))
        lines.append("")
        lines.append(rec.get("rationale", ""))
        lines.append("")
    return "\n".join(lines)


def _render_evidence_summary(snapshot: dict[str, Any]) -> str:
    """Top-level evidence + KG + confidence rollup section.

    The dashboard surfaces these aggregate fields on the snapshot root; the
    report mirrors them so a print/PDF copy keeps the full audit trail.
    """
    ev_ids = snapshot.get("evidence_ids") or []
    kg = snapshot.get("kg_features") or {}
    conf = snapshot.get("confidence") or {}
    sources = snapshot.get("source_run_ids") or {}

    lines: list[str] = []
    lines.append(f"- 证据数量：{len(ev_ids)}")
    if ev_ids:
        lines.append(f"- 证据 ID：{_fmt_evidence(ev_ids)}")
    if sources:
        lines.append(f"- 来源 Run：{_fmt_source_run_ids(sources)}")
    if kg:
        lines.append(
            "- 图谱特征："
            + _fmt_kv({k: kg.get(k) for k in (
                "node_count", "edge_count", "kol_count",
                "topic_count", "product_count", "brand_count",
            ) if k in kg})
        )
    elif snapshot.get("kg_linked"):
        lines.append("- 图谱链接：✅（无聚合特征）")
    else:
        lines.append("- 图谱链接：⛔️ 未链接")
    if conf:
        if "reliability" in conf:
            r = conf.get("reliability")
            tier_label, _ = _reliability_tier(r if isinstance(r, (int, float)) else None)
            lines.append(
                f"- 置信度（最弱链）：{_fmt_num(r)} · 等级 {tier_label}"
            )
        if "forecast" in conf:
            fc_conf = conf["forecast"]
            lines.append(
                f"  - 预测：reliability {_fmt_num(fc_conf.get('reliability'))} · "
                f"MAPE {_fmt_pct(fc_conf.get('mape'))}"
            )
        if "causal" in conf:
            ca_conf = conf["causal"]
            lines.append(
                f"  - 因果：reliability {_fmt_num(ca_conf.get('reliability'))} · "
                f"status {ca_conf.get('status', '—')}"
            )
    if not lines:
        return "_暂无证据链信息。_\n"
    lines.append("")
    return "\n".join(lines)


def _render_markdown(
    *, project_name: str, project_id: str, snapshot: dict[str, Any]
) -> str:
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    coverage = snapshot.get("coverage") or {}
    risk = snapshot.get("risk") or {}
    sim = snapshot.get("simulation")
    forecast = snapshot.get("forecast")
    causal = snapshot.get("causal")
    recs = snapshot.get("recommendations") or []
    model = snapshot.get("model", "decision-rules-v1")

    parts: list[str] = []
    parts.append(f"# 综合决策报告 · {project_name}\n")
    parts.append(
        f"> 项目 ID：`{project_id}` · 生成于 {now} · 模型：`{model}`\n"
    )
    parts.append("---\n")

    parts.append("## 一、数据来源覆盖\n")
    parts.append(_render_coverage(coverage))

    parts.append("## 二、风险评估\n")
    parts.append(_render_risk(risk))

    parts.append("## 三、舆情仿真摘要\n")
    parts.append(_render_simulation(sim))

    parts.append("## 四、预测拟合摘要\n")
    parts.append(_render_forecast(forecast))

    parts.append("## 五、因果分析摘要\n")
    parts.append(_render_causal(causal))

    parts.append("## 六、决策建议\n")
    parts.append(_render_recommendations(recs))

    parts.append("## 七、证据链与置信度汇总\n")
    parts.append(_render_evidence_summary(snapshot))

    parts.append("---\n")
    parts.append(
        "_本报告由 EchoLens 决策引擎自动生成。所有建议均附触发依据，"
        "可通过对应仿真 / 预测 / 因果运行 ID 追溯。_\n"
    )
    return "\n".join(parts)


# ---------- public API --------------------------------------------------------


def generate_report(project_id: str) -> ReportRecord:
    """Generate a markdown report from the latest decision snapshot.

    Raises
    ------
    KeyError
        If the project does not exist.
    """
    project = get_store().get(project_id)
    if project is None:
        raise KeyError(project_id)

    snapshot = build_snapshot(project_id)
    markdown = _render_markdown(
        project_name=project.name,
        project_id=project_id,
        snapshot=snapshot,
    )
    title = f"{project.name} · 决策报告"
    record = ReportRecord(
        id=uuid4().hex,
        project_id=project_id,
        title=title,
        format="markdown",
        markdown=markdown,
        snapshot=snapshot,
    )
    _get_registry().add(record)
    return record


def get_report(report_id: str) -> ReportRecord | None:
    return _get_registry().get(report_id)


def list_reports(project_id: str) -> list[ReportRecord]:
    return _get_registry().list_for_project(project_id)


def reset_for_tests() -> None:
    _get_registry().clear()


__all__ = [
    "ReportRecord",
    "generate_report",
    "get_report",
    "list_reports",
    "reset_for_tests",
]
