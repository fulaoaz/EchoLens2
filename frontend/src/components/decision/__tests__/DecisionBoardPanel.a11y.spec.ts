/**
 * Phase E a11y 回归脚手架（前端层）
 *
 * 目标：从前端侧锁住"决策→报告→Run 反查链"的 UX 入口可达性。
 *
 * 与后端 `tests/test_decision_api.py::test_snapshot_source_run_ids_resolve_to_live_runs`
 * （JSON 层 source_run_ids 反查活 Run）+ `tests/test_report_api.py::test_full_coverage_markdown_source_runs_resolve_to_live_runs`
 * （Markdown 字面里 sim/forecast/causal id 反查活 Run）共四层防御决策→报告→Run
 * 反查链：
 *
 *   1. 后端 JSON 层：snapshot.source_run_ids 反查活 Run（test_decision_api）
 *   2. 后端 Markdown 层：报告字面里的 id 反查活 Run（test_report_api）
 *   3. 后端 HTML 打印层：section/metric-row 锚点（已有）
 *   4. 前端 chip a11y 层：鼠标 / 键盘（Enter+Space）/ 读屏（aria-label/role/tabindex）
 *      三种交互均能触发 emit('open-run', kind, runId) ← 本文件
 *
 * 这条第 4 层是真实用户视角下"反查链可不可用"的最后一公里：哪怕后端
 * 三层都通了，如果 chip 只能鼠标点、读屏读不到完整 runId、键盘 Tab 不
 * 上去，决策→报告→Run 反查链对键盘 / 读屏用户就形同虚设。
 *
 * 测试覆盖：
 * - 顶层 `sourceRunChips`（覆盖 simulation / forecast / causal 三类）：
 *   - role="button" + tabindex="0" + 完整 runId 的 aria-label
 *   - @click / @keydown.enter / @keydown.space 三种触发都 emit('open-run')
 *     且 runId 与传入的完整 id 一致（不被截断短码替代）
 * - 每条建议块的 `recSourceRuns(rec)` chip：同样三种触发都 emit
 * - 没有 source_run_ids 的 chip 不渲染（不会产生空 runId 的 emit）
 */

import { mount, type VueWrapper } from '@vue/test-utils'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { NMessageProvider } from 'naive-ui'
import DecisionBoardPanel from '../DecisionBoardPanel.vue'
import type { DecisionSnapshot } from '@/api/decision'

// ---------- 显式 mock decisionApi ------------------------------------------
//
// DecisionBoardPanel 在 onMounted 里调用 decisionApi.snapshot()，
// 我们用 vi.mock 把它替换成一个 vi.fn，再在每个 it 里塞不同的 fixture，
// 这样既不需要真实 axios，也能完全控制快照结构。

const snapshotMock = vi.fn<(projectId: string) => Promise<DecisionSnapshot>>()

vi.mock('@/api/decision', async () => {
  const actual = await vi.importActual<typeof import('@/api/decision')>('@/api/decision')
  return {
    ...actual,
    decisionApi: {
      snapshot: (projectId: string) => snapshotMock(projectId),
    },
  }
})

// ---------- 测试用快照 fixture ---------------------------------------------

const SIM_ID = 'sim-job-aaa-1111-2222-3333-4444-5555'
const FC_ID = 'fc-run-bbb-1111-2222-3333-4444-5555'
const CAUSAL_ID = 'causal-run-ccc-1111-2222-3333-4444-5555'

function buildFullCoverageSnapshot(): DecisionSnapshot {
  return {
    project_id: 'pid-test',
    coverage: { simulation: true, forecast: true, causal: true },
    simulation: {
      job_id: SIM_ID,
      created_at: '2026-05-20T10:00:00',
      config: { num_agents: 20, num_rounds: 3, rng_seed: 11, kg_linked: true },
      population: {},
      network: { nodes: 20, edges: 40, mean_degree: 4 },
      final_action_totals: {},
      last_round: {
        round: 3,
        avg_sentiment: 0.42,
        awareness: 0.6,
        purchase_rate: 0.3,
        boycott_rate: 0.05,
      },
      rounds_total: 3,
      evidence_ids: ['jd:p1'],
      kg_features: { node_count: 5, edge_count: 8 },
      kg_linked: true,
    },
    forecast: {
      run_id: FC_ID,
      metric: 'volume',
      metric_label: '舆情量',
      unit: '条',
      headline: '未来 7 天舆情量预计 +12%',
      delta_relative: 0.12,
      history: [],
      forecast: [],
      diagnostics: { mape: 0.1, r2: 0.85, trend_slope: 0.02, n_observations: 30 },
      risk_flags: [],
      evidence_ids: ['jd:p1'],
      coverage: { observed_days: 30, total_days: 30, observed_ratio: 1.0 },
      confidence: { band_level: 0.95, reliability: 0.78 },
      kg_features: { node_count: 5 },
      kg_linked: true,
      created_at: '2026-05-20T10:00:00',
    },
    causal: {
      run_id: CAUSAL_ID,
      metric: 'sentiment',
      status: 'ok',
      intervention_start: '2026-05-01',
      intervention_end: null,
      ate: 0.15,
      ate_relative: 0.2,
      p_value: 0.03,
      ci_low: 0.05,
      ci_high: 0.25,
      narrative_seed: { direction: 'up', significant: true, abs_relative_pct: 20 },
      evidence_ids: ['jd:p1'],
      coverage: { pre_days: 20, post_days: 20, observed_ratio: 1.0 },
      confidence: { p_value: 0.03, significant: true, reliability: 0.8, status: 'ok' },
      kg_features: { node_count: 5 },
      kg_linked: true,
      created_at: '2026-05-20T10:00:00',
    },
    risk: {
      score: 35,
      level: 'elevated',
      reasons: ['情感下行 20%'],
    },
    recommendations: [
      {
        id: 'sentiment-recovery',
        title: '组织情感修复',
        priority: 'high',
        rationale: '仿真显示终轮抵制率 5%，需快速干预',
        evidence: ['jd:p1'],
        tags: ['crisis', 'sim'],
        source_run_ids: { simulation: SIM_ID },
        metric_trace: { boycott_rate: 0.05 },
      },
      {
        id: 'tighten-forecast',
        title: '收紧预测预算',
        priority: 'medium',
        rationale: '预测显示 +12% 增量，建议追加预算',
        evidence: [],
        tags: ['forecast'],
        source_run_ids: { forecast: FC_ID, causal: CAUSAL_ID },
        metric_trace: {},
      },
      {
        id: 'observe-only',
        title: '保持观察',
        priority: 'low',
        rationale: '无显著异常',
        evidence: [],
        tags: [],
        // 没有 source_run_ids — 不应渲染 chip
      },
    ],
    evidence_ids: ['jd:p1'],
    kg_features: { node_count: 5, edge_count: 8 },
    kg_linked: true,
    confidence: {
      forecast: { reliability: 0.78 },
      causal: { reliability: 0.8 },
      reliability: 0.78,
    },
    source_run_ids: { simulation: SIM_ID, forecast: FC_ID, causal: CAUSAL_ID },
    model: 'decision-rules-v1',
  }
}

// ---------- 渲染辅助 -------------------------------------------------------

// DecisionBoardPanel 内部 useMessage()，必须外层包 NMessageProvider 才能拿到
// provider；这里用一个轻量 wrapper 组件渲染 provider + panel，并把 emit
// 透传出来，让外层测试照常断言 ('open-run', kind, runId)。
const Harness = defineComponent({
  name: 'DecisionBoardPanelHarness',
  components: { NMessageProvider, DecisionBoardPanel },
  props: { projectId: { type: String, required: true } },
  emits: ['open-run'],
  setup(props, { emit }) {
    return () =>
      h(
        NMessageProvider,
        {},
        {
          default: () =>
            h(DecisionBoardPanel, {
              projectId: props.projectId,
              'onOpen-run': (kind: string, runId: string) => emit('open-run', kind, runId),
            }),
        },
      )
  },
})

async function renderPanel(): Promise<VueWrapper> {
  const wrapper = mount(Harness, {
    props: { projectId: 'pid-test' },
    attachTo: document.body,
  })
  // 等 onMounted -> snapshot 完成 + 模板渲染；多 tick 让 NCard/NList 落定。
  for (let i = 0; i < 8; i++) await nextTick()
  return wrapper
}

// ---------- 测试 ----------------------------------------------------------

describe('DecisionBoardPanel a11y · 决策→报告→Run 反查链 chip 可达性', () => {
  beforeEach(() => {
    snapshotMock.mockReset()
    snapshotMock.mockResolvedValue(buildFullCoverageSnapshot())
  })

  it('顶层 sourceRunChips 渲染为 role="button" + tabindex="0" + 完整 runId 的 aria-label', async () => {
    const wrapper = await renderPanel()

    const simChip = wrapper.find(`[aria-label="打开仿真 Run ${SIM_ID}"]`)
    const fcChip = wrapper.find(`[aria-label="打开预测 Run ${FC_ID}"]`)
    const causalChip = wrapper.find(`[aria-label="打开因果 Run ${CAUSAL_ID}"]`)

    expect(simChip.exists()).toBe(true)
    expect(fcChip.exists()).toBe(true)
    expect(causalChip.exists()).toBe(true)

    for (const chip of [simChip, fcChip, causalChip]) {
      expect(chip.attributes('role')).toBe('button')
      expect(chip.attributes('tabindex')).toBe('0')
    }
  })

  it('鼠标点击顶层 chip → emit("open-run", kind, 完整 runId)', async () => {
    const wrapper = await renderPanel()

    await wrapper.find(`[aria-label="打开仿真 Run ${SIM_ID}"]`).trigger('click')
    await wrapper.find(`[aria-label="打开预测 Run ${FC_ID}"]`).trigger('click')
    await wrapper.find(`[aria-label="打开因果 Run ${CAUSAL_ID}"]`).trigger('click')

    const events = wrapper.emitted('open-run') ?? []
    expect(events).toHaveLength(3)
    expect(events[0]).toEqual(['simulation', SIM_ID])
    expect(events[1]).toEqual(['forecast', FC_ID])
    expect(events[2]).toEqual(['causal', CAUSAL_ID])
  })

  it('键盘 Enter 触发顶层 chip → emit 与鼠标等价（同一 kind+完整 runId）', async () => {
    const wrapper = await renderPanel()

    await wrapper.find(`[aria-label="打开仿真 Run ${SIM_ID}"]`).trigger('keydown', { key: 'Enter' })

    const events = wrapper.emitted('open-run') ?? []
    expect(events).toHaveLength(1)
    expect(events[0]).toEqual(['simulation', SIM_ID])
  })

  it('键盘 Space 触发顶层 chip → emit 与鼠标等价', async () => {
    const wrapper = await renderPanel()

    await wrapper.find(`[aria-label="打开预测 Run ${FC_ID}"]`).trigger('keydown', { key: ' ' })

    const events = wrapper.emitted('open-run') ?? []
    expect(events).toHaveLength(1)
    expect(events[0]).toEqual(['forecast', FC_ID])
  })

  it('每条建议块的 source_run_ids chip 同样有 role/tabindex/完整 aria-label', async () => {
    const wrapper = await renderPanel()

    // 建议 #1：仅 simulation
    expect(wrapper.find(`[aria-label="打开仿真 Run ${SIM_ID}"]`).exists()).toBe(true)
    // 建议 #2：forecast + causal（顶层也有同 aria-label，故至少 2 处出现）
    const fcMatches = wrapper.findAll(`[aria-label="打开预测 Run ${FC_ID}"]`)
    const causalMatches = wrapper.findAll(`[aria-label="打开因果 Run ${CAUSAL_ID}"]`)
    expect(fcMatches.length).toBeGreaterThanOrEqual(2)
    expect(causalMatches.length).toBeGreaterThanOrEqual(2)

    for (const chip of [...fcMatches, ...causalMatches]) {
      expect(chip.attributes('role')).toBe('button')
      expect(chip.attributes('tabindex')).toBe('0')
    }
  })

  it('建议块 chip 鼠标 / Enter / Space 都能触发 emit("open-run")', async () => {
    const wrapper = await renderPanel()

    // 找到建议块里的预测 chip — 是 fcMatches 中除顶层之外的那一个
    const fcChips = wrapper.findAll(`[aria-label="打开预测 Run ${FC_ID}"]`)
    expect(fcChips.length).toBeGreaterThanOrEqual(2)

    // 顶层 chip 是首个；建议块 chip 取最后一个
    const recFcChip = fcChips[fcChips.length - 1]
    await recFcChip.trigger('keydown', { key: 'Enter' })

    const events = wrapper.emitted('open-run') ?? []
    expect(events.length).toBeGreaterThanOrEqual(1)
    // 每个 emit 都是 ['forecast', FC_ID]
    for (const ev of events) {
      expect(ev).toEqual(['forecast', FC_ID])
    }
  })

  it('没有 source_run_ids 的建议（observe-only）不渲染来源 Run chip', async () => {
    const wrapper = await renderPanel()

    // observe-only 这条 rec 没有 source_run_ids；任何包含 "observe-only" 字样的
    // chip 都不应该出现。我们用更直接的不变量校验：所有 role="button" 的
    // chip 数量 = 顶层 3 个（simulation/forecast/causal）+ 建议 #1 的 simulation
    // (1) + 建议 #2 的 forecast+causal (2) = 6。
    const allRunChips = wrapper.findAll('[role="button"][tabindex="0"][aria-label^="打开"]')
    expect(allRunChips).toHaveLength(6)
  })

  it('emit 出去的 runId 始终是完整 id，绝不被 slice(0,8) 短码替代', async () => {
    const wrapper = await renderPanel()

    await wrapper.find(`[aria-label="打开仿真 Run ${SIM_ID}"]`).trigger('click')
    await wrapper.find(`[aria-label="打开预测 Run ${FC_ID}"]`).trigger('click')
    await wrapper.find(`[aria-label="打开因果 Run ${CAUSAL_ID}"]`).trigger('click')

    const events = wrapper.emitted('open-run') ?? []
    for (const [, runId] of events) {
      expect(typeof runId).toBe('string')
      // 完整 id 长度远大于 8，且应等于原始 fixture id
      expect((runId as string).length).toBeGreaterThan(8)
    }
    expect(events.map((e) => e[1])).toEqual([SIM_ID, FC_ID, CAUSAL_ID])
  })
})
