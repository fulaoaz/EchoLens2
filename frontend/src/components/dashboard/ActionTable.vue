<script setup lang="ts">
import { h, ref } from 'vue'
import { NDataTable, NTag, NProgress } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'

interface ActionRow {
  id: string
  title: string
  expectedGmvLift: number
  riskScore: number
  tags: string[]
}

const data = ref<ActionRow[]>([
  {
    id: 'a1',
    title: '5/22 早 8 点开播 + 限时秒杀 200 件',
    expectedGmvLift: 18.4,
    riskScore: 22,
    tags: ['直播', '促销'],
  },
  {
    id: 'a2',
    title: '小红书种草投放预算上调至 12 万',
    expectedGmvLift: 11.2,
    riskScore: 14,
    tags: ['种草', '增投'],
  },
  {
    id: 'a3',
    title: '差评热词"包装"启动客服话术',
    expectedGmvLift: 4.7,
    riskScore: 9,
    tags: ['客服', '风险'],
  },
  {
    id: 'a4',
    title: '京东定价 -8% 与套装组合',
    expectedGmvLift: 9.1,
    riskScore: 31,
    tags: ['定价', '组合'],
  },
])

const columns: DataTableColumns<ActionRow> = [
  { title: '#', key: 'id', width: 56, render: (r) => h('span', { class: 'mono' }, r.id) },
  { title: '行动建议', key: 'title' },
  {
    title: '预期 GMV 增量',
    key: 'expectedGmvLift',
    width: 140,
    render: (r) =>
      h('span', { class: 'mono', style: { color: '#00E5A8' } }, `+${r.expectedGmvLift}%`),
  },
  {
    title: '风险分',
    key: 'riskScore',
    width: 140,
    render: (r) =>
      h(NProgress, {
        type: 'line',
        percentage: r.riskScore,
        showIndicator: true,
        height: 6,
        borderRadius: 4,
        status: r.riskScore > 25 ? 'warning' : 'info',
      }),
  },
  {
    title: '标签',
    key: 'tags',
    width: 200,
    render: (r) =>
      h(
        'div',
        { style: { display: 'flex', gap: '6px', flexWrap: 'wrap' } },
        r.tags.map((t) => h(NTag, { round: true, size: 'small', type: 'info' }, () => t)),
      ),
  },
]
</script>

<template>
  <NDataTable :columns="columns" :data="data" :bordered="false" size="small" />
</template>
