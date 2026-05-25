<script setup lang="ts">
import { NCard, NEmpty } from 'naive-ui'
/**
 * Placeholder for AntV G6 social-network graph wrapper.
 * Actual G6 instantiation will be wired in Milestone 2 to avoid bundling
 * the (large) G6 runtime in the M0 scaffold smoke build.
 */
</script>

<template>
  <NCard title="仿真传播网络" :bordered="false" class="network-graph">
    <div class="network-graph__canvas">
      <NEmpty description="启动仿真后，此处将渲染 1k+ Agent 的传播网络（G6）" />
    </div>
  </NCard>
</template>

<style scoped>
.network-graph__canvas {
  height: 360px;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(60% 60% at 50% 40%, rgba(91, 141, 239, 0.12), transparent 70%),
    var(--bg-elevated);
  border-radius: var(--radius-md);
  border: 1px dashed var(--border);
}
</style>
