<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import {
  NLayout,
  NLayoutHeader,
  NLayoutContent,
  NTabs,
  NTabPane,
  NButton,
  NSpace,
  NIcon,
  NTag,
  NDivider,
} from 'naive-ui'
import {
  ArrowBackOutline,
  RocketOutline,
  BulbOutline,
  TrendingUpOutline,
  GridOutline,
  DocumentTextOutline,
} from '@vicons/ionicons5'
import { useRoute, useRouter } from 'vue-router'
import CrawlProgress from '@/components/crawler/CrawlProgress.vue'
import SeedReportPanel from '@/components/seed/SeedReportPanel.vue'
import SimulationConsolePanel from '@/components/simulation/SimulationConsolePanel.vue'
import PredictionLabPanel from '@/components/prediction/PredictionLabPanel.vue'
import DecisionBoardPanel from '@/components/decision/DecisionBoardPanel.vue'
import ReportPanel from '@/components/report/ReportPanel.vue'

const props = defineProps<{ id: string }>()
const router = useRouter()
const route = useRoute()
const tab = ref<'seed' | 'sim' | 'pred' | 'dec' | 'report'>('seed')
const seedReportKey = ref(0)
const simDefaultRunId = ref<string | null>(null)
const predDefaultRunId = ref<string | null>(null)

const refreshSeedReport = () => {
  seedReportKey.value += 1
}

type DecisionRunKind = 'simulation' | 'forecast' | 'causal'

function focusRun(kind: DecisionRunKind, runId: string) {
  if (!runId) return
  if (kind === 'simulation') {
    simDefaultRunId.value = runId
    tab.value = 'sim'
  } else {
    predDefaultRunId.value = runId
    tab.value = 'pred'
  }
}

function applyRouteQuery() {
  const qTab = route.query.tab
  const qRun = route.query.runId
  const qKind = route.query.kind
  if (typeof qTab === 'string' && ['seed', 'sim', 'pred', 'dec', 'report'].includes(qTab)) {
    tab.value = qTab as typeof tab.value
  }
  if (typeof qRun === 'string' && qRun) {
    if (qKind === 'simulation') simDefaultRunId.value = qRun
    else if (qKind === 'forecast' || qKind === 'causal') predDefaultRunId.value = qRun
    else if (qTab === 'sim') simDefaultRunId.value = qRun
    else if (qTab === 'pred') predDefaultRunId.value = qRun
  }
}

onMounted(applyRouteQuery)
watch(() => route.fullPath, applyRouteQuery)

const goBack = () => router.push({ name: 'workbench' })
const goSimulationFullscreen = () =>
  router.push({
    name: 'simulation',
    params: { id: props.id },
    query: simDefaultRunId.value ? { runId: simDefaultRunId.value } : undefined,
  })
const goPrediction = () =>
  router.push({
    name: 'prediction',
    params: { id: props.id },
    query: predDefaultRunId.value ? { runId: predDefaultRunId.value } : undefined,
  })
const goDecision = () => router.push({ name: 'decision', params: { id: props.id } })
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
        <strong>项目 · {{ id }}</strong>
        <NTag type="success" round size="small">实时状态 OK</NTag>
      </NSpace>
    </NLayoutHeader>

    <NLayoutContent style="padding: 24px">
      <NTabs v-model:value="tab" type="line" animated size="large">
        <NTabPane name="seed" tab="种子报告">
          <template #tab> <NIcon :component="RocketOutline" /> 种子报告 </template>
          <NSpace vertical :size="16">
            <CrawlProgress :project-id="id" @refreshed="refreshSeedReport" />
            <SeedReportPanel :key="seedReportKey" :project-id="id" />
          </NSpace>
        </NTabPane>

        <NTabPane name="sim" tab="舆情仿真">
          <template #tab> <NIcon :component="BulbOutline" /> 舆情仿真 </template>
          <NSpace vertical :size="12">
            <NSpace justify="end">
              <NButton size="small" tertiary @click="goSimulationFullscreen"> 全屏控制台 </NButton>
            </NSpace>
            <SimulationConsolePanel :project-id="id" :default-run-id="simDefaultRunId" />
          </NSpace>
        </NTabPane>

        <NTabPane name="pred" tab="数据预测">
          <template #tab> <NIcon :component="TrendingUpOutline" /> 数据预测 </template>
          <NSpace vertical :size="12">
            <NSpace justify="end">
              <NButton size="small" tertiary @click="goPrediction"> 全屏预测实验室 </NButton>
            </NSpace>
            <PredictionLabPanel :project-id="id" :default-run-id="predDefaultRunId" />
          </NSpace>
        </NTabPane>

        <NTabPane name="dec" tab="综合决策">
          <template #tab> <NIcon :component="GridOutline" /> 综合决策 </template>
          <NSpace vertical :size="12">
            <NSpace justify="end">
              <NButton size="small" tertiary @click="goDecision"> 全屏决策看板 </NButton>
            </NSpace>
            <DecisionBoardPanel :project-id="id" @open-run="focusRun" />
          </NSpace>
        </NTabPane>

        <NTabPane name="report" tab="报告导出">
          <template #tab> <NIcon :component="DocumentTextOutline" /> 报告导出 </template>
          <ReportPanel :project-id="id" />
        </NTabPane>
      </NTabs>
    </NLayoutContent>
  </NLayout>
</template>
