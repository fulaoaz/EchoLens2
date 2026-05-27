import axios from 'axios'
import { getApiBaseUrl } from '@/composables/usePlatform'
import type { ApiEnvelope } from './index'

export interface RuntimeSettings {
  llm_base_url: string
  llm_model_name: string
  llm_api_key_configured: boolean
}

export interface UpdateRuntimeSettingsInput {
  llm_base_url: string
  llm_model_name: string
  llm_api_key?: string
}

function client() {
  return axios.create({
    baseURL: `${getApiBaseUrl()}/api`,
    timeout: 20_000,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
  })
}

function unwrap<T>(body: ApiEnvelope<T> | T): T {
  if (body && typeof body === 'object' && 'data' in body && body.data !== undefined) {
    return body.data as T
  }
  return body as T
}

export const settingsApi = {
  async get(): Promise<RuntimeSettings> {
    const resp = await client().get<ApiEnvelope<RuntimeSettings> | RuntimeSettings>('/settings')
    return unwrap(resp.data)
  },

  async update(input: UpdateRuntimeSettingsInput): Promise<RuntimeSettings> {
    const resp = await client().put<ApiEnvelope<RuntimeSettings> | RuntimeSettings>('/settings', input)
    return unwrap(resp.data)
  },
}
