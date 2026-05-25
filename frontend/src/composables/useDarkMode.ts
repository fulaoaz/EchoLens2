/**
 * 深色模式主题配置
 */

import { computed } from 'vue'
import { darkTheme, type GlobalTheme } from 'naive-ui'

// 主题偏好存储键
const THEME_STORAGE_KEY = 'echolens-theme-preference'

// 主题类型
export type ThemeMode = 'light' | 'dark' | 'auto'

/**
 * 获取系统主题偏好
 */
function getSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

/**
 * 获取存储的主题偏好
 */
function getStoredTheme(): ThemeMode {
  if (typeof window === 'undefined') return 'auto'
  const stored = localStorage.getItem(THEME_STORAGE_KEY)
  if (stored === 'light' || stored === 'dark' || stored === 'auto') {
    return stored
  }
  return 'auto'
}

/**
 * 保存主题偏好
 */
function setStoredTheme(mode: ThemeMode): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(THEME_STORAGE_KEY, mode)
}

/**
 * 解析实际主题
 */
function resolveTheme(mode: ThemeMode): 'light' | 'dark' {
  if (mode === 'auto') {
    return getSystemTheme()
  }
  return mode
}

/**
 * 应用主题到 DOM
 */
function applyThemeToDOM(theme: 'light' | 'dark'): void {
  if (typeof document === 'undefined') return

  if (theme === 'dark') {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

/**
 * 深色模式 composable
 */
export function useDarkMode() {
  // 当前主题模式
  const themeMode = computed<ThemeMode>({
    get: () => getStoredTheme(),
    set: (mode: ThemeMode) => {
      setStoredTheme(mode)
      const resolved = resolveTheme(mode)
      applyThemeToDOM(resolved)
    },
  })

  // 实际应用的主题
  const isDark = computed(() => resolveTheme(themeMode.value) === 'dark')

  // Naive UI 主题对象
  const naiveTheme = computed<GlobalTheme | null>(() => {
    return isDark.value ? darkTheme : null
  })

  // 切换主题
  function toggleTheme() {
    const current = themeMode.value
    if (current === 'light') {
      themeMode.value = 'dark'
    } else if (current === 'dark') {
      themeMode.value = 'auto'
    } else {
      themeMode.value = 'light'
    }
  }

  // 设置主题
  function setTheme(mode: ThemeMode) {
    themeMode.value = mode
  }

  // 初始化
  const resolved = resolveTheme(themeMode.value)
  applyThemeToDOM(resolved)

  // 监听系统主题变化
  if (typeof window !== 'undefined') {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = () => {
      if (themeMode.value === 'auto') {
        const resolved = getSystemTheme()
        applyThemeToDOM(resolved)
      }
    }
    mediaQuery.addEventListener('change', handleChange)
  }

  return {
    themeMode,
    isDark,
    naiveTheme,
    toggleTheme,
    setTheme,
  }
}
