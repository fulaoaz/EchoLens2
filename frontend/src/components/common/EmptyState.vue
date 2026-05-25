<script setup lang="ts">
import { NEmpty, NButton } from 'naive-ui'

interface Props {
  title?: string
  description?: string
  ctaLabel?: string
}

withDefaults(defineProps<Props>(), {
  title: '暂无数据',
  description: '当前视图还没有可用数据，请先创建项目或运行任务。',
  ctaLabel: '',
})

defineEmits<{ (e: 'cta'): void }>()
</script>

<template>
  <div class="empty-state">
    <NEmpty :description="title">
      <template #default>
        <div class="empty-state__title">{{ title }}</div>
        <div class="empty-state__desc">{{ description }}</div>
      </template>
      <template v-if="ctaLabel" #extra>
        <NButton type="primary" ghost @click="$emit('cta')">{{ ctaLabel }}</NButton>
      </template>
    </NEmpty>
  </div>
</template>

<style scoped>
.empty-state {
  padding: 48px 24px;
  display: flex;
  justify-content: center;
}
.empty-state__title {
  color: var(--text-primary);
  font-size: var(--fs-md);
  font-weight: 500;
  margin-bottom: 6px;
}
.empty-state__desc {
  color: var(--text-muted);
  font-size: var(--fs-sm);
  max-width: 360px;
  text-align: center;
}
</style>
