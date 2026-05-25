<script setup lang="ts">
import { onErrorCaptured, ref } from 'vue'
import { NCard, NButton } from 'naive-ui'

const error = ref<Error | null>(null)
const info = ref('')

onErrorCaptured((err, _instance, hookInfo) => {
  error.value = err as Error
  info.value = hookInfo
  // Allow logging via console for dev visibility but do not propagate.
  // eslint-disable-next-line no-console
  console.error('[ErrorBoundary]', err, hookInfo)
  return false
})

function reset() {
  error.value = null
  info.value = ''
}
</script>

<template>
  <template v-if="error">
    <NCard class="error-boundary" title="组件渲染异常" :bordered="false">
      <p class="error-boundary__msg">{{ error.message || '未知错误' }}</p>
      <p v-if="info" class="error-boundary__info">{{ info }}</p>
      <NButton size="small" type="primary" ghost @click="reset">重试</NButton>
    </NCard>
  </template>
  <slot v-else />
</template>

<style scoped>
.error-boundary {
  border: 1px solid rgba(255, 107, 107, 0.4);
  background: rgba(255, 107, 107, 0.06);
}
.error-boundary__msg {
  color: var(--color-danger);
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  margin: 0 0 6px;
}
.error-boundary__info {
  color: var(--text-muted);
  font-size: var(--fs-xs);
  margin: 0 0 12px;
}
</style>
