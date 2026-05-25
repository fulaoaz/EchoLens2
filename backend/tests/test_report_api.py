"""End-to-end tests for the /api/report blueprint (M5.2).

Covers:
- ping returns implemented=True
- list / generate / get / download behavior
- 404 paths (unknown project / unknown report)
- empty-project markdown contains the "missing-sim" recommendation
- full-coverage markdown contains risk-score header and at least one
  evidence-tagged recommendation block
- list ordering: newest first
- download endpoint returns text/markdown with attachment header
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

import pytest

from app.services import prediction_jobs, report_builder, sim_jobs
from app.services.crawler_store import get_crawler_store
from app.services.prediction_jobs import CausalParams, ForecastParams
from app.services.project_store import get_store


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch) -> None:
    get_store().clear()
    get_crawler_store().clear()
    prediction_jobs.reset_for_tests()
    sim_jobs.reset_for_tests()
    report_builder.reset_for_tests()

    real_submit = sim_jobs.submit_simulation

    def _sync_submit(*args: Any, **kwargs: Any) -> Any:
        kwargs["sync"] = True
        return real_submit(*args, **kwargs)

    monkeypatch.setattr(sim_jobs, "submit_simulation", _sync_submit)


# ---------- helpers -----------------------------------------------------------


def _create_project(client: Any, name: str = "report-demo") -> str:
    return client.post(
        "/api/projects", json={"name": name, "keywords": ["k"]}
    ).get_json()["data"]["id"]


def _seed_project_with_history(client: Any, *, name: str = "rep", days: int = 30) -> str:
    pid = _create_project(client, name)
    today = date(2026, 5, 20)
    posts = []
    for i in range(days):
        d = (today - timedelta(days=days - 1 - i)).isoformat()
        for j in range(1 + i // 3):
            posts.append(
                {
                    "platform": "weibo",
                    "id": f"w-{i}-{j}",
                    "author_hash": "kol_demo_aaaaaa",
                    "content": "demo",
                    "sentiment": "positive" if i >= days // 2 else "negative",
                    "posted_at": f"{d}T10:00:00",
                }
            )
    products = [
        {
            "platform": "jd",
            "id": "jd:p1",
            "title": "Demo",
            "brand": "Demo",
            "price_current": 199.0,
        }
    ]
    client.post(
        f"/api/projects/{pid}/seed_data",
        json={"products": products, "reviews": [], "posts": posts},
    )
    return pid


def _seed_report(pid: str) -> dict[str, Any]:
    return {
        "project_id": pid,
        "products": [
            {
                "platform": "jd",
                "id": "jd:p1",
                "title": "Demo",
                "brand": "Demo",
                "price_current": 199.0,
            }
        ],
        "reviews": [],
        "posts": [],
    }


# ---------- tests -------------------------------------------------------------


def test_ping_reports_implemented(client: Any) -> None:
    resp = client.get("/api/report/ping")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["data"]["implemented"] is True


def test_generate_unknown_project_returns_404(client: Any) -> None:
    resp = client.post("/api/report/generate", json={"projectId": "missing"})
    assert resp.status_code == 404
    assert resp.get_json()["success"] is False


def test_generate_missing_payload_returns_400(client: Any) -> None:
    resp = client.post("/api/report/generate", json={})
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False


def test_generate_empty_project_uses_default_recommendation(client: Any) -> None:
    pid = _create_project(client, name="empty-rep")

    resp = client.post("/api/report/generate", json={"projectId": pid})
    assert resp.status_code == 201, resp.get_data(as_text=True)
    summary = resp.get_json()["data"]
    assert summary["projectId"] == pid
    assert summary["format"] == "markdown"
    assert summary["url"].startswith("/api/report/")
    assert summary["url"].endswith("/download")

    full = client.get(f"/api/report/{summary['id']}").get_json()["data"]
    md = full["markdown"]
    # 报告标题 + 项目名
    assert "# 综合决策报告" in md
    assert "empty-rep" in md
    # 风险评估章节存在 + 默认低风险
    assert "综合风险评分：0 / 100" in md
    # 数据覆盖三项均为未跑
    assert "舆情仿真：⛔️ 未跑" in md
    assert "预测拟合：⛔️ 未跑" in md
    assert "因果分析：⛔️ 未跑" in md
    # 默认建议命中 missing-sim 模板（标题里"先跑一次舆情仿真"）
    assert "先跑一次舆情仿真" in md


def test_generate_full_coverage_markdown_contains_evidence(client: Any) -> None:
    pid = _seed_project_with_history(client, days=40)
    sim_jobs.submit_simulation(
        pid,
        _seed_report(pid),
        num_agents=20,
        num_rounds=3,
        mean_degree=4,
        rng_seed=11,
        sync=True,
    )
    prediction_jobs.run_forecast(
        ForecastParams(project_id=pid, metric="volume", horizon_days=7)
    )
    cut = (date(2026, 5, 20) - timedelta(days=20)).isoformat()
    prediction_jobs.run_causal(
        CausalParams(project_id=pid, metric="sentiment", intervention_start=cut)
    )

    resp = client.post("/api/report/generate", json={"projectId": pid})
    assert resp.status_code == 201, resp.get_data(as_text=True)
    summary = resp.get_json()["data"]

    full = client.get(f"/api/report/{summary['id']}").get_json()["data"]
    md = full["markdown"]
    snap = full["snapshot"]

    # snapshot 与 decision_engine 同步
    assert snap["coverage"] == {"simulation": True, "forecast": True, "causal": True}
    # 风险评分被正确渲染（任意 0-100）
    assert "综合风险评分：" in md
    # 仿真 + 预测 + 因果 三章节都有真实内容（没有"未运行"句式）
    assert "## 三、舆情仿真摘要" in md
    assert "## 四、预测拟合摘要" in md
    assert "## 五、因果分析摘要" in md
    assert "_未运行仿真" not in md
    assert "_未运行预测" not in md
    assert "_未运行因果分析" not in md
    # 建议章节有编号标题
    assert "## 六、决策建议" in md
    assert "### 1." in md
    # evidence 字段被渲染成 `key=value` 标记
    assert "证据链：" in md or "标签：" in md  # 至少一条建议带证据/标签


def test_generate_full_coverage_markdown_renders_phase_d_fields(client: Any) -> None:
    """Phase D contract: evidence_ids / source_run_ids / kg_features /
    confidence must surface in the rendered markdown so the export keeps the
    full audit trail (not only the JSON snapshot)."""
    pid = _seed_project_with_history(client, days=40)
    # Wire the project KG into the sim run so evidence_ids actually flow.
    from app.kg.search import get_subgraph

    sim_jobs.submit_simulation(
        pid,
        _seed_report(pid),
        num_agents=20,
        num_rounds=3,
        mean_degree=4,
        rng_seed=11,
        kg_subgraph=get_subgraph(pid) or None,
        sync=True,
    )
    prediction_jobs.run_forecast(
        ForecastParams(project_id=pid, metric="volume", horizon_days=7)
    )
    cut = (date(2026, 5, 20) - timedelta(days=20)).isoformat()
    prediction_jobs.run_causal(
        CausalParams(project_id=pid, metric="sentiment", intervention_start=cut)
    )

    rid = client.post("/api/report/generate", json={"projectId": pid}).get_json()[
        "data"
    ]["id"]
    full = client.get(f"/api/report/{rid}").get_json()["data"]
    md = full["markdown"]
    snap = full["snapshot"]

    # New top-level evidence summary section is rendered.
    assert "## 七、证据链与置信度汇总" in md
    assert f"证据数量：{len(snap['evidence_ids'])}" in md
    assert "jd:p1" in md  # crawler product evidence id should appear
    # source_run_ids surfaced with the human-readable source labels.
    assert "仿真 `" in md
    assert "预测 `" in md
    assert "因果 `" in md
    # KG features rolled up.
    assert "图谱特征：" in md
    assert "node_count" in md
    # Confidence rollup with the weakest-link reliability.
    assert "置信度（最弱链）：" in md
    # Phase E: weakest-link reliability now carries a Chinese tier label
    # (强 / 一般 / 弱) so a printed/PDF copy of the report can be read at a
    # glance — same threshold rule as the decision board chip's
    # ``reliabilityColor`` (>=0.7 strong / >=0.4 fair / else weak).
    assert re.search(r"置信度（最弱链）：[^\n]+·\s*等级\s*(强|一般|弱)", md), md
    # Forecast block renders coverage + confidence rows.
    assert "数据覆盖：观测天数" in md
    assert "置信度：band 0.95" in md
    # Causal block renders pre/post coverage.
    assert "干预前" in md and "干预后" in md
    # At least one recommendation must cite a source run + evidence ids.
    assert "来源 Run：" in md
    assert "证据链：" in md


def test_list_returns_reports_newest_first(client: Any) -> None:
    pid = _create_project(client, name="multi-rep")
    ids: list[str] = []
    for _ in range(3):
        r = client.post("/api/report/generate", json={"projectId": pid})
        ids.append(r.get_json()["data"]["id"])

    resp = client.get(f"/api/report?projectId={pid}")
    assert resp.status_code == 200
    summaries = resp.get_json()["data"]
    assert [s["id"] for s in summaries] == list(reversed(ids))


def test_list_unknown_project_returns_404(client: Any) -> None:
    resp = client.get("/api/report?projectId=missing")
    assert resp.status_code == 404


def test_list_missing_query_returns_400(client: Any) -> None:
    resp = client.get("/api/report")
    assert resp.status_code == 400


def test_get_unknown_report_returns_404(client: Any) -> None:
    resp = client.get("/api/report/nope")
    assert resp.status_code == 404


def test_download_returns_markdown_attachment(client: Any) -> None:
    pid = _create_project(client, name="dl-rep")
    rid = client.post("/api/report/generate", json={"projectId": pid}).get_json()[
        "data"
    ]["id"]

    resp = client.get(f"/api/report/{rid}/download")
    assert resp.status_code == 200
    ctype = resp.headers.get("Content-Type", "")
    assert ctype.startswith("text/markdown")
    cd = resp.headers.get("Content-Disposition", "")
    assert "attachment" in cd and ".md" in cd
    body = resp.get_data(as_text=True)
    assert "# 综合决策报告" in body


def test_download_unknown_report_returns_404(client: Any) -> None:
    resp = client.get("/api/report/nope/download")
    assert resp.status_code == 404


# ---------- M7.1 HTML download ------------------------------------------------


def test_download_html_returns_self_contained_attachment(client: Any) -> None:
    pid = _create_project(client, name="dl-html-rep")
    rid = client.post("/api/report/generate", json={"projectId": pid}).get_json()[
        "data"
    ]["id"]

    resp = client.get(f"/api/report/{rid}/download.html")
    assert resp.status_code == 200

    ctype = resp.headers.get("Content-Type", "")
    assert ctype.startswith("text/html")
    cd = resp.headers.get("Content-Disposition", "")
    assert "attachment" in cd and ".html" in cd

    body = resp.get_data(as_text=True)
    # Document shell
    assert body.startswith("<!DOCTYPE html>")
    assert "<title>" in body and "决策报告" in body
    # Self-contained: inline <style>, no external stylesheet/script links
    assert "<style>" in body
    assert "<link " not in body
    assert "<script" not in body
    # Markdown headings rendered as HTML
    assert "<h1>" in body and "综合决策报告" in body
    assert "<h2>" in body
    # Print-friendly CSS is present
    assert "@page" in body
    assert "@media print" in body


def test_download_html_unknown_report_returns_404(client: Any) -> None:
    resp = client.get("/api/report/nope/download.html")
    assert resp.status_code == 404


def test_download_html_wraps_phase_d_sections_with_class(client: Any) -> None:
    """The printable HTML must structure Phase D chapters into classed
    ``<section>`` blocks and tag well-known metric rows so the export keeps
    a stable, styleable audit layout (and so a future PDF / print pass can
    rely on these hooks).
    """
    pid = _seed_project_with_history(client, days=40)
    from app.kg.search import get_subgraph

    sim_jobs.submit_simulation(
        pid,
        _seed_report(pid),
        num_agents=20,
        num_rounds=3,
        mean_degree=4,
        rng_seed=11,
        kg_subgraph=get_subgraph(pid) or None,
        sync=True,
    )
    prediction_jobs.run_forecast(
        ForecastParams(project_id=pid, metric="volume", horizon_days=7)
    )
    cut = (date(2026, 5, 20) - timedelta(days=20)).isoformat()
    prediction_jobs.run_causal(
        CausalParams(project_id=pid, metric="sentiment", intervention_start=cut)
    )

    rid = client.post("/api/report/generate", json={"projectId": pid}).get_json()[
        "data"
    ]["id"]

    resp = client.get(f"/api/report/{rid}/download.html")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)

    # Each Phase D chapter is wrapped in a classed <section>.
    assert 'class="report-section section-coverage"' in body
    assert 'class="report-section section-risk"' in body
    assert 'class="report-section section-simulation"' in body
    assert 'class="report-section section-forecast"' in body
    assert 'class="report-section section-causal"' in body
    assert 'class="report-section section-recommendation"' in body
    assert 'class="report-section section-evidence"' in body
    # Well-known metric rows are tagged so print/PDF styling can target them.
    assert 'class="metric-row metric-evidence-count"' in body
    # The reliability row now always carries a tier modifier class so its
    # base class string ends with a space (not a closing quote). Keep a
    # substring check for the base class plus the regex below for the
    # full tier-aware contract.
    assert 'class="metric-row metric-reliability ' in body
    assert 'class="metric-row metric-source-run"' in body
    # Phase E: the reliability row also carries a tier modifier class so the
    # print stylesheet colour-codes it the same way the decision board chip
    # does (strong/fair/weak/unknown).
    assert re.search(
        r'class="metric-row metric-reliability metric-reliability-(strong|fair|weak|unknown)"',
        body,
    ), body
    # Self-contained guarantees still hold.
    assert "<link " not in body
    assert "<script" not in body


def test_download_html_escapes_inline_html_in_markdown(client: Any) -> None:
    """Defense-in-depth: even though backend markdown is deterministic,
    ensure the renderer escapes raw ``<`` / ``&`` so a future field with
    user-supplied content can't smuggle a ``<script>`` tag."""
    from app.services.report_html import markdown_to_html_fragment

    out = markdown_to_html_fragment("- <script>alert(1)</script>\n- a & b")
    assert "<script>alert(1)</script>" not in out
    assert "&lt;script&gt;" in out
    assert "a &amp; b" in out


# ---------- Phase E audit-trail round-trip -----------------------------------


_SOURCE_RUN_RE = re.compile(r"(仿真|预测|因果)\s+`([^`]+)`")


def test_full_coverage_markdown_source_runs_resolve_to_live_runs(client: Any) -> None:
    """End-to-end audit-trail invariant: every ``Run ID`` cited inside the
    rendered markdown — both in the top-level evidence summary and inside
    each recommendation's ``来源 Run：`` row — must resolve back to a live
    Run in the sim/prediction registries belonging to the same project.

    The ``test_snapshot_source_run_ids_resolve_to_live_runs`` lock in
    ``test_decision_api.py`` already protects the JSON snapshot. This test
    extends the same invariant to the printed markdown so a regression in
    ``report_builder._render_*`` (e.g. swapping ``rec.source_run_ids`` with
    a stale field, or dropping the source row from the render path) fails
    here too — the dashboard's "open Run" chip and the printed report
    audit row are both surfaces for the same audit chain.
    """
    pid = _seed_project_with_history(client, days=40)
    from app.kg.search import get_subgraph

    sim_job = sim_jobs.submit_simulation(
        pid,
        _seed_report(pid),
        num_agents=20,
        num_rounds=3,
        mean_degree=4,
        rng_seed=11,
        kg_subgraph=get_subgraph(pid) or None,
        sync=True,
    )
    fc_run = prediction_jobs.run_forecast(
        ForecastParams(project_id=pid, metric="volume", horizon_days=7)
    )
    cut = (date(2026, 5, 20) - timedelta(days=20)).isoformat()
    causal_run = prediction_jobs.run_causal(
        CausalParams(project_id=pid, metric="sentiment", intervention_start=cut)
    )

    rid = client.post("/api/report/generate", json={"projectId": pid}).get_json()[
        "data"
    ]["id"]
    full = client.get(f"/api/report/{rid}").get_json()["data"]
    md = full["markdown"]

    def _resolve(kind_label: str, run_id: str) -> None:
        if kind_label == "仿真":
            job = sim_jobs.get_job(run_id)
            assert job is not None, f"sim run {run_id} missing from registry"
            assert job.project_id == pid, (
                f"sim run {run_id} belongs to {job.project_id}, expected {pid}"
            )
        elif kind_label in ("预测", "因果"):
            run = prediction_jobs.get_run(run_id)
            expected_kind = "forecast" if kind_label == "预测" else "causal"
            assert run is not None, (
                f"{kind_label} run {run_id} missing from prediction registry"
            )
            assert run.project_id == pid, (
                f"{kind_label} run {run_id} belongs to {run.project_id}, expected {pid}"
            )
            assert run.kind == expected_kind, (
                f"{kind_label} run {run_id} stored as kind={run.kind}, "
                f"expected {expected_kind}"
            )
        else:
            raise AssertionError(f"unexpected source label {kind_label!r}")

    matches = _SOURCE_RUN_RE.findall(md)
    # The top-level "证据链与置信度汇总" section must surface all three labels.
    labels = {label for label, _ in matches}
    assert labels >= {"仿真", "预测", "因果"}, (
        f"expected sim+forecast+causal source labels in markdown, found {labels}"
    )

    # Every cited id (root-level summary AND per-recommendation rows) must
    # round-trip back to its live registry entry.
    seen_root_ids = {"仿真": sim_job.id, "预测": fc_run.id, "因果": causal_run.id}
    for label, run_id in matches:
        _resolve(label, run_id)

    # Sanity: at least one of the seeded ids actually shows up — guards
    # against the regex silently matching an empty set.
    cited_ids = {rid for _, rid in matches}
    assert cited_ids & set(seen_root_ids.values()), (
        f"none of the seeded run ids ({list(seen_root_ids.values())}) appear "
        f"in the markdown; cited ids were {cited_ids}"
    )

    # And: at least one recommendation block (### N. ...) must include a
    # ``- 来源 Run：`` row so the audit row isn't only top-level.
    rec_block_re = re.compile(
        r"### \d+\..*?(?=^### \d+\.|\Z)", re.DOTALL | re.MULTILINE
    )
    rec_blocks = rec_block_re.findall(md)
    assert rec_blocks, "expected at least one recommendation block in markdown"
    rec_with_source = [b for b in rec_blocks if "- 来源 Run：" in b]
    assert rec_with_source, (
        "no recommendation cited a source Run in markdown — the rec-level "
        "audit row regressed; check report_builder._render_recommendations"
    )
    for block in rec_with_source:
        for label, run_id in _SOURCE_RUN_RE.findall(block):
            _resolve(label, run_id)
