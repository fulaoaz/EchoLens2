/**
 * 键盘快捷键系统
 */

import { onMounted, onUnmounted } from 'vue'

export interface ShortcutConfig {
  key: string
  ctrl?: boolean
  shift?: boolean
  alt?: boolean
  meta?: boolean
  description: string
  handler: () => void
}

// 全局快捷键注册表
const globalShortcuts = new Map<string, ShortcutConfig>()

/**
 * 生成快捷键标识符
 */
function getShortcutId(config: ShortcutConfig): string {
  const parts: string[] = []
  if (config.ctrl) parts.push('ctrl')
  if (config.shift) parts.push('shift')
  if (config.alt) parts.push('alt')
  if (config.meta) parts.push('meta')
  parts.push(config.key.toLowerCase())
  return parts.join('+')
}

/**
 * 检查事件是否匹配快捷键
 */
function matchesShortcut(event: KeyboardEvent, config: ShortcutConfig): boolean {
  const key = event.key.toLowerCase()
  const configKey = config.key.toLowerCase()

  // 检查按键
  if (key !== configKey) return false

  // 检查修饰键
  if (!!config.ctrl !== event.ctrlKey) return false
  if (!!config.shift !== event.shiftKey) return false
  if (!!config.alt !== event.altKey) return false
  if (!!config.meta !== event.metaKey) return false

  return true
}

/**
 * 全局键盘事件处理
 */
function handleGlobalKeydown(event: KeyboardEvent) {
  // 忽略输入框中的快捷键
  const target = event.target as HTMLElement
  if (
    target.tagName === 'INPUT' ||
    target.tagName === 'TEXTAREA' ||
    target.isContentEditable
  ) {
    return
  }

  // 查找匹配的快捷键
  for (const config of globalShortcuts.values()) {
    if (matchesShortcut(event, config)) {
      event.preventDefault()
      config.handler()
      break
    }
  }
}

/**
 * 注册全局快捷键
 */
export function registerGlobalShortcut(config: ShortcutConfig): () => void {
  const id = getShortcutId(config)
  globalShortcuts.set(id, config)

  // 如果是第一个快捷键，添加全局监听器
  if (globalShortcuts.size === 1) {
    window.addEventListener('keydown', handleGlobalKeydown)
  }

  // 返回注销函数
  return () => {
    globalShortcuts.delete(id)
    // 如果没有快捷键了，移除全局监听器
    if (globalShortcuts.size === 0) {
      window.removeEventListener('keydown', handleGlobalKeydown)
    }
  }
}

/**
 * 获取所有已注册的快捷键
 */
export function getRegisteredShortcuts(): ShortcutConfig[] {
  return Array.from(globalShortcuts.values())
}

/**
 * 格式化快捷键显示
 */
export function formatShortcut(config: ShortcutConfig): string {
  const parts: string[] = []
  const isMac = typeof navigator !== 'undefined' && /Mac/.test(navigator.platform)

  if (config.ctrl) parts.push(isMac ? '⌃' : 'Ctrl')
  if (config.shift) parts.push(isMac ? '⇧' : 'Shift')
  if (config.alt) parts.push(isMac ? '⌥' : 'Alt')
  if (config.meta) parts.push(isMac ? '⌘' : 'Win')

  // 格式化按键名称
  const keyName = config.key.length === 1 ? config.key.toUpperCase() : config.key
  parts.push(keyName)

  return parts.join(isMac ? '' : '+')
}

/**
 * 快捷键 composable
 */
export function useShortcuts(shortcuts: ShortcutConfig[]) {
  const unregisterFns: Array<() => void> = []

  onMounted(() => {
    // 注册所有快捷键
    for (const shortcut of shortcuts) {
      const unregister = registerGlobalShortcut(shortcut)
      unregisterFns.push(unregister)
    }
  })

  onUnmounted(() => {
    // 注销所有快捷键
    for (const unregister of unregisterFns) {
      unregister()
    }
  })

  return {
    formatShortcut,
    getRegisteredShortcuts,
  }
}

/**
 * 预定义的快捷键
 */
export const COMMON_SHORTCUTS = {
  // 导航
  goToWorkbench: { key: 'h', ctrl: true, description: 'Go to Workbench' },
  goToProjects: { key: 'p', ctrl: true, description: 'Go to Projects' },
  goToSettings: { key: ',', ctrl: true, description: 'Go to Settings' },

  // 操作
  newProject: { key: 'n', ctrl: true, description: 'New Project' },
  search: { key: 'k', ctrl: true, description: 'Search' },
  save: { key: 's', ctrl: true, description: 'Save' },
  refresh: { key: 'r', ctrl: true, description: 'Refresh' },

  // 视图
  toggleSidebar: { key: 'b', ctrl: true, description: 'Toggle Sidebar' },
  toggleTheme: { key: 'd', ctrl: true, description: 'Toggle Theme' },
  toggleLanguage: { key: 'l', ctrl: true, shift: true, description: 'Toggle Language' },

  // 帮助
  showHelp: { key: '?', shift: true, description: 'Show Help' },
  showShortcuts: { key: '/', ctrl: true, description: 'Show Shortcuts' },
} as const
