<script setup lang="ts">
import { NSkeleton } from 'naive-ui'

interface Props {
  rows?: number
  height?: string
}
withDefaults(defineProps<Props>(), { rows: 3, height: '20px' })
</script>

<template>
  <div class="skeleton-stack">
    <NSkeleton v-for="i in rows" :key="i" :height="height" :sharp="false" round animated />
  </div>
</template>

<style scoped>
.skeleton-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 0;
}
</style>
