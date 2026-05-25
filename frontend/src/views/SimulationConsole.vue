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
import { ArrowBackOutline } from '@vicons/ionicons5'
import { useRoute, useRouter } from 'vue-router'
import SimulationConsolePanel from '@/components/simulation/SimulationConsolePanel.vue'

const props = defineProps<{ id: string }>()
const router = useRouter()
const route = useRoute()

const defaultRunId = computed<string | null>(() => {
  const q = route.query.runId
  return typeof q === 'string' && q ? q : null
})

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push({ name: 'project-detail', params: { id: props.id } })
  }
}
</script>

<template>
  <NLayout style="min-height: 100vh">
    <NLayoutHeader bordered style="padding: 16px 24px">
      <NSpace align="center">
        <NButton quaternary @click="goBack">
          <template #icon><NIcon :component="ArrowBackOutline" /></template>
          返回
        </NButton>
        <NDivider vertical />
        <strong>仿真控制台 · {{ id }}</strong>
        <NTag type="info" round size="small">M2 · 多智能体异步仿真</NTag>
      </NSpace>
    </NLayoutHeader>
    <NLayoutContent style="padding: 24px">
      <SimulationConsolePanel :project-id="id" :default-run-id="defaultRunId" />
    </NLayoutContent>
  </NLayout>
</template>
