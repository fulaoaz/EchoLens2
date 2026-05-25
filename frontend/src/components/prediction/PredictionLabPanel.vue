<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  NAlert,
  NButton,
  NCard,
  NDatePicker,
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
  NSelect,
  NSpace,
  NStatistic,
  NTabs,
  NTabPane,
  NTag,
  NThing,
  useMessage,
} from 'naive-ui'
import {
  AnalyticsOutline,
  PlayCircleOutline,
  PulseOutline,
  RefreshOutline,
  TrendingUpOutline,
} from '@vicons/ionicons5'
import * as echarts from 'echarts/core'
import { LineChart, BarChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TooltipComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'

import {
  predictionApi,
  type CausalInput,
  type CausalPayload,
  type ForecastInput,
  type ForecastPayload,
  type PredictionMetric,
  type PredictionRun,
  type PredictionRunSnapshot,
} from '@/api/prediction'

echarts.use([
  LineChart,
  BarChart,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TooltipComponent,
  CanvasRenderer,
])

const props = defineProps<{ projectId: string; defaultRunId?: string | null }>()
const message = useMessage()

// ---------- forms -------------------------------------------------------------

const METRIC_OPTIONS: { label: string; value: PredictionMetric }[] = [
  { label: '舆情声量 (volume)', value: 'volume' },
  { label: '净情感 (sentiment)', value: 'sentiment' },
  { label: '合成 GMV (gmv_synth)', value: 'gmv_synth' },
  { label: '负面占比 (negative_ratio)', value: 'negative_ratio' },
]

const forecastForm = reactive<Required<ForecastInput>>({
  metric: 'gmv_synth',
  horizon_days: 14,
  seasonality_period: 7,
  confidence: 0.95,
})

const causalForm = reactive<{
  metric: PredictionMetric
  intervention_start: number | null
  intervention_end: number | null
}>({
  metric: 'sentiment',
  intervention_start: null,
  intervention_end: null,
})

// ---------- run state ---------------------------------------------------------

const tab = ref<'forecast' | 'causal'>('forecast')
const submitting = ref(false)
const errorText = ref<string | null>(null)
const currentRun = ref<PredictionRun | null>(null)
const history = ref<PredictionRunSnapshot[]>([])

const isForecastRun = computed(() => currentRun.value?.kind === 'forecast')
const isCausalRun = computed(() => currentRun.value?.kind === 'causal')

const forecastResult = computed<ForecastPayload | null>(() =>
  isForecastRun.value ? (currentRun.value!.result as ForecastPayload) : null,
)
const causalResult = computed<CausalPayload | null>(() =>
  isCausalRun.value ? (currentRun.value!.result as CausalPayload) : null,
)

async function refreshHistory(): Promise<void> {
  try {
    history.value = await predictionApi.listRuns(props.projectId)
  } catch {
    history.value = []
  }
}

async function focusRunIfRequested(): Promise<void> {
  const target = props.defaultRunId
  if (!target) return
  const snap = history.value.find((s) => s.id === target)
  if (snap) await loadHistoryRun(snap)
}

function toIsoDate(ms: number | null): string | null {
  if (ms == null) return null
  return new Date(ms).toISOString().slice(0, 10)
}

async function runForecast(): Promise<void> {
  submitting.value = true
  errorText.value = null
  try {
    const run = await predictionApi.forecast(props.projectId, { ...forecastForm })
    currentRun.value = run
    setTimeout(renderForecastChart, 16)
    message.success(`预测完成 · ${run.id.slice(0, 8)}`)
    await refreshHistory()
  } catch (e) {
    const detail = (e as { response?: { data?: { error?: string } } })?.response?.data?.error
    errorText.value = detail ?? (e instanceof Error ? e.message : String(e))
  } finally {
    submitting.value = false
  }
}

async function runCausal(): Promise<void> {
  if (!causalForm.intervention_start) {
    errorText.value = '请选择干预开始日期'
    return
  }
  submitting.value = true
  errorText.value = null
  try {
    const payload: CausalInput = {
      metric: causalForm.metric,
      intervention_start: toIsoDate(causalForm.intervention_start)!,
      intervention_end: toIsoDate(causalForm.intervention_end),
    }
    const run = await predictionApi.causal(props.projectId, payload)
    currentRun.value = run
    setTimeout(renderCausalChart, 16)
    message.success(`因果分析完成 · ${run.id.slice(0, 8)}`)
    await refreshHistory()
  } catch (e) {
    const detail = (e as { response?: { data?: { error?: string } } })?.response?.data?.error
    errorText.value = detail ?? (e instanceof Error ? e.message : String(e))
  } finally {
    submitting.value = false
  }
}

async function loadHistoryRun(snap: PredictionRunSnapshot): Promise<void> {
  errorText.value = null
  try {
    const run = await predictionApi.getRun(snap.id)
    currentRun.value = run
    tab.value = run.kind === 'causal' ? 'causal' : 'forecast'
    setTimeout(() => {
      if (run.kind === 'causal') renderCausalChart()
      else renderForecastChart()
    }, 16)
  } catch (e) {
    errorText.value = e instanceof Error ? e.message : String(e)
  }
}

// ---------- charts ------------------------------------------------------------

const forecastEl = ref<HTMLDivElement | null>(null)
const causalEl = ref<HTMLDivElement | null>(null)
let forecastChart: echarts.ECharts | null = null
let causalChart: echarts.ECharts | null = null

function makeForecastOption(payload: ForecastPayload): EChartsOption {
  const hist = payload.forecast.history
  const fc = payload.forecast.forecast
  const allDates = [...hist.map((p) => p.ts), ...fc.map((p) => p.ts)]
  const histY = hist.map((p) => p.yhat)
  const histYRaw: (number | null)[] = histY
  const fcY = [...new Array(hist.length).fill(null), ...fc.map((p) => p.yhat)]
  const lower = [...new Array(hist.length).fill(null), ...fc.map((p) => p.yhat_lower)]
  const upper = [...new Array(hist.length).fill(null), ...fc.map((p) => p.yhat_upper)]
  const bandDelta = upper.map((u, i) => {
    if (u == null || lower[i] == null) return null
    return Number(((u as number) - (lower[i] as number)).toFixed(4))
  })

  return {
    backgroundColor: 'transparent',
    grid: { left: 56, right: 24, top: 36, bottom: 32 },
    legend: {
      textStyle: { color: '#CBD5E1' },
      top: 0,
      data: [
        '历史拟合',
        `置信带 (${(payload.forecast.config.confidence * 100).toFixed(0)}%)`,
        '预测 ŷ',
      ],
    },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: allDates,
      axisLine: { lineStyle: { color: 'rgba(91,141,239,0.3)' } },
      axisLabel: { color: '#94A3B8', hideOverlap: true },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(91,141,239,0.1)' } },
      axisLabel: { color: '#94A3B8' },
    },
    series: [
      {
        name: '历史拟合',
        type: 'line',
        smooth: true,
        symbol: 'none',
        data: [...histYRaw, ...new Array(fc.length).fill(null)],
        lineStyle: { color: '#94A3B8', width: 1.5, type: 'dashed' },
        itemStyle: { color: '#94A3B8' },
      },
      {
        name: '置信带下沿',
        type: 'line',
        symbol: 'none',
        data: lower,
        lineStyle: { width: 0 },
        stack: 'band',
      },
      {
        name: `置信带 (${(payload.forecast.config.confidence * 100).toFixed(0)}%)`,
        type: 'line',
        symbol: 'none',
        data: bandDelta,
        lineStyle: { width: 0 },
        areaStyle: { color: 'rgba(91,141,239,0.18)' },
        stack: 'band',
      },
      {
        name: '预测 ŷ',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        data: fcY,
        lineStyle: { color: '#5B8DEF', width: 2 },
        itemStyle: { color: '#5B8DEF' },
        markLine: hist.length
          ? {
              symbol: ['none', 'none'],
              lineStyle: { color: '#5B8DEF', type: 'dashed', opacity: 0.5 },
              data: [{ xAxis: hist[hist.length - 1]?.ts ?? '' }],
              label: { color: '#94A3B8', formatter: '预测起点' },
            }
          : undefined,
      },
    ],
  }
}

function makeCausalOption(payload: CausalPayload): EChartsOption {
  const allDates = [...payload.pre_series, ...payload.post_series].map((p) => p.date)
  const observed = [
    ...payload.pre_series.map((p) => p.value),
    ...payload.post_series.map((p) => p.value),
  ]
  const counterfactual = [
    ...new Array(payload.pre_series.length).fill(null),
    ...payload.counterfactual_series.map((p) => p.value),
  ]

  return {
    backgroundColor: 'transparent',
    grid: { left: 56, right: 24, top: 36, bottom: 32 },
    legend: { textStyle: { color: '#CBD5E1' }, top: 0 },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: allDates,
      axisLine: { lineStyle: { color: 'rgba(91,141,239,0.3)' } },
      axisLabel: { color: '#94A3B8', hideOverlap: true },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(91,141,239,0.1)' } },
      axisLabel: { color: '#94A3B8' },
    },
    series: [
      {
        name: '实际观测',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        data: observed,
        lineStyle: { color: '#00E5A8', width: 2 },
        itemStyle: { color: '#00E5A8' },
        markLine: {
          symbol: ['none', 'none'],
          lineStyle: { color: '#F87171', type: 'dashed' },
          data: [{ xAxis: payload.intervention_start }],
          label: { color: '#F87171', formatter: '干预' },
        },
      },
      {
        name: '反事实（无干预）',
        type: 'line',
        smooth: true,
        symbol: 'none',
        data: counterfactual,
        lineStyle: { color: '#94A3B8', width: 1.5, type: 'dashed' },
        itemStyle: { color: '#94A3B8' },
      },
    ],
  }
}

function renderForecastChart(): void {
  if (!forecastResult.value || !forecastEl.value) return
  forecastChart ??= echarts.init(forecastEl.value, undefined, { renderer: 'canvas' })
  forecastChart.setOption(makeForecastOption(forecastResult.value), true)
}

function renderCausalChart(): void {
  if (!causalResult.value || !causalEl.value) return
  causalChart ??= echarts.init(causalEl.value, undefined, { renderer: 'canvas' })
  causalChart.setOption(makeCausalOption(causalResult.value), true)
}

function disposeCharts(): void {
  forecastChart?.dispose()
  causalChart?.dispose()
  forecastChart = causalChart = null
}

function handleResize(): void {
  forecastChart?.resize()
  causalChart?.resize()
}

watch(tab, () => {
  setTimeout(() => {
    if (tab.value === 'forecast') renderForecastChart()
    else renderCausalChart()
  }, 16)
})

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
  disposeCharts()
})

// ---------- helpers -----------------------------------------------------------

function kindLabel(kind?: string): string {
  if (kind === 'forecast') return '时序预测'
  if (kind === 'causal') return '因果分析'
  if (kind === 'fused') return '融合'
  return '—'
}

function statusColor(status?: string): 'default' | 'info' | 'success' | 'warning' | 'error' {
  switch (status) {
    case 'completed':
      return 'success'
    case 'failed':
      return 'error'
    default:
      return 'default'
  }
}

function metricLabel(m?: string): string {
  return METRIC_OPTIONS.find((o) => o.value === m)?.label ?? m ?? '—'
}

function formatPercent(v: number): string {
  return (v * 100).toFixed(1) + '%'
}
</script>

<template>
  <div class="prediction-lab">
    <NCard :bordered="false" content-style="padding: 18px 20px">
      <template #header>
        <NSpace align="center">
          <NIcon :component="TrendingUpOutline" :size="20" color="var(--color-primary)" />
          <strong>预测实验室</strong>
          <NTag round size="small" type="info">numpy + DiD + 规则解释</NTag>
        </NSpace>
      </template>

      <NTabs v-model:value="tab" type="line" animated>
        <!-- ============== Forecast ============== -->
        <NTabPane name="forecast" tab="时序预测">
          <NForm :model="forecastForm" label-placement="left" label-width="auto" size="small">
            <NGrid :cols="4" :x-gap="16" :y-gap="8" responsive="screen">
              <NGridItem>
                <NFormItem label="指标">
                  <NSelect v-model:value="forecastForm.metric" :options="METRIC_OPTIONS" />
                </NFormItem>
              </NGridItem>
              <NGridItem>
                <NFormItem label="预测天数">
                  <NInputNumber v-model:value="forecastForm.horizon_days" :min="1" :max="200" />
                </NFormItem>
              </NGridItem>
              <NGridItem>
                <NFormItem label="季节周期">
                  <NInputNumber
                    v-model:value="forecastForm.seasonality_period"
                    :min="1"
                    :max="30"
                  />
                </NFormItem>
              </NGridItem>
              <NGridItem>
                <NFormItem label="置信水平">
                  <NInputNumber
                    v-model:value="forecastForm.confidence"
                    :min="0.5"
                    :max="0.99"
                    :step="0.05"
                    :precision="2"
                  />
                </NFormItem>
              </NGridItem>
            </NGrid>
          </NForm>
          <NSpace style="margin-top: 12px">
            <NButton
              type="primary"
              :loading="submitting"
              :disabled="submitting"
              @click="runForecast"
            >
              <template #icon><NIcon :component="PlayCircleOutline" /></template>
              运行预测
            </NButton>
            <NButton tertiary @click="refreshHistory">
              <template #icon><NIcon :component="RefreshOutline" /></template>
              刷新历史
            </NButton>
          </NSpace>
        </NTabPane>

        <!-- ============== Causal ============== -->
        <NTabPane name="causal" tab="因果干预 (DiD)">
          <NForm label-placement="left" label-width="auto" size="small">
            <NGrid :cols="4" :x-gap="16" :y-gap="8" responsive="screen">
              <NGridItem>
                <NFormItem label="指标">
                  <NSelect v-model:value="causalForm.metric" :options="METRIC_OPTIONS" />
                </NFormItem>
              </NGridItem>
              <NGridItem>
                <NFormItem label="干预开始">
                  <NDatePicker
                    v-model:value="causalForm.intervention_start"
                    type="date"
                    clearable
                    style="width: 100%"
                  />
                </NFormItem>
              </NGridItem>
              <NGridItem>
                <NFormItem label="干预结束(可选)">
                  <NDatePicker
                    v-model:value="causalForm.intervention_end"
                    type="date"
                    clearable
                    style="width: 100%"
                  />
                </NFormItem>
              </NGridItem>
            </NGrid>
          </NForm>
          <NSpace style="margin-top: 12px">
            <NButton
              type="primary"
              :loading="submitting"
              :disabled="submitting || !causalForm.intervention_start"
              @click="runCausal"
            >
              <template #icon><NIcon :component="PulseOutline" /></template>
              估计 ATE
            </NButton>
            <NButton tertiary @click="refreshHistory">
              <template #icon><NIcon :component="RefreshOutline" /></template>
              刷新历史
            </NButton>
          </NSpace>
        </NTabPane>
      </NTabs>
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

    <!-- ============== Forecast result ============== -->
    <template v-if="forecastResult">
      <NCard :bordered="false" style="margin-top: 16px" content-style="padding: 12px 12px 16px">
        <template #header>
          <NSpace align="center">
            <NIcon :component="AnalyticsOutline" />
            预测曲线 · {{ metricLabel(currentRun?.metric) }}
          </NSpace>
        </template>
        <div ref="forecastEl" class="pred-chart" />
      </NCard>

      <NGrid :cols="4" :x-gap="16" :y-gap="12" responsive="screen" style="margin-top: 16px">
        <NGridItem>
          <NCard :bordered="false" content-style="padding: 14px 18px">
            <NStatistic label="历史观测">
              {{ forecastResult.forecast.diagnostics.n_observations }} 天
            </NStatistic>
          </NCard>
        </NGridItem>
        <NGridItem>
          <NCard :bordered="false" content-style="padding: 14px 18px">
            <NStatistic label="MAPE">
              {{ formatPercent(forecastResult.forecast.diagnostics.mape) }}
            </NStatistic>
          </NCard>
        </NGridItem>
        <NGridItem>
          <NCard :bordered="false" content-style="padding: 14px 18px">
            <NStatistic label="R²">
              {{ forecastResult.forecast.diagnostics.r2.toFixed(3) }}
            </NStatistic>
          </NCard>
        </NGridItem>
        <NGridItem>
          <NCard :bordered="false" content-style="padding: 14px 18px">
            <NStatistic label="趋势斜率/天">
              {{ forecastResult.forecast.diagnostics.trend_slope.toFixed(4) }}
            </NStatistic>
          </NCard>
        </NGridItem>
      </NGrid>

      <NCard :bordered="false" style="margin-top: 16px" content-style="padding: 18px 20px">
        <template #header>预测解读 · {{ forecastResult.explanation.metric_label }}</template>
        <p class="pred-headline">{{ forecastResult.explanation.headline }}</p>
        <ul class="pred-bullets">
          <li v-for="b in forecastResult.explanation.bullets" :key="b.text">
            {{ b.text }}
            <NSpace size="small" style="display: inline-flex; margin-left: 8px">
              <NTag v-for="ev in b.evidence" :key="ev" size="tiny" round type="info">
                {{ ev }}={{ forecastResult.explanation.evidence_index[ev] ?? '—' }}
              </NTag>
            </NSpace>
          </li>
        </ul>
        <NDivider style="margin: 12px 0" />
        <NSpace>
          <NTag
            v-for="flag in forecastResult.explanation.risk_flags"
            :key="flag"
            type="warning"
            round
            size="small"
          >
            {{ flag }}
          </NTag>
          <span
            v-if="!forecastResult.explanation.risk_flags.length"
            style="color: var(--text-muted); font-size: 12px"
          >
            未触发风险标记
          </span>
        </NSpace>
      </NCard>
    </template>

    <!-- ============== Causal result ============== -->
    <template v-if="causalResult">
      <NCard :bordered="false" style="margin-top: 16px" content-style="padding: 12px 12px 16px">
        <template #header>
          <NSpace align="center">
            <NIcon :component="PulseOutline" />
            干预反事实 · {{ metricLabel(currentRun?.metric) }}
          </NSpace>
        </template>
        <div v-if="causalResult.status === 'ok'" ref="causalEl" class="pred-chart" />
        <NEmpty
          v-else
          :description="
            causalResult.status === 'insufficient_data'
              ? '前置窗口不足 3 天，无法估计反事实趋势'
              : '干预日期晚于历史末端，未观测到 post 窗口'
          "
        />
      </NCard>

      <NGrid
        v-if="causalResult.status === 'ok'"
        :cols="4"
        :x-gap="16"
        :y-gap="12"
        responsive="screen"
        style="margin-top: 16px"
      >
        <NGridItem>
          <NCard :bordered="false" content-style="padding: 14px 18px">
            <NStatistic label="ATE">
              {{ causalResult.ate.toFixed(3) }}
            </NStatistic>
          </NCard>
        </NGridItem>
        <NGridItem>
          <NCard :bordered="false" content-style="padding: 14px 18px">
            <NStatistic label="相对变化">
              {{ formatPercent(causalResult.ate_relative) }}
            </NStatistic>
          </NCard>
        </NGridItem>
        <NGridItem>
          <NCard :bordered="false" content-style="padding: 14px 18px">
            <NStatistic label="p 值">
              {{ causalResult.p_value.toFixed(4) }}
            </NStatistic>
          </NCard>
        </NGridItem>
        <NGridItem>
          <NCard :bordered="false" content-style="padding: 14px 18px">
            <NStatistic label="样本 (前/后)">
              {{ causalResult.pre_days }} / {{ causalResult.post_days }}
            </NStatistic>
          </NCard>
        </NGridItem>
      </NGrid>

      <NCard
        v-if="causalResult.status === 'ok'"
        :bordered="false"
        style="margin-top: 16px"
        content-style="padding: 18px 20px"
      >
        <template #header>因果解读</template>
        <p class="pred-headline">
          干预后均值 {{ causalResult.post_mean.toFixed(3) }}，反事实均值
          {{ causalResult.post_counterfactual_mean.toFixed(3) }}， ATE =
          {{ causalResult.ate.toFixed(3) }} ({{ formatPercent(causalResult.ate_relative) }})； 95%
          CI [{{ causalResult.ci_low.toFixed(3) }}, {{ causalResult.ci_high.toFixed(3) }}]，
          {{ causalResult.narrative_seed.significant ? '统计显著 (p<0.05)' : '未达显著 (p≥0.05)' }}.
        </p>
        <NSpace>
          <NTag
            :type="
              causalResult.narrative_seed.direction === 'up'
                ? 'success'
                : causalResult.narrative_seed.direction === 'down'
                  ? 'error'
                  : 'default'
            "
            round
          >
            方向：{{
              causalResult.narrative_seed.direction === 'up'
                ? '正向'
                : causalResult.narrative_seed.direction === 'down'
                  ? '负向'
                  : '持平'
            }}
          </NTag>
          <NTag round type="info"
            >|ATE/反事实| = {{ causalResult.narrative_seed.abs_relative_pct.toFixed(2) }}%</NTag
          >
          <NTag round>模型：{{ causalResult.model }}</NTag>
        </NSpace>
      </NCard>
    </template>

    <!-- ============== History ============== -->
    <NCard :bordered="false" style="margin-top: 16px" content-style="padding: 18px 20px">
      <template #header>预测运行历史</template>
      <NEmpty v-if="!history.length" size="small" description="尚未生成预测" />
      <NList v-else hoverable clickable :show-divider="false">
        <NListItem v-for="snap in history.slice(0, 8)" :key="snap.id" @click="loadHistoryRun(snap)">
          <NThing>
            <template #header>
              <NSpace align="center">
                <span style="font-family: var(--font-mono)">{{ snap.id.slice(0, 8) }}</span>
                <NTag round size="small" :type="snap.kind === 'causal' ? 'warning' : 'info'">
                  {{ kindLabel(snap.kind) }}
                </NTag>
                <NTag :type="statusColor(snap.status)" round size="small">
                  {{ snap.status }}
                </NTag>
              </NSpace>
            </template>
            <template #description>
              <NSpace size="small">
                <span>{{ metricLabel(snap.metric) }}</span>
                <NDivider vertical />
                <span>{{ new Date(snap.created_at).toLocaleString('zh-CN') }}</span>
              </NSpace>
            </template>
          </NThing>
        </NListItem>
      </NList>
    </NCard>
  </div>
</template>

<style scoped>
.prediction-lab {
  width: 100%;
}
.pred-chart {
  width: 100%;
  height: 320px;
}
.pred-headline {
  color: var(--text-primary);
  font-size: var(--fs-md);
  line-height: 1.6;
  margin: 0 0 12px;
}
.pred-bullets {
  margin: 0;
  padding-left: 18px;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: 1.7;
}
.pred-bullets li {
  margin-bottom: 6px;
}
</style>
