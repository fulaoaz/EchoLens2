<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import {
  NModal,
  NCard,
  NForm,
  NFormItem,
  NInput,
  NDynamicTags,
  NSelect,
  NButton,
  NSpace,
  useMessage,
  type FormInst,
  type FormRules,
} from 'naive-ui'
import { useProjectsStore } from '@/stores/projects'
import { useRouter } from 'vue-router'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ 'update:show': [value: boolean] }>()

const formRef = ref<FormInst | null>(null)
const message = useMessage()
const router = useRouter()
const store = useProjectsStore()

const submitting = ref(false)

const form = reactive({
  name: '',
  description: '',
  keywords: [] as string[],
  target_platforms: [] as string[],
})

const platformOptions = [
  { label: '淘宝 / 天猫', value: 'taobao' },
  { label: '京东', value: 'jd' },
  { label: '拼多多', value: 'pdd' },
  { label: '抖音 / 抖店', value: 'douyin' },
  { label: '微博', value: 'weibo' },
  { label: '小红书', value: 'xhs' },
  { label: '知乎', value: 'zhihu' },
  { label: '新闻聚合', value: 'news' },
]

const rules: FormRules = {
  name: [{ required: true, message: '项目名称必填', trigger: 'blur' }],
}

watch(
  () => props.show,
  (v) => {
    if (v) {
      form.name = ''
      form.description = ''
      form.keywords = []
      form.target_platforms = []
    }
  },
)

async function handleSubmit(): Promise<void> {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  submitting.value = true
  try {
    const project = await store.create({ ...form })
    message.success(`项目 ${project.name} 已创建`)
    emit('update:show', false)
    router.push({ name: 'project-detail', params: { id: project.id } })
  } catch (e) {
    message.error(`创建失败：${e instanceof Error ? e.message : String(e)}`)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <NModal :show="show" @update:show="(v) => emit('update:show', v)">
    <NCard
      title="新建项目"
      :bordered="false"
      style="width: 600px"
      :segmented="{ content: true }"
      role="dialog"
      aria-modal="true"
    >
      <NForm ref="formRef" :model="form" :rules="rules" label-placement="top">
        <NFormItem label="项目名称" path="name" required>
          <NInput v-model:value="form.name" placeholder="如：双 11 美妆活动预演" maxlength="200" />
        </NFormItem>
        <NFormItem label="目标关键词">
          <NDynamicTags v-model:value="form.keywords" />
        </NFormItem>
        <NFormItem label="目标平台">
          <NSelect
            v-model:value="form.target_platforms"
            multiple
            :options="platformOptions"
            placeholder="选择要爬取的平台"
          />
        </NFormItem>
        <NFormItem label="备注">
          <NInput
            v-model:value="form.description"
            type="textarea"
            placeholder="可选：业务背景、活动周期、KPI"
            :autosize="{ minRows: 2, maxRows: 4 }"
          />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="emit('update:show', false)">取消</NButton>
          <NButton type="primary" :loading="submitting" @click="handleSubmit">创建</NButton>
        </NSpace>
      </template>
    </NCard>
  </NModal>
</template>
