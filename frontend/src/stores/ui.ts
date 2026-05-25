import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUiStore = defineStore('ui', () => {
  const collapsed = ref(false)
  const showDemoBadge = ref(true)

  function toggleSider() {
    collapsed.value = !collapsed.value
  }

  return { collapsed, showDemoBadge, toggleSider }
})
