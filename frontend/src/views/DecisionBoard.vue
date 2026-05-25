<script setup lang="ts">
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
import { useRouter } from 'vue-router'
import DecisionBoardPanel from '@/components/decision/DecisionBoardPanel.vue'

const props = defineProps<{ id: string }>()
const router = useRouter()
const goBack = () => router.push({ name: 'project-detail', params: { id: props.id } })

type DecisionRunKind = 'simulation' | 'forecast' | 'causal'

function onOpenRun(kind: DecisionRunKind, runId: string) {
  if (!runId) return
  const tab = kind === 'simulation' ? 'sim' : 'pred'
  router.push({
    name: 'project-detail',
    params: { id: props.id },
    query: { tab, kind, runId },
  })
}
</script>

<template>
  <NLayout style="min-height: 100vh">
    <NLayoutHeader bordered style="padding: 16px 24px">
      <NSpace align="center">
        <NButton quaternary @click="goBack">
          <template #icon><NIcon :component="ArrowBackOutline" /></template>
          返回项目
        </NButton>
        <NDivider vertical />
        <strong>综合决策看板 · {{ id }}</strong>
        <NTag type="info" size="small" round>融合 仿真 + 预测 + 因果</NTag>
      </NSpace>
    </NLayoutHeader>
    <NLayoutContent style="padding: 24px">
      <DecisionBoardPanel :project-id="id" @open-run="onOpenRun" />
    </NLayoutContent>
  </NLayout>
</template>
