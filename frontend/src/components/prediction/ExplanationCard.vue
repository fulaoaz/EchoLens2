<script setup lang="ts">
import { NCard, NTag, NSpace } from 'naive-ui'

interface Props {
  title?: string
  rationale?: string
  evidence?: string[]
}
withDefaults(defineProps<Props>(), {
  title: '预测归因',
  rationale:
    '近 14 日小红书"早 C 晚 A"种草内容增长 38%，叠加直播节奏调整，预测 GMV 在 D+7 出现 12% 上行拐点；置信区间已剔除节假日效应。',
  evidence: () => ['Prophet 回测 MAPE 8.4%', 'DoWhy ATE +0.12', '小红书种草帖 +38% w/w'],
})
</script>

<template>
  <NCard :bordered="false" :title="title" class="explanation-card">
    <p class="explanation-card__text">{{ rationale }}</p>
    <NSpace size="small">
      <NTag v-for="e in evidence" :key="e" type="info" round size="small">{{ e }}</NTag>
    </NSpace>
  </NCard>
</template>

<style scoped>
.explanation-card__text {
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  line-height: 1.65;
  margin: 0 0 12px;
}
</style>
