/**
 * 语言切换 composable
 */

import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

// 语言存储键
const LOCALE_STORAGE_KEY = 'echolens-locale'

// 支持的语言
export const SUPPORTED_LOCALES = [
  { value: 'zh-CN', label: '简体中文', flag: '🇨🇳' },
  { value: 'en-US', label: 'English', flag: '🇺🇸' },
] as const

export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number]['value']

/**
 * 获取存储的语言偏好
 */
function getStoredLocale(): SupportedLocale {
  if (typeof window === 'undefined') return 'zh-CN'
  const stored = localStorage.getItem(LOCALE_STORAGE_KEY)
  if (stored === 'zh-CN' || stored === 'en-US') {
    return stored
  }
  // 尝试从浏览器语言推断
  const browserLang = navigator.language
  if (browserLang.startsWith('zh')) {
    return 'zh-CN'
  }
  return 'en-US'
}

/**
 * 保存语言偏好
 */
function setStoredLocale(locale: SupportedLocale): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(LOCALE_STORAGE_KEY, locale)
}

/**
 * 语言切换 composable
 */
export function useLocale() {
  const { locale, t } = useI18n()

  // 当前语言
  const currentLocale = computed<SupportedLocale>({
    get: () => locale.value as SupportedLocale,
    set: (value: SupportedLocale) => {
      locale.value = value
      setStoredLocale(value)
      // 更新 HTML lang 属性
      if (typeof document !== 'undefined') {
        document.documentElement.lang = value
      }
    },
  })

  // 当前语言信息
  const currentLocaleInfo = computed(() => {
    return SUPPORTED_LOCALES.find((l) => l.value === currentLocale.value)
  })

  // 切换语言
  function toggleLocale() {
    currentLocale.value = currentLocale.value === 'zh-CN' ? 'en-US' : 'zh-CN'
  }

  // 设置语言
  function setLocale(locale: SupportedLocale) {
    currentLocale.value = locale
  }

  // 初始化
  const stored = getStoredLocale()
  if (locale.value !== stored) {
    locale.value = stored
  }
  if (typeof document !== 'undefined') {
    document.documentElement.lang = stored
  }

  return {
    locale: currentLocale,
    localeInfo: currentLocaleInfo,
    supportedLocales: SUPPORTED_LOCALES,
    toggleLocale,
    setLocale,
    t,
  }
}
