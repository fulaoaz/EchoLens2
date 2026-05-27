<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  NAlert,
  NButton,
  NCard,
  NForm,
  NFormItem,
  NGrid,
  NGridItem,
  NInput,
  NLayout,
  NLayoutContent,
  NLayoutHeader,
  NSpace,
  NTag,
  useMessage,
} from 'naive-ui'
import { useRouter } from 'vue-router'
import { settingsApi } from '@/api/settings'
import { getApiBaseUrl, getStoredApiBaseUrl, setStoredApiBaseUrl } from '@/composables/usePlatform'

const router = useRouter()
const message = useMessage()
const loading = ref(false)
const saving = ref(false)
const keyConfigured = ref(false)

const form = reactive({
  backendBaseUrl: getStoredApiBaseUrl() || getApiBaseUrl(),
  llmBaseUrl: 'https://api.openai.com/v1',
  llmModelName: 'gpt-4o-mini',
  llmApiKey: '',
})

async function loadSettings(): Promise<void> {
  loading.value = true
  try {
    const settings = await settingsApi.get()
    form.llmBaseUrl = settings.llm_base_url
    form.llmModelName = settings.llm_model_name
    keyConfigured.value = settings.llm_api_key_configured
  } catch (e) {
    message.warning(`无法读取后端模型配置：${e instanceof Error ? e.message : String(e)}`)
  } finally {
    loading.value = false
  }
}

async function saveSettings(): Promise<void> {
  saving.value = true
  const previousBackendBaseUrl = getStoredApiBaseUrl()
  try {
    setStoredApiBaseUrl(form.backendBaseUrl)
    form.backendBaseUrl = getApiBaseUrl()
    const input = {
      llm_base_url: form.llmBaseUrl.trim(),
      llm_model_name: form.llmModelName.trim(),
      ...(form.llmApiKey.trim() ? { llm_api_key: form.llmApiKey.trim() } : {}),
    }
    const settings = await settingsApi.update(input)
    form.llmBaseUrl = settings.llm_base_url
    form.llmModelName = settings.llm_model_name
    form.llmApiKey = ''
    keyConfigured.value = settings.llm_api_key_configured
    message.success('配置已保存，后续请求将使用新的模型提供商参数')
  } catch (e) {
    setStoredApiBaseUrl(previousBackendBaseUrl)
    form.backendBaseUrl = getStoredApiBaseUrl() || getApiBaseUrl()
    message.error(`保存失败：${e instanceof Error ? e.message : String(e)}`)
  } finally {
    saving.value = false
  }
}

function resetBackendUrl(): void {
  form.backendBaseUrl = ''
  setStoredApiBaseUrl('')
  form.backendBaseUrl = getApiBaseUrl()
  message.success('已恢复默认后端服务地址')
}

onMounted(loadSettings)
</script>

<template>
  <NLayout style="min-height: 100vh">
    <NLayoutHeader
      bordered
      style="padding: 18px 32px; display: flex; justify-content: space-between; align-items: center"
    >
      <div>
        <div style="font-family: var(--font-mono); font-size: 18px; letter-spacing: 1px">
          系统设置
        </div>
        <div style="color: var(--text-muted); font-size: 13px; margin-top: 4px">
          配置后端服务地址与模型提供商参数
        </div>
      </div>
      <NSpace>
        <NButton quaternary @click="router.push({ name: 'workbench' })">返回工作台</NButton>
        <NButton :loading="loading" @click="loadSettings">重新读取</NButton>
        <NButton type="primary" :loading="saving" @click="saveSettings">保存配置</NButton>
      </NSpace>
    </NLayoutHeader>

    <NLayoutContent style="padding: 32px">
      <NGrid :cols="2" :x-gap="18" :y-gap="18" responsive="screen">
        <NGridItem>
          <NCard title="客户端连接">
            <NAlert type="info" :bordered="false" style="margin-bottom: 18px">
              Windows 和 Android 客户端会先连接这里填写的后端服务地址，再由后端调用模型提供商。
            </NAlert>
            <NForm label-placement="top">
              <NFormItem label="后端服务地址">
                <NInput
                  v-model:value="form.backendBaseUrl"
                  placeholder="例如：http://localhost:5001 或 http://10.0.2.2:5001"
                />
              </NFormItem>
              <NSpace>
                <NButton @click="resetBackendUrl">恢复默认地址</NButton>
                <NTag round type="info">当前请求地址：{{ getApiBaseUrl() }}</NTag>
              </NSpace>
            </NForm>
          </NCard>
        </NGridItem>

        <NGridItem>
          <NCard title="模型提供商">
            <NAlert type="warning" :bordered="false" style="margin-bottom: 18px">
              API Key 只在保存时提交给后端写入本地 .env；页面不会回显已保存的 Key。
            </NAlert>
            <NForm label-placement="top">
              <NFormItem label="LLM Base URL">
                <NInput v-model:value="form.llmBaseUrl" placeholder="https://api.openai.com/v1" />
              </NFormItem>
              <NFormItem label="模型名称">
                <NInput v-model:value="form.llmModelName" placeholder="gpt-4o-mini" />
              </NFormItem>
              <NFormItem :label="keyConfigured ? '替换 API Key（已配置）' : 'API Key（未配置）'">
                <NInput
                  v-model:value="form.llmApiKey"
                  type="password"
                  show-password-on="click"
                  placeholder="留空则不修改已保存的 API Key"
                />
              </NFormItem>
            </NForm>
          </NCard>
        </NGridItem>
      </NGrid>
    </NLayoutContent>
  </NLayout>
</template>
