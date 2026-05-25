<script setup lang="ts">
import { computed } from 'vue'
import {
  NLayout,
  NLayoutHeader,
  NLayoutContent,
  NButton,
  NSpace,
  NIcon,
  NDivider,
  NTag,
} from 'naive-ui'
import { ArrowBackOutline, TrendingUpOutline } from '@vicons/ionicons5'
import { useRoute, useRouter } from 'vue-router'
import PredictionLabPanel from '@/components/prediction/PredictionLabPanel.vue'

defineProps<{ id: string }>()
const router = useRouter()
const route = useRoute()

const defaultRunId = computed<string | null>(() => {
  const q = route.query.runId
  return typeof q === 'string' && q ? q : null
})
</script>

<template>
  <NLayout style="min-height: 100vh">
    <NLayoutHeader bordered style="padding: 16px 24px">
      <NSpace align="center">
        <NButton quaternary @click="router.back()">
          <template #icon><NIcon :component="ArrowBackOutline" /></template>
          返回
        </NButton>
        <NDivider vertical />
        <NIcon :component="TrendingUpOutline" :size="18" color="var(--color-primary)" />
        <strong>预测实验室 · {{ id }}</strong>
        <NTag type="info" round size="small">时序 + 因果 · M3</NTag>
      </NSpace>
    </NLayoutHeader>
    <NLayoutContent style="padding: 24px">
      <PredictionLabPanel :project-id="id" :default-run-id="defaultRunId" />
    </NLayoutContent>
  </NLayout>
</template>
