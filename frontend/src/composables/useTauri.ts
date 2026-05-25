/**
 * Tauri 桌面端特性封装
 *
 * 提供：
 * - 窗口管理
 * - 系统托盘
 * - 原生菜单
 * - 键盘快捷键
 */

import { ref, onMounted, onUnmounted } from 'vue'
import { isTauri } from './usePlatform'

type UnlistenFn = () => void

/**
 * 窗口管理
 */
export function useWindow() {
  const isMaximized = ref(false)
  const isFullscreen = ref(false)

  let unlistenResize: UnlistenFn | null = null

  onMounted(async () => {
    if (!isTauri.value) return

    const { getCurrentWindow } = await import('@tauri-apps/api/window')
    const appWindow = getCurrentWindow()

    // 初始化状态
    isMaximized.value = await appWindow.isMaximized()
    isFullscreen.value = await appWindow.isFullscreen()

    // 监听窗口状态变化
    unlistenResize = await appWindow.onResized(async () => {
      isMaximized.value = await appWindow.isMaximized()
      isFullscreen.value = await appWindow.isFullscreen()
    })
  })

  onUnmounted(() => {
    if (unlistenResize) {
      unlistenResize()
    }
  })

  async function minimize() {
    if (!isTauri.value) return
    const { getCurrentWindow } = await import('@tauri-apps/api/window')
    await getCurrentWindow().minimize()
  }

  async function toggleMaximize() {
    if (!isTauri.value) return
    const { getCurrentWindow } = await import('@tauri-apps/api/window')
    await getCurrentWindow().toggleMaximize()
  }

  async function toggleFullscreen() {
    if (!isTauri.value) return
    const { getCurrentWindow } = await import('@tauri-apps/api/window')
    const appWindow = getCurrentWindow()
    const current = await appWindow.isFullscreen()
    await appWindow.setFullscreen(!current)
  }

  async function close() {
    if (!isTauri.value) return
    const { getCurrentWindow } = await import('@tauri-apps/api/window')
    await getCurrentWindow().close()
  }

  async function hide() {
    if (!isTauri.value) return
    const { getCurrentWindow } = await import('@tauri-apps/api/window')
    await getCurrentWindow().hide()
  }

  async function show() {
    if (!isTauri.value) return
    const { getCurrentWindow } = await import('@tauri-apps/api/window')
    const appWindow = getCurrentWindow()
    await appWindow.show()
    await appWindow.setFocus()
  }

  return {
    isMaximized,
    isFullscreen,
    minimize,
    toggleMaximize,
    toggleFullscreen,
    close,
    hide,
    show,
  }
}

/**
 * 全局快捷键
 */
export function useShortcuts(_shortcuts: Record<string, () => void>) {
  const registered: string[] = []

  onMounted(async () => {
    if (!isTauri.value) return

    // Tauri 2.0 uses plugin-global-shortcut
    // For now, skip shortcut registration as it requires additional setup
    console.warn('Global shortcuts require @tauri-apps/plugin-global-shortcut')
  })

  onUnmounted(async () => {
    if (!isTauri.value || registered.length === 0) return
    // Cleanup would go here
  })
}

/**
 * 系统托盘交互
 */
export function useTray() {
  async function showWindow() {
    if (!isTauri.value) return
    const { getCurrentWindow } = await import('@tauri-apps/api/window')
    const appWindow = getCurrentWindow()
    await appWindow.show()
    await appWindow.setFocus()
  }

  async function hideWindow() {
    if (!isTauri.value) return
    const { getCurrentWindow } = await import('@tauri-apps/api/window')
    await getCurrentWindow().hide()
  }

  return {
    showWindow,
    hideWindow,
  }
}

/**
 * 应用元数据
 */
export function useAppInfo() {
  const name = ref('')
  const version = ref('')

  onMounted(async () => {
    if (!isTauri.value) return

    const { getName, getVersion } = await import('@tauri-apps/api/app')
    name.value = await getName()
    version.value = await getVersion()
  })

  return {
    name,
    version,
  }
}
