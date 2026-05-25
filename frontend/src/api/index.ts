import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'

/** Backend response envelope (best-effort: tolerates plain payloads too). */
export interface ApiEnvelope<T = unknown> {
  success?: boolean
  code?: number
  data?: T
  message?: string
  error?: string
}

interface RetryConfig extends AxiosRequestConfig {
  __retryCount?: number
  __maxRetries?: number
}

const DEFAULT_TIMEOUT_MS = 20_000
const MAX_RETRIES = 2
const RETRY_BACKOFF_MS = 400

const http: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: DEFAULT_TIMEOUT_MS,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
})

http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  // Future: attach auth token / project header here.
  return config
})

http.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error) => {
    const config = (error?.config ?? {}) as RetryConfig
    const status = error?.response?.status
    const isNetworkOrIdempotent =
      !error?.response ||
      status >= 500 ||
      ['get', 'head', 'options'].includes((config.method ?? 'get').toLowerCase())

    config.__retryCount = config.__retryCount ?? 0
    const max = config.__maxRetries ?? MAX_RETRIES

    if (isNetworkOrIdempotent && config.__retryCount < max) {
      config.__retryCount += 1
      const delay = RETRY_BACKOFF_MS * 2 ** (config.__retryCount - 1)
      await new Promise((r) => setTimeout(r, delay))
      return http(config)
    }
    return Promise.reject(error)
  },
)

export function unwrap<T>(resp: AxiosResponse<ApiEnvelope<T> | T>): T {
  const body = resp.data as ApiEnvelope<T> & T
  if (body && typeof body === 'object' && 'data' in body && body.data !== undefined) {
    return body.data as T
  }
  return body as T
}

export default http
