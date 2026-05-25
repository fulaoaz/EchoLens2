<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  NCard,
  NSpace,
  NSpin,
  NAlert,
  NButton,
  NTag,
  NIcon,
  NEmpty,
  NList,
  NListItem,
  NThing,
  NDivider,
  NScrollbar,
  useMessage,
} from 'naive-ui'
import {
  RefreshOutline,
  DocumentTextOutline,
  DownloadOutline,
  AddCircleOutline,
} from '@vicons/ionicons5'
import { reportApi, type ReportSummary } from '@/api/report'

const props = defineProps<{ projectId: string }>()
const message = useMessage()

const loading = ref(false)
const generating = ref(false)
const errorText = ref<string | null>(null)

const reports = ref<ReportSummary[]>([])
const selectedId = ref<string | null>(null)
const currentMarkdown = ref<string>('')
const currentLoading = ref(false)

// ---------- API actions ------------------------------------------------------

async function loadList(autoSelectFirst = false): Promise<void> {
  if (!props.projectId) return
  loading.value = true
  errorText.value = null
  try {
    reports.value = await reportApi.list(props.projectId)
    if (autoSelectFirst && reports.value.length) {
      await selectReport(reports.value[0].id)
    } else if (selectedId.value && !reports.value.some((r) => r.id === selectedId.value)) {
      selectedId.value = null
      currentMarkdown.value = ''
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    errorText.value = msg
    message.error(`报告列表加载失败：${msg}`)
  } finally {
    loading.value = false
  }
}

async function selectReport(id: string): Promise<void> {
  selectedId.value = id
  currentLoading.value = true
  try {
    const full = await reportApi.get(id)
    currentMarkdown.value = full.markdown
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    message.error(`报告加载失败：${msg}`)
    currentMarkdown.value = ''
  } finally {
    currentLoading.value = false
  }
}

async function generate(): Promise<void> {
  if (!props.projectId) return
  generating.value = true
  try {
    const summary = await reportApi.generate(props.projectId)
    message.success('报告已生成')
    await loadList()
    await selectReport(summary.id)
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    message.error(`生成失败：${msg}`)
  } finally {
    generating.value = false
  }
}

const currentReport = computed<ReportSummary | null>(() => {
  if (!selectedId.value) return null
  return reports.value.find((r) => r.id === selectedId.value) ?? null
})

const downloadHref = computed(() =>
  selectedId.value ? reportApi.downloadUrl(selectedId.value) : '#',
)
const downloadHtmlHref = computed(() =>
  selectedId.value ? reportApi.downloadHtmlUrl(selectedId.value) : '#',
)

onMounted(() => loadList(true))
watch(
  () => props.projectId,
  () => {
    selectedId.value = null
    currentMarkdown.value = ''
    void loadList(true)
  },
)

// ---------- minimal markdown renderer ----------------------------------------
//
// We deliberately avoid pulling in markdown-it (≈ 70 KB gzipped) for a single
// internal report view. The backend renderer is deterministic and only emits
// the patterns below — anything richer should ship a dedicated dep.

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function inline(text: string): string {
  let out = escapeHtml(text)
  // bold **xxx**
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  // italic *xxx* (only when surrounded by spaces or boundary)
  // skip — backend doesn't emit italics; avoids accidental matches.
  // inline code `xxx`
  out = out.replace(/`([^`]+)`/g, '<code>$1</code>')
  return out
}

function renderMarkdown(md: string): string {
  if (!md) return ''
  const lines = md.split(/\r?\n/)
  const html: string[] = []
  let inList = false
  let inBlockquote = false

  const closeList = (): void => {
    if (inList) {
      html.push('</ul>')
      inList = false
    }
  }
  const closeQuote = (): void => {
    if (inBlockquote) {
      html.push('</blockquote>')
      inBlockquote = false
    }
  }

  for (const raw of lines) {
    const line = raw.trimEnd()
    if (!line.trim()) {
      closeList()
      closeQuote()
      continue
    }
    if (line.startsWith('### ')) {
      closeList()
      closeQuote()
      html.push(`<h3>${inline(line.slice(4))}</h3>`)
      continue
    }
    if (line.startsWith('## ')) {
      closeList()
      closeQuote()
      html.push(`<h2>${inline(line.slice(3))}</h2>`)
      continue
    }
    if (line.startsWith('# ')) {
      closeList()
      closeQuote()
      html.push(`<h1>${inline(line.slice(2))}</h1>`)
      continue
    }
    if (line === '---' || line === '***') {
      closeList()
      closeQuote()
      html.push('<hr />')
      continue
    }
    if (line.startsWith('> ')) {
      closeList()
      if (!inBlockquote) {
        html.push('<blockquote>')
        inBlockquote = true
      }
      html.push(`<p>${inline(line.slice(2))}</p>`)
      continue
    }
    if (/^\s*-\s+/.test(line)) {
      closeQuote()
      if (!inList) {
        html.push('<ul>')
        inList = true
      }
      html.push(`<li>${inline(line.replace(/^\s*-\s+/, ''))}</li>`)
      continue
    }
    closeList()
    closeQuote()
    html.push(`<p>${inline(line)}</p>`)
  }
  closeList()
  closeQuote()
  return html.join('\n')
}

const renderedHtml = computed(() => renderMarkdown(currentMarkdown.value))
</script>

<template>
  <div class="report-panel">
    <NSpace align="center" justify="space-between" style="margin-bottom: 16px">
      <NSpace align="center" :size="8">
        <NIcon :component="DocumentTextOutline" />
        <strong>决策报告</strong>
        <NTag size="small" round>同源决策快照 · markdown</NTag>
      </NSpace>
      <NSpace :size="8">
        <NButton type="primary" :loading="generating" :disabled="!projectId" @click="generate">
          <template #icon><NIcon :component="AddCircleOutline" /></template>
          生成新报告
        </NButton>
        <NButton size="small" :loading="loading" @click="() => loadList()">
          <template #icon><NIcon :component="RefreshOutline" /></template>
          刷新
        </NButton>
      </NSpace>
    </NSpace>

    <NAlert
      v-if="errorText"
      type="error"
      :title="'加载失败'"
      closable
      style="margin-bottom: 12px"
      @close="errorText = null"
    >
      {{ errorText }}
    </NAlert>

    <div class="report-grid">
      <NCard
        :bordered="false"
        size="small"
        title="历史报告"
        class="list-card"
        content-style="padding: 0"
      >
        <NSpin :show="loading">
          <NEmpty
            v-if="!reports.length && !loading"
            size="small"
            description="尚无历史报告"
            style="padding: 24px 0"
          />
          <NScrollbar v-else style="max-height: 540px">
            <NList hoverable clickable size="small">
              <NListItem
                v-for="r in reports"
                :key="r.id"
                :class="{ 'item-active': r.id === selectedId }"
                @click="selectReport(r.id)"
              >
                <NThing>
                  <template #header>
                    <span class="rep-title">{{ r.title }}</span>
                  </template>
                  <template #description>
                    <span class="rep-time">{{ r.generatedAt }}</span>
                  </template>
                </NThing>
              </NListItem>
            </NList>
          </NScrollbar>
        </NSpin>
      </NCard>

      <NCard :bordered="false" size="small" class="preview-card">
        <template #header>
          <NSpace align="center" :size="8">
            <strong>{{ currentReport?.title ?? '预览' }}</strong>
            <NTag v-if="currentReport" size="tiny" round>
              {{ currentReport.format }}
            </NTag>
          </NSpace>
        </template>
        <template #header-extra>
          <NSpace :size="6">
            <NButton
              v-if="currentReport"
              tag="a"
              :href="downloadHref"
              :download="`echolens-report-${currentReport.id.slice(0, 8)}.md`"
              size="small"
              tertiary
            >
              <template #icon><NIcon :component="DownloadOutline" /></template>
              下载 .md
            </NButton>
            <NButton
              v-if="currentReport"
              tag="a"
              :href="downloadHtmlHref"
              :download="`echolens-report-${currentReport.id.slice(0, 8)}.html`"
              size="small"
              tertiary
              title="自包含 HTML — 浏览器打开后用打印另存为 PDF"
            >
              <template #icon><NIcon :component="DownloadOutline" /></template>
              下载 .html
            </NButton>
          </NSpace>
        </template>
        <NSpin :show="currentLoading">
          <NEmpty
            v-if="!currentReport"
            description="选择左侧报告或点击「生成新报告」"
            style="padding: 48px 0"
          />
          <NScrollbar v-else style="max-height: 580px">
            <!-- eslint-disable-next-line vue/no-v-html -- markdown is backend-deterministic and rendered inline, no external input -->
            <div class="markdown-body" v-html="renderedHtml" />
          </NScrollbar>
        </NSpin>
      </NCard>
    </div>

    <NDivider style="margin: 24px 0 8px" />
    <p class="footnote">
      报告由 <code>decision-rules-v1</code> 生成，规则可解释、可追溯。每条建议附 evidence
      字段，用于回溯到具体仿真 / 预测 / 因果运行。
    </p>
  </div>
</template>

<style scoped>
.report-panel {
  width: 100%;
}
.report-grid {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 16px;
  align-items: start;
}
.list-card,
.preview-card {
  background: var(--bg-card, rgba(255, 255, 255, 0.02));
}
.item-active {
  background: var(--bg-tag, rgba(91, 141, 239, 0.12));
}
.rep-title {
  font-size: var(--fs-sm, 13px);
  font-weight: 600;
}
.rep-time {
  color: var(--text-muted, #888);
  font-size: 12px;
}
.markdown-body {
  padding: 4px 8px;
  color: var(--text-primary, #d8d8d8);
  font-size: 14px;
  line-height: 1.65;
}
.markdown-body :deep(h1) {
  font-size: 22px;
  margin: 12px 0 8px;
}
.markdown-body :deep(h2) {
  font-size: 17px;
  margin: 18px 0 8px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--border-muted, rgba(255, 255, 255, 0.08));
}
.markdown-body :deep(h3) {
  font-size: 15px;
  margin: 14px 0 6px;
}
.markdown-body :deep(p) {
  margin: 6px 0;
}
.markdown-body :deep(ul) {
  padding-left: 22px;
  margin: 6px 0;
}
.markdown-body :deep(li) {
  margin: 2px 0;
}
.markdown-body :deep(blockquote) {
  margin: 8px 0;
  padding: 4px 12px;
  color: var(--text-secondary, #aaa);
  border-left: 3px solid var(--color-accent, #5b8def);
  background: rgba(91, 141, 239, 0.06);
}
.markdown-body :deep(code) {
  padding: 1px 5px;
  border-radius: 3px;
  background: rgba(91, 141, 239, 0.12);
  font-family: 'JetBrainsMono', 'Fira Code', Consolas, monospace;
  font-size: 12.5px;
}
.markdown-body :deep(hr) {
  border: 0;
  border-top: 1px solid var(--border-muted, rgba(255, 255, 255, 0.08));
  margin: 14px 0;
}
.markdown-body :deep(strong) {
  color: var(--text-emphasis, #fff);
}
.footnote {
  color: var(--text-muted, #888);
  font-size: 12px;
}
@media (max-width: 960px) {
  .report-grid {
    grid-template-columns: 1fr;
  }
}
</style>
