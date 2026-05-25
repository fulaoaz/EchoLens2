<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  NAlert,
  NButton,
  NCard,
  NDynamicInput,
  NEmpty,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NProgress,
  NSpace,
  NTag,
  useMessage,
} from 'naive-ui'
import { crawlerApi, type CrawlJob } from '@/api/crawler'

const props = defineProps<{ projectId: string }>()
const emit = defineEmits<{ refreshed: [] }>()

const message = useMessage()
const jobs = ref<CrawlJob[]>([])
const sourceUrls = ref<string[]>([''])
const platformsText = ref('')
const materialText = ref('')
const maxTargets = ref<number>(8)
const loading = ref(false)
const starting = ref(false)
const errorText = ref<string | null>(null)

const platforms = computed(() =>
  platformsText.value
    .split(/[，,\s]+/)
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean),
)

const validSourceUrls = computed(() => sourceUrls.value.map((item) => item.trim()).filter(Boolean))

const trimmedMaterial = computed(() => materialText.value.trim())

const canStart = computed(
  () => validSourceUrls.value.length > 0 || trimmedMaterial.value.length > 0,
)

function statusType(s: CrawlJob['status']) {
  return s === 'success'
    ? 'success'
    : s === 'failed'
      ? 'error'
      : s === 'running'
        ? 'info'
        : s === 'cancelled'
          ? 'warning'
          : 'default'
}

function sourceLabel(source: CrawlJob['source']): string {
  if (source === 'manual_url') return '手动 URL'
  if (source === 'material_search') return '材料检索'
  return source ?? ''
}

async function loadJobs(): Promise<void> {
  loading.value = true
  errorText.value = null
  try {
    jobs.value = await crawlerApi.listJobs(props.projectId)
  } catch (e) {
    errorText.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
  }
}

async function startCrawl(): Promise<void> {
  if (!canStart.value) {
    message.warning('请粘贴营销材料，或至少补充一个公开 URL')
    return
  }
  starting.value = true
  errorText.value = null
  try {
    const created = await crawlerApi.start({
      projectId: props.projectId,
      platforms: platforms.value,
      sourceUrls: validSourceUrls.value,
      materialText: trimmedMaterial.value,
      maxTargets: maxTargets.value,
    })
    jobs.value = [...created, ...jobs.value]
    const failed = created.filter((job) => job.status === 'failed')
    if (failed.length) {
      message.error(`采集完成，但 ${failed.length} 个任务失败，请查看错误信息`)
    } else {
      message.success(`采集完成，共生成 ${created.length} 个任务并写入种子数据`)
      emit('refreshed')
    }
    sourceUrls.value = ['']
  } catch (e) {
    message.error(`启动采集失败：${e instanceof Error ? e.message : String(e)}`)
  } finally {
    starting.value = false
  }
}

async function cancel(job: CrawlJob): Promise<void> {
  try {
    const updated = await crawlerApi.cancel(job.id)
    jobs.value = jobs.value.map((item) => (item.id === updated.id ? updated : item))
  } catch (e) {
    message.error(`取消失败：${e instanceof Error ? e.message : String(e)}`)
  }
}

watch(() => props.projectId, loadJobs)
onMounted(loadJobs)
</script>

<template>
  <NCard title="材料驱动真实采集" :bordered="false" class="crawl-progress">
    <NSpace vertical size="medium">
      <NAlert type="info" :bordered="false">
        基于项目关键词与你提供的营销材料，自动在公开搜索入口（新闻、微博、小红书、知乎）发现舆情线索，
        并按 robots.txt、透明 User-Agent 与限速策略采集。也可补充具体公开 URL 进一步定向。
      </NAlert>

      <NForm label-placement="top">
        <NFormItem label="营销材料 / 舆情上下文（推荐）">
          <NInput
            v-model:value="materialText"
            type="textarea"
            placeholder="粘贴产品介绍、推广文案、舆情简报等，系统会自动抽取关键词进行公开检索。"
            :autosize="{ minRows: 4, maxRows: 10 }"
            clearable
          />
        </NFormItem>
        <NFormItem label="补充公开 URL（可选）">
          <NDynamicInput v-model:value="sourceUrls" placeholder="https://example.com/public-page" />
        </NFormItem>
        <NSpace align="end" :wrap="true">
          <NFormItem label="平台提示（可选）" style="min-width: 240px">
            <NInput v-model:value="platformsText" placeholder="news, weibo, xhs, zhihu" clearable />
          </NFormItem>
          <NFormItem label="最大任务数" style="width: 160px">
            <NInputNumber v-model:value="maxTargets" :min="1" :max="50" />
          </NFormItem>
          <NButton type="primary" :loading="starting" :disabled="!canStart" @click="startCrawl">
            开始材料驱动采集
          </NButton>
          <NButton tertiary :loading="loading" @click="loadJobs">刷新任务</NButton>
        </NSpace>
      </NForm>

      <NAlert v-if="errorText" type="error" closable @close="errorText = null">
        {{ errorText }}
      </NAlert>

      <NEmpty v-if="!jobs.length && !loading" size="small" description="尚无爬虫任务" />

      <div v-for="job in jobs" :key="job.id" class="crawl-progress__row">
        <div class="crawl-progress__head">
          <span class="crawl-progress__platform">{{ job.platform }}</span>
          <NTag :type="statusType(job.status)" size="small" round>{{ job.status }}</NTag>
          <NTag v-if="job.source" size="small" round :bordered="false" type="default">
            {{ sourceLabel(job.source) }}
          </NTag>
          <NTag v-if="job.keyword" size="small" round :bordered="false" type="info">
            {{ job.keyword }}
          </NTag>
          <span class="crawl-progress__count mono">{{ job.itemsCollected }} 条</span>
          <NButton
            v-if="job.status === 'pending' || job.status === 'running'"
            size="tiny"
            tertiary
            @click="cancel(job)"
          >
            取消
          </NButton>
        </div>
        <div v-if="job.sourceUrl" class="crawl-progress__url">{{ job.sourceUrl }}</div>
        <NProgress
          :percentage="job.progress"
          :show-indicator="true"
          :height="8"
          :border-radius="6"
          :status="
            job.status === 'failed' ? 'error' : job.status === 'success' ? 'success' : 'info'
          "
        />
        <NAlert v-if="job.error" type="error" :bordered="false" class="crawl-progress__error">
          {{ job.error }}
        </NAlert>
      </div>
    </NSpace>
  </NCard>
</template>

<style scoped>
.crawl-progress__row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.crawl-progress__head {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.crawl-progress__platform {
  font-weight: 600;
  color: var(--text-primary);
}
.crawl-progress__count {
  margin-left: auto;
  color: var(--text-muted);
  font-size: var(--fs-sm);
}
.crawl-progress__url {
  color: var(--text-muted);
  font-size: var(--fs-xs);
  word-break: break-all;
}
.crawl-progress__error {
  margin-top: 4px;
}
</style>
