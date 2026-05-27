<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  NLayout,
  NLayoutHeader,
  NLayoutContent,
  NCard,
  NGrid,
  NGridItem,
  NTag,
  NButton,
  NSpace,
  NIcon,
  NProgress,
  NStatistic,
  NEmpty,
  NSpin,
  NPopconfirm,
  useMessage,
} from 'naive-ui'
import {
  AddCircleOutline,
  FlashOutline,
  SparklesOutline,
  AnalyticsOutline,
  RefreshOutline,
  SettingsOutline,
  TrashOutline,
} from '@vicons/ionicons5'
import { useRouter } from 'vue-router'
import { useProjectsStore } from '@/stores/projects'
import NewProjectModal from '@/components/common/NewProjectModal.vue'
import type { Project, ProjectStatus } from '@/api/projects'

const router = useRouter()
const store = useProjectsStore()
const message = useMessage()

const showNew = ref(false)

onMounted(() => store.refresh())

const platformLabel = (p: Project): string =>
  p.target_platforms.length ? p.target_platforms.join(' · ') : '未指定平台'

const statusMap: Record<
  ProjectStatus,
  { label: string; type: 'info' | 'warning' | 'success' | 'error' | 'default' }
> = {
  created: { label: '待启动', type: 'default' },
  crawling: { label: '爬取中', type: 'info' },
  seed_ready: { label: '种子就绪', type: 'info' },
  simulating: { label: '仿真中', type: 'warning' },
  predicting: { label: '预测中', type: 'warning' },
  ready: { label: '完成', type: 'success' },
  failed: { label: '失败', type: 'error' },
}

const projectProgress = (p: Project): number => {
  const map: Record<ProjectStatus, number> = {
    created: 0,
    crawling: 25,
    seed_ready: 40,
    simulating: 60,
    predicting: 75,
    ready: 100,
    failed: 100,
  }
  return map[p.status] ?? 0
}

const totalKeywords = computed(() => {
  const set = new Set<string>()
  for (const p of store.items) p.keywords.forEach((k) => set.add(k))
  return Array.from(set)
})

const trendingWords = computed(() =>
  totalKeywords.value.length
    ? totalKeywords.value.slice(0, 12)
    : ['国货美妆', '直播种草', '保湿', '防晒', '618 预热', '价保', '中秋礼盒', '小众香水'],
)

async function handleDelete(id: string, name: string): Promise<void> {
  try {
    await store.remove(id)
    message.success(`已删除 ${name}`)
  } catch (e) {
    message.error(`删除失败：${e instanceof Error ? e.message : String(e)}`)
  }
}

const goProject = (id: string): unknown => router.push({ name: 'project-detail', params: { id } })
</script>

<template>
  <NLayout style="min-height: 100vh">
    <NLayoutHeader
      bordered
      style="padding: 18px 32px; display: flex; justify-content: space-between; align-items: center"
    >
      <div style="display: flex; align-items: center; gap: 12px">
        <NIcon :component="SparklesOutline" :size="26" color="var(--color-primary)" />
        <span style="font-family: var(--font-mono); font-size: 18px; letter-spacing: 1px">
          EchoLens 2.0
        </span>
        <NTag size="small" type="info" round>电子商务大数据分析</NTag>
      </div>
      <NSpace>
        <NButton quaternary @click="router.push({ name: 'settings' })">
          <template #icon><NIcon :component="SettingsOutline" /></template>
          系统设置
        </NButton>
        <NButton circle quaternary :loading="store.loading" @click="store.refresh()">
          <template #icon><NIcon :component="RefreshOutline" /></template>
        </NButton>
        <NButton type="primary" size="medium" @click="showNew = true">
          <template #icon><NIcon :component="AddCircleOutline" /></template>
          新建项目
        </NButton>
      </NSpace>
    </NLayoutHeader>

    <NLayoutContent style="padding: 32px">
      <NGrid :cols="4" :x-gap="16" :y-gap="16" responsive="screen" style="margin-bottom: 24px">
        <NGridItem>
          <NCard><NStatistic label="项目总数" :value="store.count" /></NCard>
        </NGridItem>
        <NGridItem>
          <NCard>
            <NStatistic
              label="进行中"
              :value="
                store.count - (store.byStatus['ready'] ?? 0) - (store.byStatus['failed'] ?? 0)
              "
            />
          </NCard>
        </NGridItem>
        <NGridItem>
          <NCard>
            <NStatistic label="已完成" :value="store.byStatus['ready'] ?? 0" />
          </NCard>
        </NGridItem>
        <NGridItem>
          <NCard>
            <NStatistic label="关键词覆盖" :value="totalKeywords.length" />
          </NCard>
        </NGridItem>
      </NGrid>

      <h3 style="margin: 0 0 16px 4px; color: var(--text-muted); font-weight: 500">最近项目</h3>

      <NSpin :show="store.loading">
        <NEmpty
          v-if="!store.loading && store.count === 0"
          description="还没有项目 — 点击右上角『新建项目』开始一次舆情分析"
        >
          <template #extra>
            <NButton type="primary" @click="showNew = true">
              <template #icon><NIcon :component="AddCircleOutline" /></template>
              新建第一个项目
            </NButton>
          </template>
        </NEmpty>
        <NGrid v-else :cols="3" :x-gap="16" :y-gap="16" responsive="screen">
          <NGridItem v-for="p in store.items" :key="p.id">
            <NCard
              hoverable
              :style="{ cursor: 'pointer', boxShadow: 'var(--shadow-card)' }"
              @click="goProject(p.id)"
            >
              <NSpace vertical size="medium">
                <NSpace justify="space-between" align="center">
                  <strong style="font-size: 16px">{{ p.name }}</strong>
                  <NTag :type="statusMap[p.status].type" size="small" round>
                    {{ statusMap[p.status].label }}
                  </NTag>
                </NSpace>
                <div style="color: var(--text-muted); font-size: 13px">
                  <NIcon :component="AnalyticsOutline" /> {{ platformLabel(p) }} · 更新于
                  {{ new Date(p.updated_at).toLocaleString('zh-CN') }}
                </div>
                <NProgress :percentage="projectProgress(p)" :show-indicator="true" />
                <NSpace v-if="p.keywords.length" :wrap="true">
                  <NTag v-for="k in p.keywords.slice(0, 4)" :key="k" size="small" round>
                    {{ k }}
                  </NTag>
                  <NTag v-if="p.keywords.length > 4" size="small" round>
                    +{{ p.keywords.length - 4 }}
                  </NTag>
                </NSpace>
                <NSpace justify="end" @click.stop>
                  <NPopconfirm @positive-click="handleDelete(p.id, p.name)">
                    <template #trigger>
                      <NButton tertiary size="tiny">
                        <template #icon><NIcon :component="TrashOutline" /></template>
                        删除
                      </NButton>
                    </template>
                    确认删除项目「{{ p.name }}」？
                  </NPopconfirm>
                </NSpace>
              </NSpace>
            </NCard>
          </NGridItem>
        </NGrid>
      </NSpin>

      <NCard style="margin-top: 24px" title="今日关注词">
        <NSpace>
          <NTag v-for="w in trendingWords" :key="w" round>
            <template #icon><NIcon :component="FlashOutline" /></template>
            {{ w }}
          </NTag>
        </NSpace>
      </NCard>
    </NLayoutContent>

    <NewProjectModal v-model:show="showNew" />
  </NLayout>
</template>
