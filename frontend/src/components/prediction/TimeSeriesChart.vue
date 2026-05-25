<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { NCard } from 'naive-ui'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  MarkAreaComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'

echarts.use([
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  MarkAreaComponent,
  CanvasRenderer,
])

interface Props {
  metric?: string
}
const props = withDefaults(defineProps<Props>(), { metric: 'GMV 预测 (¥万元)' })

const el = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

function makeOption(): EChartsOption {
  const days = Array.from({ length: 30 }, (_, i) => `D+${i + 1}`)
  const yhat = days.map((_, i) => Number((120 + i * 4 + Math.sin(i / 3) * 10).toFixed(1)))
  const upper = yhat.map((v) => Number((v * 1.12).toFixed(1)))
  const lower = yhat.map((v) => Number((v * 0.9).toFixed(1)))

  return {
    backgroundColor: 'transparent',
    grid: { left: 40, right: 16, top: 32, bottom: 28 },
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
      name: props.metric,
      nameTextStyle: { color: '#94A3B8' },
      splitLine: { lineStyle: { color: 'rgba(91,141,239,0.1)' } },
      axisLabel: { color: '#94A3B8' },
    },
    series: [
      {
        name: '95% 上限',
        type: 'line',
        data: upper,
        lineStyle: { width: 0 },
        symbol: 'none',
        stack: 'band',
      },
      {
        name: '95% 下限',
        type: 'line',
        data: lower.map((l, i) => upper[i] - l),
        lineStyle: { width: 0 },
        areaStyle: { color: 'rgba(91, 141, 239, 0.18)' },
        symbol: 'none',
        stack: 'band',
      },
      {
        name: '预测',
        type: 'line',
        data: yhat,
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { color: '#5B8DEF', width: 2 },
        itemStyle: { color: '#5B8DEF' },
      },
    ],
  }
}

function render() {
  if (!el.value) return
  if (!chart) chart = echarts.init(el.value, undefined, { renderer: 'canvas' })
  chart.setOption(makeOption())
}

onMounted(() => {
  render()
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
  chart = null
})

function resize() {
  chart?.resize()
}

watch(() => props.metric, render)
</script>

<template>
  <NCard :bordered="false" :title="metric" content-style="padding: 8px 8px 0;">
    <div ref="el" class="ts-chart" />
  </NCard>
</template>

<style scoped>
.ts-chart {
  width: 100%;
  height: 320px;
}
</style>
