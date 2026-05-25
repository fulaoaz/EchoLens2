<script setup lang="ts">
import { NCard, NEmpty } from 'naive-ui'
/**
 * Placeholder for d3-based causal DAG view.
 * Real DAG (DoWhy ↔ d3.hierarchy) wired in Milestone 3.
 */
</script>

<template>
  <NCard title="因果 DAG (反事实推演)" :bordered="false">
    <div class="causal-dag__panel">
      <NEmpty description="选择干预变量后将渲染因果有向图（d3）" />
    </div>
  </NCard>
</template>

<style scoped>
.causal-dag__panel {
  height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-elevated);
}
</style>
