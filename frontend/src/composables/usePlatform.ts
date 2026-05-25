/**
 * 平台抽象层 - 统一 Web/Tauri/Capacitor 的 API 差异
 *
 * 提供统一的接口用于：
 * - 文件访问
 * - 网络请求
 * - 系统通知
 * - 平台检测
 */

import { ref, computed } from 'vue'

// 平台类型
export type Platform = 'web' | 'tauri' | 'capacitor-ios' | 'capacitor-android'

// 平台检测
export function detectPlatform(): Platform {
  // 检测 Tauri
  if (typeof window !== 'undefined' && '__TAURI__' in window) {
    return 'tauri'
  }

  // 检测 Capacitor
  if (typeof window !== 'undefined' && 'Capacitor' in window) {
    const Capacitor = (window as { Capacitor?: { getPlatform: () => string } }).Capacitor
    if (Capacitor?.getPlatform() === 'ios') {
      return 'capacitor-ios'
    }
    if (Capacitor.getPlatform() === 'android') {
      return 'capacitor-android'
    }
  }

  // 默认为 Web
  return 'web'
}

// 当前平台
export const currentPlatform = ref<Platform>(detectPlatform())

// 平台判断
export const isWeb = computed(() => currentPlatform.value === 'web')
export const isTauri = computed(() => currentPlatform.value === 'tauri')
export const isCapacitor = computed(() =>
  currentPlatform.value.startsWith('capacitor-'),
)
export const isIOS = computed(() => currentPlatform.value === 'capacitor-ios')
export const isAndroid = computed(() => currentPlatform.value === 'capacitor-android')
export const isMobile = computed(() => isIOS.value || isAndroid.value)
export const isDesktop = computed(() => isTauri.value || isWeb.value)

// 文件选择接口
export interface FilePickerOptions {
  multiple?: boolean
  accept?: string
}

export interface PickedFile {
  name: string
  size: number
  type: string
  data: ArrayBuffer | string
}

/**
 * 统一的文件选择器
 */
export async function pickFiles(options: FilePickerOptions = {}): Promise<PickedFile[]> {
  const platform = currentPlatform.value

  if (platform === 'tauri') {
    // Tauri 文件选择
    const { open } = await import('@tauri-apps/plugin-dialog')
    const { readFile } = await import('@tauri-apps/plugin-fs')

    const selected = await open({
      multiple: options.multiple ?? false,
      filters: options.accept
        ? [
            {
              name: 'Files',
              extensions: options.accept.split(',').map((ext) => ext.trim().replace('.', '')),
            },
          ]
        : undefined,
    })

    if (!selected) return []

    const paths = Array.isArray(selected) ? selected : [selected]
    const files: PickedFile[] = []

    for (const path of paths) {
      const data = await readFile(path)
      const name = path.split(/[\\/]/).pop() || 'unknown'
      files.push({
        name,
        size: data.byteLength,
        type: '', // Tauri 不提供 MIME type
        data,
      })
    }

    return files
  }

  if (platform.startsWith('capacitor-')) {
    // Capacitor 文件选择（使用 Filesystem API）
    // 注意：Capacitor 的文件选择需要额外的插件
    // 这里使用标准的 Web API 作为后备
    return pickFilesWeb(options)
  }

  // Web 平台
  return pickFilesWeb(options)
}

/**
 * Web 平台的文件选择实现
 */
async function pickFilesWeb(options: FilePickerOptions): Promise<PickedFile[]> {
  return new Promise((resolve) => {
    const input = document.createElement('input')
    input.type = 'file'
    input.multiple = options.multiple ?? false
    if (options.accept) {
      input.accept = options.accept
    }

    input.onchange = async () => {
      if (!input.files) {
        resolve([])
        return
      }

      const files: PickedFile[] = []
      for (let i = 0; i < input.files.length; i++) {
        const file = input.files[i]
        const data = await file.arrayBuffer()
        files.push({
          name: file.name,
          size: file.size,
          type: file.type,
          data,
        })
      }

      resolve(files)
    }

    input.click()
  })
}

// 网络请求基础 URL
export function getApiBaseUrl(): string {
  const platform = currentPlatform.value

  if (platform === 'tauri') {
    // Tauri 桌面端连接本地后端
    return 'http://localhost:5001'
  }

  if (platform === 'capacitor-android') {
    // Android 模拟器访问宿主机
    return 'http://10.0.2.2:5001'
  }

  if (platform === 'capacitor-ios') {
    // iOS 模拟器访问宿主机
    return 'http://localhost:5001'
  }

  // Web 平台使用相对路径或环境变量
  return import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001'
}

// 系统通知
export async function showNotification(title: string, body: string): Promise<void> {
  const platform = currentPlatform.value

  if (platform === 'tauri') {
    // Tauri 原生通知
    const { sendNotification } = await import('@tauri-apps/plugin-notification')
    await sendNotification({ title, body })
    return
  }

  if (platform.startsWith('capacitor-')) {
    // Capacitor 本地通知
    const { LocalNotifications } = await import('@capacitor/local-notifications')
    await LocalNotifications.schedule({
      notifications: [
        {
          title,
          body,
          id: Date.now(),
          schedule: { at: new Date(Date.now() + 1000) },
        },
      ],
    })
    return
  }

  // Web 平台使用浏览器通知
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification(title, { body })
  } else if ('Notification' in window && Notification.permission !== 'denied') {
    const permission = await Notification.requestPermission()
    if (permission === 'granted') {
      new Notification(title, { body })
    }
  }
}

// 平台特性检测
export interface PlatformCapabilities {
  fileSystem: boolean
  notifications: boolean
  systemTray: boolean
  nativeMenus: boolean
}

export function getPlatformCapabilities(): PlatformCapabilities {
  const platform = currentPlatform.value

  if (platform === 'tauri') {
    return {
      fileSystem: true,
      notifications: true,
      systemTray: true,
      nativeMenus: true,
    }
  }

  if (platform.startsWith('capacitor-')) {
    return {
      fileSystem: true,
      notifications: true,
      systemTray: false,
      nativeMenus: false,
    }
  }

  return {
    fileSystem: false,
    notifications: 'Notification' in window,
    systemTray: false,
    nativeMenus: false,
  }
}

// 导出所有功能
export default {
  detectPlatform,
  currentPlatform,
  isWeb,
  isTauri,
  isCapacitor,
  isIOS,
  isAndroid,
  isMobile,
  isDesktop,
  pickFiles,
  getApiBaseUrl,
  showNotification,
  getPlatformCapabilities,
}
