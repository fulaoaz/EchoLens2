<script setup lang="ts">
import KpiCard from '@/components/common/KpiCard.vue'

interface Tile {
  key: string
  label: string
  value: number | string
  unit?: string
  delta?: number
  trend?: 'up' | 'down' | 'flat'
  accent?: 'primary' | 'accent' | 'warn' | 'danger'
}

interface Props {
  tiles?: Tile[]
}

const defaults: Tile[] = [
  { key: 'gmv', label: '7 日 GMV 预测', value: 4823, unit: '万元', delta: 12.4, trend: 'up' },
  {
    key: 'risk',
    label: '风险预警分',
    value: 18,
    unit: '/100',
    delta: -3.2,
    trend: 'down',
    accent: 'warn',
  },
  {
    key: 'sim',
    label: '仿真转化率',
    value: '23.6',
    unit: '%',
    delta: 5.1,
    trend: 'up',
    accent: 'accent',
  },
  { key: 'top', label: 'Top 行动建议', value: 5, unit: '条', accent: 'primary' },
]

const props = withDefaults(defineProps<Props>(), {
  tiles: () => defaults,
})
</script>

<template>
  <div class="kpi-grid">
    <KpiCard
      v-for="t in props.tiles"
      :key="t.key"
      :label="t.label"
      :value="t.value"
      :unit="t.unit"
      :delta="t.delta"
      :trend="t.trend"
      :accent="t.accent"
    />
  </div>
</template>

<style scoped>
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}
</style>
