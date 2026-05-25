<script setup lang="ts">
import { NLog } from 'naive-ui'

const log = `[t=00:00] runner: bootstrap 1024 agents
[t=00:01] kg: load NetworkX subgraph (nodes=1024 edges=3812)
[t=00:02] agent A-0042 → action=转发 platform=小红书 weight=0.62
[t=00:03] agent A-0118 → action=购买 platform=京东 weight=0.81
[t=00:05] runner: round 1/30 complete  spread_rate=0.084
[t=00:08] llm: explain bucket "美妆/早C晚A" sentiment=+0.41
[t=00:12] runner: round 2/30 complete  spread_rate=0.121`
</script>

<template>
  <NLog :rows="12" :log="log" trim language="text" />
</template>
