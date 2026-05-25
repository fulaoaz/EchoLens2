<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  NAlert,
  NButton,
  NCard,
  NCollapse,
  NCollapseItem,
  NDivider,
  NEmpty,
  NForm,
  NFormItem,
  NGrid,
  NGridItem,
  NIcon,
  NInputNumber,
  NList,
  NListItem,
  NProgress,
  NSpace,
  NSpin,
  NStatistic,
  NTag,
  NThing,
  useMessage,
} from 'naive-ui'
import {
  CloseCircleOutline,
  FlashOutline,
  PlayCircleOutline,
  RefreshOutline,
  StatsChartOutline,
  TimerOutline,
} from '@vicons/ionicons5'
import * as echarts from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'

import {
  simulationApi,
  subscribeJobEvents,
  type CampaignEntry,
  type JobEventStream,
  type JobSnapshot,
  type RoundMetrics,
  type RunSimulationInput,
  type SimEvent,
  type SimulationResult,
} from '@/api/simulation'

echarts.use([LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{ projectId: string; defaultRunId?: string | null }>()
const message = useMessage()

// ---------- form state --------------------------------------------------------

const form = reactive<
  Required<Omit<RunSimulationInput, 'target_product_id' | 'campaign_schedule'>> & {
    stimulus: number
    price_pressure: number
  }
>({
  num_agents: 200,
  num_rounds: 12,
  mean_degree: 8,
  rng_seed: 42,
  stimulus: 0.4,
  price_pressure: 0.4,
})

function buildPayload(): RunSimulationInput {
  const campaign: CampaignEntry[] = [
    { round: 0, stimulus: form.stimulus, price_pressure: form.price_pressure },
  ]
  return {
    num_agents: form.num_agents,
    num_rounds: form.num_rounds,
    mean_degree: form.mean_degree,
    rng_seed: form.rng_seed,
    campaign_schedule: campaign,
  }
}

// ---------- run state ---------------------------------------------------------

const job = ref<JobSnapshot | null>(null)
const result = ref<SimulationResult | null>(null)
const rounds = ref<RoundMetrics[]>([])
const submitting = ref(false)
const errorText = ref<string | null>(null)
let stream: JobEventStream | null = null

const isRunning = computed(() => {
  const s = job.value?.status
  return s === 'pending' || s === 'running'
})
const progressPercent = computed(() => {
  const j = job.value
  if (!j || j.total_rounds === 0) return 0
  return Math.round((j.rounds_done / j.total_rounds) * 100)
})

const runHistory = ref<JobSnapshot[]>([])

async function refreshHistory(): Promise<void> {
  try {
    runHistory.value = await simulationApi.listJobs(props.projectId)
  } catch (e) {
    // Empty project / 404 — silently ignore on refresh.
    runHistory.value = []
  }
}

async function focusRunIfRequested(): Promise<void> {
  const target = props.defaultRunId
  if (!target) return
  // Only auto-load completed jobs; running ones get focus via the live stream.
  const snap = runHistory.value.find((j) => j.id === target)
  if (snap && snap.status === 'completed') {
    await loadHistoryRun(snap)
  }
}

function closeStream(): void {
  stream?.close()
  stream = null
}

function onSimEvent(ev: SimEvent): void {
  if (ev.heartbeat) return
  if (ev.type === 'round' && ev.metrics) {
    // Append-or-replace to keep the array idempotent on reconnects.
    const existing = rounds.value.findIndex((r) => r.round === ev.metrics!.round)
    if (existing >= 0) rounds.value[existing] = ev.metrics
    else rounds.value.push(ev.metrics)
    if (job.value) {
      job.value.rounds_done = ev.rounds_done ?? rounds.value.length
      job.value.last_round_metrics = ev.metrics
    }
    setTimeout(renderCharts, 0)
  } else if (ev.type === 'done') {
    finishRun('completed')
  } else if (ev.type === 'failed') {
    errorText.value = ev.error ?? '仿真失败'
    finishRun('failed')
  } else if (ev.type === 'cancelled') {
    finishRun('cancelled')
  } else if (ev.type === 'started' && job.value) {
    job.value.status = 'running'
    job.value.started_at = ev.timestamp ?? new Date().toISOString()
  }
}

async function finishRun(status: 'completed' | 'failed' | 'cancelled'): Promise<void> {
  closeStream()
  if (job.value) {
    job.value.status = status
    job.value.finished_at = new Date().toISOString()
  }
  if (status === 'completed' && job.value) {
    try {
      result.value = await simulationApi.getResult(job.value.id)
      // Trust the canonical rounds list.
      rounds.value = [...result.value.rounds]
      setTimeout(renderCharts, 0)
    } catch (e) {
      errorText.value = e instanceof Error ? e.message : String(e)
    }
  }
  await refreshHistory()
}

async function startRun(): Promise<void> {
  submitting.value = true
  errorText.value = null
  result.value = null
  rounds.value = []
  closeStream()
  try {
    const snap = await simulationApi.runAsync(props.projectId, buildPayload())
    job.value = snap
    stream = subscribeJobEvents(snap.id, onSimEvent, () => {
      // Don't surface SSE close-on-done as an error.
      if (job.value && (job.value.status === 'completed' || job.value.status === 'cancelled')) {
        return
      }
      errorText.value = '事件流连接异常，已断开'
      closeStream()
    })
    message.success(`仿真已提交：${snap.id.slice(0, 8)}`)
    await refreshHistory()
  } catch (e) {
    const detail = (e as { response?: { data?: { error?: string } } })?.response?.data?.error
    errorText.value = detail ?? (e instanceof Error ? e.message : String(e))
  } finally {
    submitting.value = false
  }
}

async function cancelRun(): Promise<void> {
  if (!job.value) return
  try {
    const resp = await simulationApi.cancel(job.value.id)
    if (resp.cancelled) {
      message.warning('已请求取消，等待当前轮结束')
    } else {
      message.info('任务已不在可取消状态')
    }
  } catch (e) {
    message.error(`取消失败：${e instanceof Error ? e.message : String(e)}`)
  }
}

async function loadHistoryRun(snap: JobSnapshot): Promise<void> {
  if (snap.status !== 'completed') return
  errorText.value = null
  try {
    const r = await simulationApi.getResult(snap.id)
    result.value = r
    job.value = snap
    rounds.value = [...r.rounds]
    setTimeout(renderCharts, 0)
  } catch (e) {
    errorText.value = e instanceof Error ? e.message : String(e)
  }
}

// ---------- charts ------------------------------------------------------------

const trendEl = ref<HTMLDivElement | null>(null)
const actionsEl = ref<HTMLDivElement | null>(null)
let trendChart: echarts.ECharts | null = null
let actionsChart: echarts.ECharts | null = null

const ACTION_PALETTE: Record<string, string> = {
  buy: '#00E5A8',
  comment: '#5B8DEF',
  share: '#22D3EE',
  boycott: '#F87171',
  ignore: '#475569',
  search: '#FBBF24',
}
const ACTION_LABEL: Record<string, string> = {
  buy: '购买',
  comment: '评论',
  share: '转发',
  boycott: '抵制',
  ignore: '忽略',
  search: '搜索',
}

function makeTrendOption(): EChartsOption {
  const xs = rounds.value.map((r) => `R${r.round}`)
  return {
    backgroundColor: 'transparent',
    grid: { left: 48, right: 16, top: 36, bottom: 28 },
    legend: { textStyle: { color: '#CBD5E1' }, top: 0 },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: xs,
      axisLine: { lineStyle: { color: 'rgba(91,141,239,0.3)' } },
      axisLabel: { color: '#94A3B8' },
    },
    yAxis: [
      {
        type: 'value',
        name: '情感',
        min: -1,
        max: 1,
        splitLine: { lineStyle: { color: 'rgba(91,141,239,0.1)' } },
        axisLabel: { color: '#94A3B8' },
        nameTextStyle: { color: '#94A3B8' },
      },
      {
        type: 'value',
        name: '比率',
        min: 0,
        max: 1,
        splitLine: { show: false },
        axisLabel: { color: '#94A3B8' },
        nameTextStyle: { color: '#94A3B8' },
      },
    ],
    series: [
      {
        name: '平均情感',
        type: 'line',
        smooth: true,
        symbolSize: 6,
        data: rounds.value.map((r) => r.avg_sentiment),
        lineStyle: { color: '#5B8DEF', width: 2 },
        itemStyle: { color: '#5B8DEF' },
      },
      {
        name: '认知率',
        type: 'line',
        smooth: true,
        symbolSize: 6,
        yAxisIndex: 1,
        data: rounds.value.map((r) => r.awareness),
        lineStyle: { color: '#22D3EE', width: 2 },
        itemStyle: { color: '#22D3EE' },
      },
      {
        name: '购买率',
        type: 'line',
        smooth: true,
        symbolSize: 6,
        yAxisIndex: 1,
        data: rounds.value.map((r) => r.purchase_rate),
        lineStyle: { color: '#00E5A8', width: 2 },
        itemStyle: { color: '#00E5A8' },
      },
      {
        name: '抵制率',
        type: 'line',
        smooth: true,
        symbolSize: 6,
        yAxisIndex: 1,
        data: rounds.value.map((r) => r.boycott_rate),
        lineStyle: { color: '#F87171', width: 2 },
        itemStyle: { color: '#F87171' },
      },
    ],
  }
}

function makeActionsOption(): EChartsOption {
  const xs = rounds.value.map((r) => `R${r.round}`)
  const kinds = Object.keys(ACTION_PALETTE)
  const series = kinds.map((k) => ({
    name: ACTION_LABEL[k] ?? k,
    type: 'bar' as const,
    stack: 'actions',
    emphasis: { focus: 'series' as const },
    itemStyle: { color: ACTION_PALETTE[k] ?? '#5B8DEF' },
    data: rounds.value.map((r) => r.action_counts[k] ?? 0),
  }))
  return {
    backgroundColor: 'transparent',
    grid: { left: 48, right: 16, top: 36, bottom: 28 },
    legend: { textStyle: { color: '#CBD5E1' }, top: 0 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: {
      type: 'category',
      data: xs,
      axisLine: { lineStyle: { color: 'rgba(91,141,239,0.3)' } },
      axisLabel: { color: '#94A3B8' },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(91,141,239,0.1)' } },
      axisLabel: { color: '#94A3B8' },
    },
    series,
  }
}

function renderCharts(): void {
  if (rounds.value.length === 0) return
  if (trendEl.value) {
    trendChart ??= echarts.init(trendEl.value, undefined, { renderer: 'canvas' })
    trendChart.setOption(makeTrendOption(), true)
  }
  if (actionsEl.value) {
    actionsChart ??= echarts.init(actionsEl.value, undefined, { renderer: 'canvas' })
    actionsChart.setOption(makeActionsOption(), true)
  }
}

function disposeCharts(): void {
  trendChart?.dispose()
  actionsChart?.dispose()
  trendChart = actionsChart = null
}

function handleResize(): void {
  trendChart?.resize()
  actionsChart?.resize()
}

watch(
  () => rounds.value.length,
  () => setTimeout(renderCharts, 16),
)

onMounted(() => {
  void (async () => {
    await refreshHistory()
    await focusRunIfRequested()
  })()
  window.addEventListener('resize', handleResize)
})

watch(
  () => props.defaultRunId,
  () => {
    void focusRunIfRequested()
  },
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  closeStream()
  disposeCharts()
})

// ---------- helpers -----------------------------------------------------------

function statusColor(status?: string): 'default' | 'info' | 'success' | 'warning' | 'error' {
  switch (status) {
    case 'completed':
      return 'success'
    case 'running':
    case 'pending':
      return 'info'
    case 'failed':
      return 'error'
    case 'cancelled':
      return 'warning'
    default:
      return 'default'
  }
}

function statusLabel(status?: string): string {
  switch (status) {
    case 'pending':
      return '排队中'
    case 'running':
      return '运行中'
    case 'completed':
      return '已完成'
    case 'failed':
      return '失败'
    case 'cancelled':
      return '已取消'
    default:
      return '空闲'
  }
}
</script>

<template>
  <div class="sim-console">
    <NCard :bordered="false" content-style="padding: 18px 20px">
      <template #header>
        <NSpace align="center">
          <NIcon :component="FlashOutline" :size="20" color="var(--color-primary)" />
          <strong>舆情仿真控制台</strong>
          <NTag :type="statusColor(job?.status)" round size="small">
            {{ statusLabel(job?.status) }}
          </NTag>
        </NSpace>
      </template>

      <NForm
        :model="form"
        label-placement="left"
        label-width="auto"
        size="small"
        require-mark-placement="right-hanging"
      >
        <NGrid :cols="4" :x-gap="16" :y-gap="8" responsive="screen">
          <NGridItem>
            <NFormItem label="Agent 数">
              <NInputNumber v-model:value="form.num_agents" :min="1" :max="10000" />
            </NFormItem>
          </NGridItem>
          <NGridItem>
            <NFormItem label="轮数">
              <NInputNumber v-model:value="form.num_rounds" :min="1" :max="200" />
            </NFormItem>
          </NGridItem>
          <NGridItem>
            <NFormItem label="平均度">
              <NInputNumber v-model:value="form.mean_degree" :min="2" :max="64" />
            </NFormItem>
          </NGridItem>
          <NGridItem>
            <NFormItem label="RNG 种子">
              <NInputNumber v-model:value="form.rng_seed" />
            </NFormItem>
          </NGridItem>
          <NGridItem>
            <NFormItem label="刺激">
              <NInputNumber
                v-model:value="form.stimulus"
                :min="-1"
                :max="1"
                :step="0.1"
                :precision="2"
              />
            </NFormItem>
          </NGridItem>
          <NGridItem>
            <NFormItem label="价格压力">
              <NInputNumber
                v-model:value="form.price_pressure"
                :min="0"
                :max="1"
                :step="0.1"
                :precision="2"
              />
            </NFormItem>
          </NGridItem>
        </NGrid>
      </NForm>

      <NSpace style="margin-top: 12px">
        <NButton type="primary" :loading="submitting" :disabled="isRunning" @click="startRun">
          <template #icon><NIcon :component="PlayCircleOutline" /></template>
          启动仿真
        </NButton>
        <NButton :disabled="!isRunning" @click="cancelRun">
          <template #icon><NIcon :component="CloseCircleOutline" /></template>
          请求取消
        </NButton>
        <NButton tertiary @click="refreshHistory">
          <template #icon><NIcon :component="RefreshOutline" /></template>
          刷新历史
        </NButton>
      </NSpace>
    </NCard>

    <NAlert
      v-if="errorText"
      type="error"
      closable
      style="margin-top: 16px"
      @close="errorText = null"
    >
      {{ errorText }}
    </NAlert>

    <NCard v-if="job" :bordered="false" style="margin-top: 16px" content-style="padding: 18px 20px">
      <NSpace justify="space-between" align="center" style="margin-bottom: 12px">
        <div style="font-family: var(--font-mono); font-size: 13px; color: var(--text-muted)">
          {{ job.id.slice(0, 12) }} · 创建于
          {{ new Date(job.created_at).toLocaleTimeString('zh-CN') }}
        </div>
        <NTag :type="statusColor(job.status)" round size="small">
          {{ statusLabel(job.status) }}
        </NTag>
      </NSpace>
      <NProgress
        :percentage="progressPercent"
        :status="
          job.status === 'failed'
            ? 'error'
            : job.status === 'cancelled'
              ? 'warning'
              : job.status === 'completed'
                ? 'success'
                : 'default'
        "
        :indicator-placement="'inside'"
      />
      <NGrid :cols="4" :x-gap="16" :y-gap="12" responsive="screen" style="margin-top: 14px">
        <NGridItem>
          <NStatistic label="进度"> {{ job.rounds_done }} / {{ job.total_rounds }} </NStatistic>
        </NGridItem>
        <NGridItem>
          <NStatistic label="平均情感">
            {{ job.last_round_metrics?.avg_sentiment.toFixed(3) ?? '—' }}
          </NStatistic>
        </NGridItem>
        <NGridItem>
          <NStatistic label="购买率">
            {{
              job.last_round_metrics
                ? (job.last_round_metrics.purchase_rate * 100).toFixed(1) + '%'
                : '—'
            }}
          </NStatistic>
        </NGridItem>
        <NGridItem>
          <NStatistic label="抵制率">
            {{
              job.last_round_metrics
                ? (job.last_round_metrics.boycott_rate * 100).toFixed(1) + '%'
                : '—'
            }}
          </NStatistic>
        </NGridItem>
      </NGrid>
    </NCard>

    <NGrid
      v-if="rounds.length"
      :cols="2"
      :x-gap="16"
      :y-gap="16"
      responsive="screen"
      style="margin-top: 16px"
    >
      <NGridItem>
        <NCard :bordered="false" content-style="padding: 12px 12px 16px">
          <template #header>
            <NSpace align="center">
              <NIcon :component="StatsChartOutline" />
              核心指标轨迹
            </NSpace>
          </template>
          <div ref="trendEl" class="sim-chart" />
        </NCard>
      </NGridItem>
      <NGridItem>
        <NCard :bordered="false" content-style="padding: 12px 12px 16px">
          <template #header>
            <NSpace align="center">
              <NIcon :component="StatsChartOutline" />
              动作分布（按轮）
            </NSpace>
          </template>
          <div ref="actionsEl" class="sim-chart" />
        </NCard>
      </NGridItem>
    </NGrid>

    <NCard
      v-if="result"
      :bordered="false"
      style="margin-top: 16px"
      content-style="padding: 18px 20px"
    >
      <template #header>
        <NSpace align="center">
          <NIcon :component="TimerOutline" />
          仿真摘要
        </NSpace>
      </template>
      <NCollapse arrow-placement="right">
        <NCollapseItem title="人群结构" name="pop">
          <NSpace>
            <NTag v-for="(v, k) in result.population.persona_counts" :key="k" round size="small">
              {{ k }}: {{ v }}
            </NTag>
          </NSpace>
          <div style="margin-top: 8px; color: var(--text-muted); font-size: 12px">
            初始平均情感 {{ result.population.avg_initial_sentiment.toFixed(3) }} · 人口规模
            {{ result.population.size }}
          </div>
        </NCollapseItem>
        <NCollapseItem title="社交网络" name="net">
          节点 {{ result.network.nodes }} · 边 {{ result.network.edges }} · 平均度
          {{ result.network.mean_degree.toFixed(2) }} · 最大度 {{ result.network.max_degree }}
        </NCollapseItem>
        <NCollapseItem title="累计动作" name="actions">
          <NSpace>
            <NTag
              v-for="(v, k) in result.final_action_totals"
              :key="k"
              round
              size="small"
              :color="{ color: ACTION_PALETTE[k] ?? '#475569', textColor: '#0F172A' }"
            >
              {{ ACTION_LABEL[k] ?? k }}: {{ v }}
            </NTag>
          </NSpace>
        </NCollapseItem>
      </NCollapse>
    </NCard>

    <NCard :bordered="false" style="margin-top: 16px" content-style="padding: 18px 20px">
      <template #header>
        <NSpace align="center">
          <NIcon :component="TimerOutline" />
          运行历史
        </NSpace>
      </template>
      <NSpin :show="false">
        <NEmpty v-if="!runHistory.length" size="small" description="尚未运行过仿真" />
        <NList v-else hoverable clickable :show-divider="false">
          <NListItem
            v-for="snap in runHistory.slice(0, 8)"
            :key="snap.id"
            @click="loadHistoryRun(snap)"
          >
            <NThing>
              <template #header>
                <NSpace align="center">
                  <span style="font-family: var(--font-mono)">{{ snap.id.slice(0, 8) }}</span>
                  <NTag :type="statusColor(snap.status)" round size="small">
                    {{ statusLabel(snap.status) }}
                  </NTag>
                </NSpace>
              </template>
              <template #description>
                <NSpace size="small">
                  <span>Agent {{ snap.config.num_agents }}</span>
                  <NDivider vertical />
                  <span>{{ snap.config.num_rounds }} 轮</span>
                  <NDivider vertical />
                  <span>{{ new Date(snap.created_at).toLocaleString('zh-CN') }}</span>
                </NSpace>
              </template>
            </NThing>
          </NListItem>
        </NList>
      </NSpin>
    </NCard>
  </div>
</template>

<style scoped>
.sim-console {
  width: 100%;
}
.sim-chart {
  width: 100%;
  height: 280px;
}
</style>
