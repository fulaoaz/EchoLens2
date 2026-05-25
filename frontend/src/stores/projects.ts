import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { projectsApi, type CreateProjectInput, type Project } from '@/api/projects'

export const useProjectsStore = defineStore('projects', () => {
  const items = ref<Project[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastFetched = ref<number | null>(null)

  const count = computed(() => items.value.length)
  const byStatus = computed(() => {
    const groups: Record<string, number> = {}
    for (const p of items.value) groups[p.status] = (groups[p.status] ?? 0) + 1
    return groups
  })

  async function refresh(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const result = await projectsApi.list()
      items.value = result.items
      lastFetched.value = Date.now()
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  }

  async function create(input: CreateProjectInput): Promise<Project> {
    const project = await projectsApi.create(input)
    items.value = [project, ...items.value]
    return project
  }

  async function remove(id: string): Promise<void> {
    await projectsApi.remove(id)
    items.value = items.value.filter((p) => p.id !== id)
  }

  function getById(id: string): Project | undefined {
    return items.value.find((p) => p.id === id)
  }

  return {
    items,
    loading,
    error,
    lastFetched,
    count,
    byStatus,
    refresh,
    create,
    remove,
    getById,
  }
})

export default useProjectsStore
