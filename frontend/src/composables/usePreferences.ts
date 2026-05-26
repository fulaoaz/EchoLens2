/**
 * 用户偏好设置管理
 */

import { ref, watch } from 'vue'
import type { SupportedLocale } from './useLocale'
import type { ThemeMode } from './useDarkMode'

// 偏好设置存储键
const PREFERENCES_STORAGE_KEY = 'echolens-preferences'

// 用户偏好设置接口
export interface UserPreferences {
  // 外观
  theme: ThemeMode
  locale: SupportedLocale
  fontSize: 'small' | 'medium' | 'large'
  compactMode: boolean

  // 通知
  enableNotifications: boolean
  enableSoundEffects: boolean

  // 编辑器
  autoSave: boolean
  autoSaveInterval: number // 秒

  // 高级
  enableDebugMode: boolean
  enableExperimentalFeatures: boolean
  maxConcurrentTasks: number

  // 数据
  dataRetentionDays: number
  autoBackup: boolean
  autoBackupInterval: number // 小时
}

// 默认偏好设置
const DEFAULT_PREFERENCES: UserPreferences = {
  theme: 'auto',
  locale: 'zh-CN',
  fontSize: 'medium',
  compactMode: false,

  enableNotifications: true,
  enableSoundEffects: false,

  autoSave: true,
  autoSaveInterval: 30,

  enableDebugMode: false,
  enableExperimentalFeatures: false,
  maxConcurrentTasks: 3,

  dataRetentionDays: 30,
  autoBackup: true,
  autoBackupInterval: 24,
}

/**
 * 加载偏好设置
 */
function loadPreferences(): UserPreferences {
  if (typeof window === 'undefined') return { ...DEFAULT_PREFERENCES }

  try {
    const stored = localStorage.getItem(PREFERENCES_STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      return { ...DEFAULT_PREFERENCES, ...parsed }
    }
  } catch (error) {
    console.error('Failed to load preferences:', error)
  }

  return { ...DEFAULT_PREFERENCES }
}

/**
 * 保存偏好设置
 */
function savePreferences(preferences: UserPreferences): void {
  if (typeof window === 'undefined') return

  try {
    localStorage.setItem(PREFERENCES_STORAGE_KEY, JSON.stringify(preferences))
  } catch (error) {
    console.error('Failed to save preferences:', error)
  }
}

/**
 * 用户偏好设置 composable
 */
export function usePreferences() {
  const preferences = ref<UserPreferences>(loadPreferences())

  // 监听变化并自动保存
  watch(
    preferences,
    (newPreferences) => {
      savePreferences(newPreferences)
    },
    { deep: true },
  )

  // 重置为默认值
  function resetPreferences() {
    preferences.value = { ...DEFAULT_PREFERENCES }
  }

  // 导出偏好设置
  function exportPreferences(): string {
    return JSON.stringify(preferences.value, null, 2)
  }

  // 导入偏好设置
  function importPreferences(json: string): boolean {
    try {
      const parsed = JSON.parse(json)
      preferences.value = { ...DEFAULT_PREFERENCES, ...parsed }
      return true
    } catch (error) {
      console.error('Failed to import preferences:', error)
      return false
    }
  }

  // 更新单个偏好
  function updatePreference<K extends keyof UserPreferences>(key: K, value: UserPreferences[K]) {
    preferences.value[key] = value
  }

  return {
    preferences,
    resetPreferences,
    exportPreferences,
    importPreferences,
    updatePreference,
  }
}

/**
 * 字体大小映射
 */
export const FONT_SIZE_MAP = {
  small: '14px',
  medium: '16px',
  large: '18px',
} as const

/**
 * 应用字体大小
 */
export function applyFontSize(size: UserPreferences['fontSize']): void {
  if (typeof document === 'undefined') return
  document.documentElement.style.fontSize = FONT_SIZE_MAP[size]
}
