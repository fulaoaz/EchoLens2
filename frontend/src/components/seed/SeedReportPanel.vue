<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import {
  NCard,
  NEmpty,
  NSpace,
  NSpin,
  NTag,
  NButton,
  NIcon,
  NGrid,
  NGridItem,
  NList,
  NListItem,
  NThing,
  NDivider,
  NAlert,
  useMessage,
} from 'naive-ui'
import {
  CloudUploadOutline,
  PeopleOutline,
  PricetagsOutline,
  ChatbubblesOutline,
  ShareSocialOutline,
  RefreshOutline,
  TrendingUpOutline,
} from '@vicons/ionicons5'
import * as echarts from 'echarts/core'
import { LineChart, PieChart, BarChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DatasetComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'

import KpiCard from '@/components/common/KpiCard.vue'
import { projectsApi, type SeedDataInput, type SeedReport } from '@/api/projects'

echarts.use([
  LineChart,
  PieChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DatasetComponent,
  CanvasRenderer,
])

const props = defineProps<{ projectId: string }>()
const message = useMessage()

const report = ref<SeedReport | null>(null)
const loading = ref(false)
const ingesting = ref(false)
const errorText = ref<string | null>(null)

const sentimentEl = ref<HTMLDivElement | null>(null)
const timelineEl = ref<HTMLDivElement | null>(null)
const priceEl = ref<HTMLDivElement | null>(null)
let sentimentChart: echarts.ECharts | null = null
let timelineChart: echarts.ECharts | null = null
let priceChart: echarts.ECharts | null = null

const SENTIMENT_PALETTE: Record<string, string> = {
  positive: '#00E5A8',
  negative: '#F87171',
  neutral: '#94A3B8',
  mixed: '#FBBF24',
  unknown: '#475569',
}

const SENTIMENT_LABEL: Record<string, string> = {
  positive: '正面',
  negative: '负面',
  neutral: '中性',
  mixed: '混合',
  unknown: '未知',
}

const hasData = computed(() => {
  if (!report.value) return false
  const c = report.value.counts
  return c.products + c.reviews + c.posts > 0
})

const totalKols = computed(() => report.value?.top_kols.length ?? 0)

async function load(): Promise<void> {
  loading.value = true
  errorText.value = null
  try {
    report.value = await projectsApi.getSeedReport(props.projectId)
  } catch (e) {
    errorText.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

async function injectDemo(): Promise<void> {
  ingesting.value = true
  try {
    await projectsApi.ingestSeedData(props.projectId, demoSeedPayload())
    message.success('已注入演示数据，正在刷新报告')
    await load()
  } catch (e) {
    message.error(`注入失败：${e instanceof Error ? e.message : String(e)}`)
  } finally {
    ingesting.value = false
  }
}

function demoSeedPayload(): SeedDataInput {
  const day = (offset: number) => {
    const d = new Date()
    d.setDate(d.getDate() - offset)
    return d.toISOString().slice(0, 10)
  }
  return {
    products: [
      {
        platform: 'jd',
        id: 'jd:demo-1',
        title: 'Anker 737 移动电源 官方旗舰店',
        brand: 'Anker',
        price_current: 599,
        crawled_at: new Date().toISOString(),
      },
      {
        platform: 'taobao',
        id: 'tb:demo-1',
        title: 'Anker 737 移动电源 正品包邮',
        brand: 'Anker',
        price_current: 549,
        crawled_at: new Date().toISOString(),
      },
      {
        platform: 'jd',
        id: 'jd:demo-2',
        title: '罗技 G502 鼠标',
        brand: 'Logitech',
        price_current: 399,
        crawled_at: new Date().toISOString(),
      },
    ],
    reviews: [
      { platform: 'jd', id: 'r1', content: '续航很好', sentiment: 'positive' },
      { platform: 'jd', id: 'r2', content: '充电速度快', sentiment: 'positive' },
      { platform: 'jd', id: 'r3', content: '外壳掉漆', sentiment: 'negative' },
      { platform: 'jd', id: 'r4', content: '一般般', sentiment: 'neutral' },
    ],
    posts: [
      {
        platform: 'weibo',
        id: 'w1',
        author_hash: 'kol_alice_aaaaaa',
        content: '试用感受：很顶 #移动电源',
        sentiment: 'positive',
        posted_at: `${day(2)}T10:00:00`,
      },
      {
        platform: 'weibo',
        id: 'w2',
        author_hash: 'kol_alice_aaaaaa',
        content: '续测一周：稳',
        sentiment: 'positive',
        posted_at: `${day(1)}T09:00:00`,
      },
      {
        platform: 'xhs',
        id: 'x1',
        author_hash: 'kol_bob_bbbbbb',
        content: '拔草帖：发热严重',
        sentiment: 'negative',
        posted_at: `${day(1)}T18:00:00`,
      },
    ],
  }
}

function makeSentimentOption(): EChartsOption {
  const dist = report.value?.review_sentiment_distribution ?? {}
  const data = Object.entries(dist).map(([k, v]) => ({
    name: SENTIMENT_LABEL[k] ?? k,
    value: v,
    itemStyle: { color: SENTIMENT_PALETTE[k] ?? '#5B8DEF' },
  }))
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: {
      orient: 'horizontal',
      bottom: 0,
      textStyle: { color: '#CBD5E1' },
    },
    series: [
      {
        type: 'pie',
        radius: ['52%', '76%'],
        center: ['50%', '46%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: 'var(--bg-card)', borderWidth: 2 },
        label: { show: false },
        labelLine: { show: false },
        data: data.length
          ? data
          : [{ name: '暂无评论', value: 1, itemStyle: { color: '#475569' } }],
      },
    ],
  }
}

function makeTimelineOption(): EChartsOption {
  const buckets = report.value?.sentiment_volume_timeline ?? []
  const days = Array.from(new Set(buckets.map((b) => b.date))).sort()
  const sentiments = Array.from(new Set(buckets.map((b) => b.sentiment)))
  const series = sentiments.map((s) => ({
    name: SENTIMENT_LABEL[s] ?? s,
    type: 'line' as const,
    smooth: true,
    symbolSize: 6,
    lineStyle: { width: 2, color: SENTIMENT_PALETTE[s] ?? '#5B8DEF' },
    itemStyle: { color: SENTIMENT_PALETTE[s] ?? '#5B8DEF' },
    areaStyle: { opacity: 0.18, color: SENTIMENT_PALETTE[s] ?? '#5B8DEF' },
    data: days.map((d) => buckets.find((b) => b.date === d && b.sentiment === s)?.count ?? 0),
  }))
  return {
    backgroundColor: 'transparent',
    grid: { left: 40, right: 16, top: 36, bottom: 28 },
    tooltip: { trigger: 'axis' },
    legend: { textStyle: { color: '#CBD5E1' }, top: 0 },
    xAxis: {
      type: 'category',
      data: days,
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

function makePriceOption(): EChartsOption {
  const products = report.value?.products ?? []
  const groups = report.value?.cross_platform_groups ?? {}
  const productById = new Map(products.map((p) => [p.id ?? '', p]))

  const categories: string[] = []
  const seriesData: Array<{
    value: [string, number]
    platform: string
  }> = []

  for (const [groupKey, ids] of Object.entries(groups)) {
    const groupName = groupKey.split('|').slice(1).join(' ').trim() || groupKey
    categories.push(groupName)
    for (const id of ids) {
      const p = productById.get(id)
      if (p && typeof p.price_current === 'number') {
        seriesData.push({
          value: [groupName, p.price_current],
          platform: p.platform ?? '?',
        })
      }
    }
  }

  return {
    backgroundColor: 'transparent',
    grid: { left: 80, right: 24, top: 36, bottom: 28 },
    tooltip: {
      trigger: 'item',
      formatter: (p) => {
        const param = p as unknown as { data: { value: [string, number]; platform: string } }
        return `${param.data.value[0]}<br/>${param.data.platform}: ¥${param.data.value[1]}`
      },
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLine: { lineStyle: { color: 'rgba(91,141,239,0.3)' } },
      axisLabel: { color: '#94A3B8', interval: 0, rotate: categories.length > 4 ? 25 : 0 },
    },
    yAxis: {
      type: 'value',
      name: '价格 (¥)',
      nameTextStyle: { color: '#94A3B8' },
      splitLine: { lineStyle: { color: 'rgba(91,141,239,0.1)' } },
      axisLabel: { color: '#94A3B8' },
    },
    series: [
      {
        type: 'scatter',
        symbolSize: 16,
        data: seriesData,
        itemStyle: {
          color: '#5B8DEF',
          borderColor: '#fff',
          borderWidth: 1,
          opacity: 0.9,
        },
      },
    ],
  }
}

function renderCharts(): void {
  if (!report.value) return
  if (sentimentEl.value) {
    sentimentChart ??= echarts.init(sentimentEl.value, undefined, { renderer: 'canvas' })
    sentimentChart.setOption(makeSentimentOption())
  }
  if (timelineEl.value) {
    timelineChart ??= echarts.init(timelineEl.value, undefined, { renderer: 'canvas' })
    timelineChart.setOption(makeTimelineOption(), true)
  }
  if (priceEl.value) {
    priceChart ??= echarts.init(priceEl.value, undefined, { renderer: 'canvas' })
    priceChart.setOption(makePriceOption(), true)
  }
}

function disposeCharts(): void {
  sentimentChart?.dispose()
  timelineChart?.dispose()
  priceChart?.dispose()
  sentimentChart = timelineChart = priceChart = null
}

function handleResize(): void {
  sentimentChart?.resize()
  timelineChart?.resize()
  priceChart?.resize()
}

watch(report, () => {
  // Wait for v-if blocks to mount the chart divs.
  setTimeout(renderCharts, 16)
})

onMounted(() => {
  load()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  disposeCharts()
})
</script>

<template>
  <NSpin :show="loading">
    <NAlert v-if="errorText" type="error" closable style="margin-bottom: 16px">
      {{ errorText }}
    </NAlert>

    <NCard v-if="!hasData" :bordered="false">
      <NEmpty description="尚无种子数据。注入演示数据快速预览，或等待爬虫流水线产出真实记录。">
        <template #extra>
          <NSpace>
            <NButton type="primary" :loading="ingesting" @click="injectDemo">
              <template #icon><NIcon :component="CloudUploadOutline" /></template>
              注入演示数据
            </NButton>
            <NButton tertiary @click="load">
              <template #icon><NIcon :component="RefreshOutline" /></template>
              刷新
            </NButton>
          </NSpace>
        </template>
      </NEmpty>
    </NCard>

    <template v-else-if="report">
      <NSpace justify="space-between" align="center" style="margin-bottom: 16px">
        <div style="color: var(--text-muted); font-size: 13px">
          报告生成时间：{{ new Date(report.generated_at).toLocaleString('zh-CN') }}
        </div>
        <NSpace>
          <NButton tertiary size="small" :loading="ingesting" @click="injectDemo">
            <template #icon><NIcon :component="CloudUploadOutline" /></template>
            追加演示数据
          </NButton>
          <NButton tertiary size="small" @click="load">
            <template #icon><NIcon :component="RefreshOutline" /></template>
            刷新
          </NButton>
        </NSpace>
      </NSpace>

      <NCard :bordered="false" style="margin-bottom: 16px" content-style="padding: 18px 20px">
        <NSpace align="center">
          <NIcon :component="TrendingUpOutline" :size="22" color="var(--color-primary)" />
          <strong style="font-size: 15px">{{ report.summary_text }}</strong>
        </NSpace>
      </NCard>

      <NGrid :cols="4" :x-gap="16" :y-gap="16" responsive="screen" style="margin-bottom: 20px">
        <NGridItem>
          <KpiCard label="商品数" :value="report.counts.products" accent="primary" />
        </NGridItem>
        <NGridItem>
          <KpiCard label="评论数" :value="report.counts.reviews" accent="accent" />
        </NGridItem>
        <NGridItem>
          <KpiCard label="社交贴文" :value="report.counts.posts" accent="warn" />
        </NGridItem>
        <NGridItem>
          <KpiCard
            label="跨平台撞品"
            :value="report.counts.cross_platform_groups"
            accent="danger"
          />
        </NGridItem>
      </NGrid>

      <NGrid :cols="2" :x-gap="16" :y-gap="16" responsive="screen">
        <NGridItem>
          <NCard :bordered="false" content-style="padding: 12px 12px 16px">
            <template #header>
              <NSpace align="center">
                <NIcon :component="ChatbubblesOutline" />
                评论情感分布
              </NSpace>
            </template>
            <div ref="sentimentEl" class="sr-chart sr-chart--sm" />
          </NCard>
        </NGridItem>
        <NGridItem>
          <NCard :bordered="false" content-style="padding: 12px 12px 16px">
            <template #header>
              <NSpace align="center">
                <NIcon :component="ShareSocialOutline" />
                舆情声量时间线
              </NSpace>
            </template>
            <div ref="timelineEl" class="sr-chart sr-chart--sm" />
          </NCard>
        </NGridItem>
        <NGridItem>
          <NCard :bordered="false" content-style="padding: 12px 12px 16px">
            <template #header>
              <NSpace align="center">
                <NIcon :component="PricetagsOutline" />
                跨平台同款价格
              </NSpace>
            </template>
            <div
              v-if="report.counts.cross_platform_groups > 0"
              ref="priceEl"
              class="sr-chart sr-chart--sm"
            />
            <NEmpty
              v-else
              size="small"
              description="尚未识别到跨平台同款商品"
              style="padding: 20px 0"
            />
          </NCard>
        </NGridItem>
        <NGridItem>
          <NCard :bordered="false" content-style="padding: 6px 0 0">
            <template #header>
              <NSpace align="center" justify="space-between">
                <NSpace align="center">
                  <NIcon :component="PeopleOutline" />
                  Top KOL（按贴文数）
                </NSpace>
                <NTag size="small" round>共 {{ totalKols }} 位</NTag>
              </NSpace>
            </template>
            <NEmpty
              v-if="totalKols === 0"
              size="small"
              description="尚无 KOL 数据"
              style="padding: 32px 0"
            />
            <NList v-else hoverable clickable :show-divider="false">
              <NListItem v-for="kol in report.top_kols.slice(0, 8)" :key="kol.author_hash">
                <NThing>
                  <template #header>
                    <span style="font-family: var(--font-mono); font-size: 13px">
                      {{ kol.author_hash }}
                    </span>
                  </template>
                  <template #description>
                    <NTag :bordered="false" size="small" type="info" round>
                      贴文 × {{ kol.post_count }}
                    </NTag>
                  </template>
                </NThing>
              </NListItem>
            </NList>
          </NCard>
        </NGridItem>
      </NGrid>

      <NDivider style="margin: 24px 0 16px" />

      <NCard
        v-if="report.products.length"
        :bordered="false"
        title="商品采样"
        content-style="padding: 0"
      >
        <NList hoverable :show-divider="false">
          <NListItem v-for="p in report.products.slice(0, 10)" :key="p.id ?? p.title">
            <NThing>
              <template #header>{{ p.title || '(未命名商品)' }}</template>
              <template #description>
                <NSpace size="small">
                  <NTag size="small" round>{{ p.platform || '?' }}</NTag>
                  <NTag v-if="p.brand" size="small" round type="info">{{ p.brand }}</NTag>
                  <NTag
                    v-if="typeof p.price_current === 'number'"
                    size="small"
                    round
                    type="success"
                  >
                    ¥{{ p.price_current.toFixed(0) }}
                  </NTag>
                </NSpace>
              </template>
            </NThing>
          </NListItem>
        </NList>
      </NCard>
    </template>
  </NSpin>
</template>

<style scoped>
.sr-chart {
  width: 100%;
  height: 280px;
}
.sr-chart--sm {
  height: 240px;
}
</style>
