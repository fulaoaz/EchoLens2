<script setup lang="ts">
import { computed } from 'vue'
import { NCard, NStatistic, NTag } from 'naive-ui'

interface Props {
  label: string
  value: number | string
  unit?: string
  delta?: number
  trend?: 'up' | 'down' | 'flat'
  accent?: 'primary' | 'accent' | 'warn' | 'danger'
}

const props = withDefaults(defineProps<Props>(), {
  unit: '',
  delta: undefined,
  trend: 'flat',
  accent: 'primary',
})

const accentColor = computed(() => {
  switch (props.accent) {
    case 'accent':
      return 'var(--color-accent)'
    case 'warn':
      return 'var(--color-warn)'
    case 'danger':
      return 'var(--color-danger)'
    default:
      return 'var(--color-primary)'
  }
})

const trendType = computed<'success' | 'error' | 'default'>(() => {
  if (props.trend === 'up') return 'success'
  if (props.trend === 'down') return 'error'
  return 'default'
})

const trendArrow = computed(() => {
  if (props.trend === 'up') return '▲'
  if (props.trend === 'down') return '▼'
  return '·'
})
</script>

<template>
  <NCard class="kpi-card" :bordered="false" content-style="padding: 18px 20px;">
    <div class="kpi-card__row">
      <div class="kpi-card__label">{{ label }}</div>
      <NTag v-if="delta !== undefined" :type="trendType" size="small" round>
        {{ trendArrow }} {{ Math.abs(delta).toFixed(1) }}%
      </NTag>
    </div>
    <NStatistic :value="value">
      <template #suffix>
        <span class="kpi-card__unit">{{ unit }}</span>
      </template>
    </NStatistic>
    <div class="kpi-card__glow" />
  </NCard>
</template>

<style scoped>
.kpi-card {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background:
    linear-gradient(135deg, rgba(91, 141, 239, 0.08), rgba(0, 229, 168, 0.04)), var(--bg-card);
  transition:
    transform var(--motion-base),
    box-shadow var(--motion-base);
}
.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-card-hover);
}
.kpi-card__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.kpi-card__label {
  font-size: var(--fs-sm);
  color: var(--text-muted);
  letter-spacing: 0.02em;
}
.kpi-card__unit {
  margin-left: 4px;
  font-size: var(--fs-sm);
  color: var(--text-muted);
}
.kpi-card__glow {
  position: absolute;
  inset: -40% -40% auto auto;
  width: 160px;
  height: 160px;
  pointer-events: none;
  background: radial-gradient(closest-side, v-bind(accentColor), transparent 70%);
  opacity: 0.18;
}
</style>
