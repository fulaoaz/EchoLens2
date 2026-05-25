<script setup lang="ts">
import { ref } from 'vue'
import { NDataTable, NTag } from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'

interface AgentRow {
  id: string
  persona: string
  platform: string
  action: '购买' | '观望' | '差评' | '转发'
  sentiment: number
}

const rows = ref<AgentRow[]>([
  { id: 'A-0042', persona: '95后/学生党', platform: '小红书', action: '转发', sentiment: 0.62 },
  { id: 'A-0118', persona: '都市白领', platform: '京东', action: '购买', sentiment: 0.81 },
  { id: 'A-0257', persona: '宝妈', platform: '淘宝', action: '观望', sentiment: 0.41 },
  { id: 'A-0388', persona: '中年男性', platform: '微博', action: '差评', sentiment: -0.12 },
])

const columns: DataTableColumns<AgentRow> = [
  { title: 'ID', key: 'id', width: 92, render: (r) => h('span', { class: 'mono' }, r.id) },
  { title: '画像', key: 'persona' },
  { title: '平台', key: 'platform', width: 100 },
  {
    title: '动作',
    key: 'action',
    width: 100,
    render: (r) =>
      h(
        NTag,
        {
          size: 'small',
          round: true,
          type:
            r.action === '购买'
              ? 'success'
              : r.action === '差评'
                ? 'error'
                : r.action === '转发'
                  ? 'info'
                  : 'default',
        },
        () => r.action,
      ),
  },
  {
    title: '情感',
    key: 'sentiment',
    width: 100,
    render: (r) =>
      h('span', { class: 'mono', style: { color: r.sentiment >= 0 ? '#00E5A8' : '#FF6B6B' } }, [
        r.sentiment.toFixed(2),
      ]),
  },
]

import { h } from 'vue'
</script>

<template>
  <NDataTable :columns="columns" :data="rows" :pagination="false" size="small" />
</template>
