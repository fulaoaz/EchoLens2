<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  NCard,
  NSpace,
  NSpin,
  NAlert,
  NButton,
  NTag,
  NGrid,
  NGridItem,
  NIcon,
  NEmpty,
  NDivider,
  NProgress,
  NList,
  NListItem,
  NThing,
  NTooltip,
  NStatistic,
  useMessage,
} from 'naive-ui'
import {
  RefreshOutline,
  AlertCircleOutline,
  CheckmarkCircleOutline,
  WarningOutline,
  GitNetworkOutline,
  LayersOutline,
  ShieldCheckmarkOutline,
} from '@vicons/ionicons5'
import {
  decisionApi,
  type DecisionConfidenceRollup,
  type DecisionKgFeatures,
  type DecisionRecommendation,
  type DecisionSnapshot,
  type DecisionSourceRunIds,
  type RiskLevel,
} from '@/api/decision'
import { useReliabilityTier } from '@/composables/useReliabilityTier'

const props = defineProps<{ projectId: string }>()
const emit = defineEmits<{
  (e: 'open-run', kind: 'simulation' | 'forecast' | 'causal', runId: string): void
}>()

const message = useMessage()

const loading = ref(false)
const snapshot = ref<DecisionSnapshot | null>(null)
const errorText = ref<string | null>(null)

async function load(): Promise<void> {
  if (!props.projectId) return
  loading.value = true
  errorText.value = null
  try {
    snapshot.value = await decisionApi.snapshot(props.projectId)
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    errorText.value = msg
    message.error(`决策快照加载失败：${msg}`)
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.projectId, load)

// ---------- derived state ---------------------------------------------------

const coverage = computed(() => snapshot.value?.coverage ?? null)
const risk = computed(() => snapshot.value?.risk ?? null)
const recommendations = computed<DecisionRecommendation[]>(
  () => snapshot.value?.recommendations ?? [],
)
const evidenceIds = computed<string[]>(() => snapshot.value?.evidence_ids ?? [])
const kgFeatures = computed<DecisionKgFeatures>(() => snapshot.value?.kg_features ?? {})
const confidenceRollup = computed<DecisionConfidenceRollup>(() => snapshot.value?.confidence ?? {})
const sourceRunIds = computed<DecisionSourceRunIds>(() => snapshot.value?.source_run_ids ?? {})

const riskColor = computed<'success' | 'warning' | 'error' | 'default'>(() => {
  const lvl = risk.value?.level
  if (lvl === 'high') return 'error'
  if (lvl === 'elevated') return 'warning'
  if (lvl === 'low') return 'success'
  return 'default'
})

const riskLabel = (lvl: RiskLevel | undefined): string => {
  if (lvl === 'high') return '高风险'
  if (lvl === 'elevated') return '中等风险'
  if (lvl === 'low') return '低风险'
  return '未知'
}

const priorityType = (p: DecisionRecommendation['priority']): 'error' | 'warning' | 'info' => {
  if (p === 'high') return 'error'
  if (p === 'medium') return 'warning'
  return 'info'
}

const priorityLabel = (p: DecisionRecommendation['priority']): string => {
  if (p === 'high') return '高优先级'
  if (p === 'medium') return '中优先级'
  return '观察项'
}

const coverageBadges = computed(() => {
  const c = coverage.value
  if (!c) return []
  return [
    { key: 'simulation', label: '舆情仿真', present: c.simulation },
    { key: 'forecast', label: '预测拟合', present: c.forecast },
    { key: 'causal', label: '因果分析', present: c.causal },
  ]
})

const fmtPct = (v: number | null | undefined, digits = 1): string => {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  return `${(v * 100).toFixed(digits)}%`
}
const fmtNum = (v: number | null | undefined, digits = 2): string => {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  return v.toFixed(digits)
}
const fmtCount = (v: number | null | undefined): string => {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  return String(Math.round(v))
}

const SOURCE_LABEL: Record<keyof DecisionSourceRunIds, string> = {
  simulation: '仿真',
  forecast: '预测',
  causal: '因果',
}

const sourceRunChips = computed<
  { kind: 'simulation' | 'forecast' | 'causal'; label: string; runId: string }[]
>(() => {
  const out: { kind: 'simulation' | 'forecast' | 'causal'; label: string; runId: string }[] = []
  ;(['simulation', 'forecast', 'causal'] as const).forEach((k) => {
    const id = sourceRunIds.value?.[k]
    if (id) out.push({ kind: k, label: SOURCE_LABEL[k], runId: id })
  })
  return out
})

const kgFeatureRows = computed<{ key: string; label: string; value: number | string }[]>(() => {
  const f = kgFeatures.value ?? {}
  const order: { key: string; label: string }[] = [
    { key: 'node_count', label: '节点' },
    { key: 'edge_count', label: '边' },
    { key: 'kol_count', label: 'KOL' },
    { key: 'topic_count', label: '话题' },
    { key: 'product_count', label: '商品' },
    { key: 'brand_count', label: '品牌' },
  ]
  return order
    .filter((row) => f[row.key] !== undefined && f[row.key] !== null)
    .map((row) => ({ ...row, value: f[row.key] as number | string }))
})

const reliability = computed(() => confidenceRollup.value?.reliability ?? null)
// 阈值与 (label, slug, naiveType) 的单一权威源在 `@/composables/useReliabilityTier`，
// 后端镜像在 `backend/app/services/reliability_tier.py`。任何颜色档位调整都必须改
// composable，并同步改两端契约测试，绝不在这里硬写 0.7/0.4。
const reliabilityTier = useReliabilityTier(reliability)
const reliabilityColor = computed<'success' | 'warning' | 'error' | 'default'>(
  () => reliabilityTier.value.naiveType,
)

const sampleEvidence = computed(() => evidenceIds.value.slice(0, 8))

function openRun(kind: 'simulation' | 'forecast' | 'causal', runId?: string | null): void {
  if (!runId) return
  emit('open-run', kind, runId)
}

function recSourceRuns(
  rec: DecisionRecommendation,
): { kind: 'simulation' | 'forecast' | 'causal'; runId: string }[] {
  const src = rec.source_run_ids ?? {}
  const out: { kind: 'simulation' | 'forecast' | 'causal'; runId: string }[] = []
  ;(['simulation', 'forecast', 'causal'] as const).forEach((k) => {
    if (src[k]) out.push({ kind: k, runId: src[k] as string })
  })
  return out
}

function recMetricEntries(rec: DecisionRecommendation): { key: string; value: string }[] {
  const trace = rec.metric_trace ?? {}
  return Object.entries(trace).map(([k, v]) => ({
    key: k,
    value: typeof v === 'number' ? fmtNum(v, 4) : String(v),
  }))
}
</script>

<template>
  <div class="decision-board">
    <NSpace align="center" justify="space-between" style="margin-bottom: 16px">
      <NSpace align="center" :size="8">
        <strong>综合决策快照</strong>
        <NTag v-if="snapshot" size="small" round>model · {{ snapshot.model }}</NTag>
        <NTag v-if="snapshot?.kg_linked" size="small" round type="success">
          <template #icon><NIcon :component="GitNetworkOutline" /></template>
          已链接图谱
        </NTag>
      </NSpace>
      <NButton size="small" :loading="loading" @click="load">
        <template #icon><NIcon :component="RefreshOutline" /></template>
        刷新
      </NButton>
    </NSpace>

    <NSpin :show="loading">
      <NAlert v-if="errorText" type="error" :title="'加载失败'" closable @close="errorText = null">
        {{ errorText }}
      </NAlert>

      <NEmpty
        v-else-if="!snapshot"
        description="尚无决策快照——后端可能仍在初始化"
        style="padding: 48px 0"
      />

      <template v-else>
        <!-- 数据覆盖 -->
        <NCard :bordered="false" content-style="padding: 14px 18px" style="margin-bottom: 16px">
          <NSpace align="center" :size="12" wrap>
            <span style="color: var(--text-muted); font-size: var(--fs-sm)">数据来源覆盖：</span>
            <NTag
              v-for="b in coverageBadges"
              :key="b.key"
              :type="b.present ? 'success' : 'default'"
              :bordered="false"
              round
              size="small"
            >
              <template #icon>
                <NIcon :component="b.present ? CheckmarkCircleOutline : AlertCircleOutline" />
              </template>
              {{ b.label }}
            </NTag>
            <NDivider v-if="sourceRunChips.length" vertical />
            <NTag
              v-for="chip in sourceRunChips"
              :key="chip.kind"
              size="small"
              round
              type="info"
              :bordered="false"
              checkable
              role="button"
              tabindex="0"
              :aria-label="`打开${chip.label} Run ${chip.runId}`"
              style="cursor: pointer"
              @click="openRun(chip.kind, chip.runId)"
              @keydown.enter.prevent="openRun(chip.kind, chip.runId)"
              @keydown.space.prevent="openRun(chip.kind, chip.runId)"
            >
              {{ chip.label }} · {{ chip.runId.slice(0, 8) }}
            </NTag>
          </NSpace>
        </NCard>

        <!-- 风险评分 -->
        <NCard
          v-if="risk"
          :bordered="false"
          content-style="padding: 18px 20px"
          style="margin-bottom: 16px"
        >
          <NGrid :cols="24" :x-gap="20" :y-gap="12" responsive="screen">
            <NGridItem :span="8">
              <NSpace vertical :size="6">
                <span class="label-muted">综合风险评分</span>
                <div class="risk-score-row">
                  <span class="risk-score-num" :class="`risk-score-num--${risk.level}`">
                    {{ risk.score }}
                  </span>
                  <span class="risk-score-suffix">/ 100</span>
                </div>
                <NTag :type="riskColor" round size="small">
                  <template #icon>
                    <NIcon
                      :component="risk.level === 'low' ? CheckmarkCircleOutline : WarningOutline"
                    />
                  </template>
                  {{ riskLabel(risk.level) }}
                </NTag>
              </NSpace>
            </NGridItem>
            <NGridItem :span="16">
              <NSpace vertical :size="8">
                <span class="label-muted">风险维度（依据规则汇总）</span>
                <NProgress
                  :percentage="risk.score"
                  :status="riskColor === 'default' ? 'info' : riskColor"
                  :indicator-placement="'inside'"
                  processing
                />
                <NList v-if="risk.reasons.length" size="small" hoverable>
                  <NListItem v-for="(r, idx) in risk.reasons" :key="idx">
                    <NThing description-style="font-size: var(--fs-sm)">
                      <template #description>
                        <span style="color: var(--text-secondary)">· {{ r }}</span>
                      </template>
                    </NThing>
                  </NListItem>
                </NList>
                <NEmpty
                  v-else
                  description="暂无显著风险触发项"
                  size="small"
                  style="padding: 8px 0"
                />
              </NSpace>
            </NGridItem>
          </NGrid>
        </NCard>

        <!-- 三块概览 -->
        <NGrid :cols="3" :x-gap="16" :y-gap="16" responsive="screen" style="margin-bottom: 16px">
          <NGridItem>
            <NCard size="small" :bordered="false">
              <template #header>
                <NSpace align="center" :size="6">
                  <strong>舆情仿真</strong>
                  <NTag
                    v-if="snapshot.simulation?.kg_linked"
                    size="tiny"
                    round
                    type="success"
                    :bordered="false"
                  >
                    KG
                  </NTag>
                </NSpace>
              </template>
              <template #header-extra>
                <NButton
                  v-if="snapshot.simulation"
                  size="tiny"
                  tertiary
                  @click="openRun('simulation', snapshot.simulation.job_id)"
                >
                  打开 Run
                </NButton>
              </template>
              <template v-if="snapshot.simulation">
                <NSpace vertical :size="8">
                  <NStatistic
                    label="抵制率（终轮）"
                    :value="fmtPct(snapshot.simulation.last_round.boycott_rate)"
                  />
                  <NSpace :size="6" wrap>
                    <NTag size="small" round
                      >平均情感 {{ fmtNum(snapshot.simulation.last_round.avg_sentiment) }}</NTag
                    >
                    <NTag size="small" round
                      >购买率 {{ fmtPct(snapshot.simulation.last_round.purchase_rate) }}</NTag
                    >
                    <NTag size="small" round
                      >Agents · {{ snapshot.simulation.config.num_agents ?? '—' }}</NTag
                    >
                    <NTag size="small" round>Rounds · {{ snapshot.simulation.rounds_total }}</NTag>
                  </NSpace>
                  <NSpace
                    v-if="snapshot.simulation.evidence_ids.length"
                    :size="4"
                    wrap
                    class="evidence-row"
                  >
                    <span class="label-muted">证据：</span>
                    <NTag
                      v-for="ev in snapshot.simulation.evidence_ids.slice(0, 4)"
                      :key="ev"
                      size="tiny"
                      round
                      type="info"
                      >{{ ev }}</NTag
                    >
                    <NTag
                      v-if="snapshot.simulation.evidence_ids.length > 4"
                      size="tiny"
                      round
                      :bordered="false"
                      >+{{ snapshot.simulation.evidence_ids.length - 4 }}</NTag
                    >
                  </NSpace>
                </NSpace>
              </template>
              <NEmpty v-else size="small" description="未跑过仿真" />
            </NCard>
          </NGridItem>

          <NGridItem>
            <NCard size="small" :bordered="false">
              <template #header>
                <NSpace align="center" :size="6">
                  <strong>预测拟合</strong>
                  <NTag
                    v-if="snapshot.forecast?.kg_linked"
                    size="tiny"
                    round
                    type="success"
                    :bordered="false"
                  >
                    KG
                  </NTag>
                </NSpace>
              </template>
              <template #header-extra>
                <NButton
                  v-if="snapshot.forecast"
                  size="tiny"
                  tertiary
                  @click="openRun('forecast', snapshot.forecast.run_id)"
                >
                  打开 Run
                </NButton>
              </template>
              <template v-if="snapshot.forecast">
                <NSpace vertical :size="8">
                  <NStatistic
                    :label="`窗内变化 · ${snapshot.forecast.metric_label}`"
                    :value="fmtPct(snapshot.forecast.delta_relative)"
                  />
                  <NTooltip>
                    <template #trigger>
                      <span class="forecast-headline">{{ snapshot.forecast.headline }}</span>
                    </template>
                    解释器输出 · 用于决策依据
                  </NTooltip>
                  <NSpace :size="6" wrap>
                    <NTag size="small" round
                      >MAPE {{ fmtPct(snapshot.forecast.diagnostics.mape) }}</NTag
                    >
                    <NTag size="small" round
                      >R² {{ fmtNum(snapshot.forecast.diagnostics.r2) }}</NTag
                    >
                    <NTag
                      v-if="snapshot.forecast.confidence?.band_level !== undefined"
                      size="small"
                      round
                      type="info"
                      >Band {{ fmtPct(snapshot.forecast.confidence.band_level, 0) }}</NTag
                    >
                    <NTag
                      v-if="snapshot.forecast.confidence?.reliability !== undefined"
                      size="small"
                      round
                      type="success"
                      >可靠度 {{ fmtPct(snapshot.forecast.confidence.reliability) }}</NTag
                    >
                    <NTag
                      v-for="flag in snapshot.forecast.risk_flags"
                      :key="flag"
                      size="small"
                      type="warning"
                      round
                      >{{ flag }}</NTag
                    >
                  </NSpace>
                  <NSpace
                    v-if="snapshot.forecast.coverage?.observed_days !== undefined"
                    :size="4"
                    wrap
                    class="evidence-row"
                  >
                    <span class="label-muted">数据覆盖：</span>
                    <NTag size="tiny" round :bordered="false">
                      观测 {{ fmtCount(snapshot.forecast.coverage.observed_days) }} /
                      {{ fmtCount(snapshot.forecast.coverage.total_days) }} 天 ·
                      {{ fmtPct(snapshot.forecast.coverage.observed_ratio) }}
                    </NTag>
                  </NSpace>
                </NSpace>
              </template>
              <NEmpty v-else size="small" description="未生成预测" />
            </NCard>
          </NGridItem>

          <NGridItem>
            <NCard size="small" :bordered="false">
              <template #header>
                <NSpace align="center" :size="6">
                  <strong>因果分析</strong>
                  <NTag
                    v-if="snapshot.causal?.kg_linked"
                    size="tiny"
                    round
                    type="success"
                    :bordered="false"
                  >
                    KG
                  </NTag>
                </NSpace>
              </template>
              <template #header-extra>
                <NButton
                  v-if="snapshot.causal"
                  size="tiny"
                  tertiary
                  @click="openRun('causal', snapshot.causal.run_id)"
                >
                  打开 Run
                </NButton>
              </template>
              <template v-if="snapshot.causal && snapshot.causal.status === 'ok'">
                <NSpace vertical :size="8">
                  <NStatistic
                    label="干预后相对效应"
                    :value="fmtPct(snapshot.causal.ate_relative)"
                  />
                  <NSpace :size="6" wrap>
                    <NTag size="small" round>ATE {{ fmtNum(snapshot.causal.ate, 4) }}</NTag>
                    <NTag size="small" round>p {{ fmtNum(snapshot.causal.p_value, 3) }}</NTag>
                    <NTag
                      v-if="snapshot.causal.confidence?.reliability !== undefined"
                      size="small"
                      round
                      type="success"
                      >可靠度 {{ fmtPct(snapshot.causal.confidence.reliability) }}</NTag
                    >
                    <NTag
                      v-if="snapshot.causal.narrative_seed.significant"
                      size="small"
                      :type="
                        snapshot.causal.narrative_seed.direction === 'down' ? 'error' : 'success'
                      "
                      round
                      >显著 ·
                      {{
                        snapshot.causal.narrative_seed.direction === 'down'
                          ? '负向'
                          : snapshot.causal.narrative_seed.direction === 'up'
                            ? '正向'
                            : '稳定'
                      }}</NTag
                    >
                    <NTag v-else size="small" round>未达显著</NTag>
                  </NSpace>
                  <NSpace
                    v-if="snapshot.causal.coverage?.pre_days !== undefined"
                    :size="4"
                    wrap
                    class="evidence-row"
                  >
                    <span class="label-muted">前后窗：</span>
                    <NTag size="tiny" round :bordered="false">
                      干预前 {{ fmtCount(snapshot.causal.coverage.pre_days) }} 天 / 干预后
                      {{ fmtCount(snapshot.causal.coverage.post_days) }} 天
                    </NTag>
                  </NSpace>
                </NSpace>
              </template>
              <NEmpty
                v-else
                size="small"
                :description="
                  snapshot.causal ? `因果状态：${snapshot.causal.status}` : '未运行因果分析'
                "
              />
            </NCard>
          </NGridItem>
        </NGrid>

        <!-- 证据链 + 置信度 + 图谱特征 -->
        <NCard
          :bordered="false"
          size="small"
          style="margin-bottom: 16px"
          content-style="padding: 16px 18px"
        >
          <template #header>
            <NSpace align="center" :size="6">
              <NIcon :component="ShieldCheckmarkOutline" />
              <strong>证据链与置信度</strong>
            </NSpace>
          </template>
          <NGrid :cols="3" :x-gap="20" :y-gap="12" responsive="screen">
            <NGridItem>
              <NSpace vertical :size="6">
                <span class="label-muted">最弱链可靠度</span>
                <NTag :type="reliabilityColor" round size="large">
                  {{ reliability === null ? '—' : fmtPct(reliability) }}
                </NTag>
                <NSpace :size="6" wrap>
                  <NTag
                    v-if="confidenceRollup.forecast?.reliability !== undefined"
                    size="tiny"
                    round
                    >预测 {{ fmtPct(confidenceRollup.forecast.reliability) }}</NTag
                  >
                  <NTag v-if="confidenceRollup.causal?.reliability !== undefined" size="tiny" round
                    >因果 {{ fmtPct(confidenceRollup.causal.reliability) }}</NTag
                  >
                </NSpace>
              </NSpace>
            </NGridItem>
            <NGridItem>
              <NSpace vertical :size="6">
                <span class="label-muted">
                  <NIcon :component="LayersOutline" /> 证据数量：
                  {{ evidenceIds.length }}
                </span>
                <NSpace :size="4" wrap>
                  <NTag
                    v-for="ev in sampleEvidence"
                    :key="ev"
                    size="tiny"
                    round
                    type="info"
                    :bordered="false"
                    >{{ ev }}</NTag
                  >
                  <NTag
                    v-if="evidenceIds.length > sampleEvidence.length"
                    size="tiny"
                    round
                    :bordered="false"
                    >+{{ evidenceIds.length - sampleEvidence.length }}</NTag
                  >
                  <NEmpty v-if="!evidenceIds.length" size="small" description="暂无证据 id" />
                </NSpace>
              </NSpace>
            </NGridItem>
            <NGridItem>
              <NSpace vertical :size="6">
                <span class="label-muted"> <NIcon :component="GitNetworkOutline" /> 图谱特征 </span>
                <NSpace :size="4" wrap>
                  <NTag
                    v-for="row in kgFeatureRows"
                    :key="row.key"
                    size="tiny"
                    round
                    :bordered="false"
                  >
                    {{ row.label }} {{ row.value }}
                  </NTag>
                  <NEmpty v-if="!kgFeatureRows.length" size="small" description="未链接知识图谱" />
                </NSpace>
              </NSpace>
            </NGridItem>
          </NGrid>
        </NCard>

        <!-- 行动建议 -->
        <NCard title="决策建议" :bordered="false" size="small">
          <NEmpty v-if="!recommendations.length" size="small" description="暂无可执行建议" />
          <NList v-else hoverable>
            <NListItem v-for="rec in recommendations" :key="rec.id">
              <NThing>
                <template #header>
                  <NSpace align="center" :size="8">
                    <NTag :type="priorityType(rec.priority)" size="small" round>
                      {{ priorityLabel(rec.priority) }}
                    </NTag>
                    <strong>{{ rec.title }}</strong>
                  </NSpace>
                </template>
                <template #description>
                  <span style="color: var(--text-secondary); font-size: var(--fs-sm)">
                    {{ rec.rationale }}
                  </span>
                </template>
                <template #footer>
                  <NSpace vertical :size="4">
                    <NSpace :size="6" wrap>
                      <NTag
                        v-for="t in rec.tags"
                        :key="t"
                        size="tiny"
                        round
                        :bordered="false"
                        style="background: var(--bg-tag, rgba(91, 141, 239, 0.08))"
                        >#{{ t }}</NTag
                      >
                    </NSpace>
                    <NSpace v-if="recSourceRuns(rec).length" :size="6" wrap>
                      <span class="label-muted">来源 Run：</span>
                      <NTag
                        v-for="src in recSourceRuns(rec)"
                        :key="src.kind"
                        size="tiny"
                        round
                        type="info"
                        checkable
                        role="button"
                        tabindex="0"
                        :aria-label="`打开${SOURCE_LABEL[src.kind]} Run ${src.runId}`"
                        style="cursor: pointer"
                        @click="openRun(src.kind, src.runId)"
                        @keydown.enter.prevent="openRun(src.kind, src.runId)"
                        @keydown.space.prevent="openRun(src.kind, src.runId)"
                      >
                        {{ SOURCE_LABEL[src.kind] }} · {{ src.runId.slice(0, 8) }}
                      </NTag>
                    </NSpace>
                    <NSpace v-if="recMetricEntries(rec).length" :size="6" wrap>
                      <span class="label-muted">指标依据：</span>
                      <NTag
                        v-for="m in recMetricEntries(rec)"
                        :key="m.key"
                        size="tiny"
                        round
                        :bordered="false"
                        >{{ m.key }} = {{ m.value }}</NTag
                      >
                    </NSpace>
                    <NSpace v-if="rec.evidence.length" :size="6" wrap>
                      <span class="label-muted">证据：</span>
                      <NTag v-for="ev in rec.evidence" :key="ev" size="tiny" round type="info">{{
                        ev
                      }}</NTag>
                    </NSpace>
                  </NSpace>
                </template>
              </NThing>
            </NListItem>
          </NList>
        </NCard>
      </template>
    </NSpin>
  </div>
</template>

<style scoped>
.decision-board {
  width: 100%;
}
.label-muted {
  color: var(--text-muted);
  font-size: var(--fs-sm);
}
.evidence-row {
  align-items: center;
}
.risk-score-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.risk-score-num {
  font-size: 44px;
  font-weight: 600;
  letter-spacing: -0.02em;
  line-height: 1;
}
.risk-score-num--low {
  color: var(--color-accent, #00e5a8);
}
.risk-score-num--elevated {
  color: var(--color-warn, #f5a524);
}
.risk-score-num--high {
  color: var(--color-danger, #ef4444);
}
.risk-score-suffix {
  color: var(--text-muted);
  font-size: var(--fs-sm);
}
.forecast-headline {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}
</style>
