/**
 * 全局错误处理
 */

import { ref } from 'vue'
import type { AxiosError } from 'axios'

export interface ErrorInfo {
  id: string
  type: 'network' | 'server' | 'validation' | 'unknown'
  message: string
  detail?: string
  timestamp: number
  retryable: boolean
}

// 错误队列
const errors = ref<ErrorInfo[]>([])

// 错误计数器
let errorIdCounter = 0

/**
 * 生成错误 ID
 */
function generateErrorId(): string {
  return `error-${Date.now()}-${++errorIdCounter}`
}

/**
 * 解析 Axios 错误
 */
function parseAxiosError(error: AxiosError): Omit<ErrorInfo, 'id' | 'timestamp'> {
  const status = error.response?.status

  // 网络错误
  if (!error.response) {
    return {
      type: 'network',
      message: '网络连接失败',
      detail: '请检查网络连接后重试',
      retryable: true,
    }
  }

  // 服务器错误
  if (status && status >= 500) {
    return {
      type: 'server',
      message: '服务器错误',
      detail: `服务器返回 ${status} 错误，请稍后重试`,
      retryable: true,
    }
  }

  // 客户端错误
  if (status === 400) {
    const responseData = error.response?.data as { message?: string } | undefined
    return {
      type: 'validation',
      message: '请求参数错误',
      detail: responseData?.message || '请检查输入参数',
      retryable: false,
    }
  }

  if (status === 401) {
    return {
      type: 'validation',
      message: '未授权',
      detail: '请先登录',
      retryable: false,
    }
  }

  if (status === 403) {
    return {
      type: 'validation',
      message: '权限不足',
      detail: '您没有权限访问该资源',
      retryable: false,
    }
  }

  if (status === 404) {
    return {
      type: 'validation',
      message: '资源不存在',
      detail: '请求的资源未找到',
      retryable: false,
    }
  }

  // 未知错误
  return {
    type: 'unknown',
    message: '未知错误',
    detail: error.message || '发生了未知错误',
    retryable: false,
  }
}

/**
 * 添加错误
 */
export function addError(error: Error | AxiosError | string): ErrorInfo {
  let errorInfo: Omit<ErrorInfo, 'id' | 'timestamp'>

  if (typeof error === 'string') {
    errorInfo = {
      type: 'unknown',
      message: error,
      retryable: false,
    }
  } else if ('isAxiosError' in error && error.isAxiosError) {
    errorInfo = parseAxiosError(error as AxiosError)
  } else {
    errorInfo = {
      type: 'unknown',
      message: error.message || '发生了未知错误',
      retryable: false,
    }
  }

  const fullError: ErrorInfo = {
    ...errorInfo,
    id: generateErrorId(),
    timestamp: Date.now(),
  }

  errors.value.push(fullError)

  // 自动清理旧错误（保留最近 10 条）
  if (errors.value.length > 10) {
    errors.value.shift()
  }

  return fullError
}

/**
 * 移除错误
 */
export function removeError(id: string): void {
  const index = errors.value.findIndex((e) => e.id === id)
  if (index !== -1) {
    errors.value.splice(index, 1)
  }
}

/**
 * 清空所有错误
 */
export function clearErrors(): void {
  errors.value = []
}

/**
 * 错误处理 composable
 */
export function useErrorHandler() {
  return {
    errors,
    addError,
    removeError,
    clearErrors,
  }
}

/**
 * 全局错误处理器（用于 Vue app.config.errorHandler）
 */
export function globalErrorHandler(error: Error): void {
  console.error('Global error:', error)
  addError(error)
}

/**
 * 未捕获的 Promise 错误处理器
 */
export function unhandledRejectionHandler(event: PromiseRejectionEvent): void {
  console.error('Unhandled promise rejection:', event.reason)
  addError(event.reason)
}

/**
 * 安装全局错误处理器
 */
export function installGlobalErrorHandlers(): void {
  if (typeof window === 'undefined') return

  window.addEventListener('unhandledrejection', unhandledRejectionHandler)
}

/**
 * 卸载全局错误处理器
 */
export function uninstallGlobalErrorHandlers(): void {
  if (typeof window === 'undefined') return

  window.removeEventListener('unhandledrejection', unhandledRejectionHandler)
}
