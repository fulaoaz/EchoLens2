import http, { unwrap } from './index'

export type CrawlJobSource = 'manual_url' | 'material_search' | string

export interface CrawlJob {
  id: string
  projectId: string
  platform: string
  sourceUrl?: string
  keyword?: string
  source?: CrawlJobSource
  status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled'
  progress: number
  itemsCollected: number
  startedAt?: string
  finishedAt?: string
  error?: string
}

export interface StartCrawlInput {
  projectId: string
  platforms?: string[]
  sourceUrls?: string[]
  materialText?: string
  maxTargets?: number
}

export const crawlerApi = {
  async listJobs(projectId: string): Promise<CrawlJob[]> {
    const resp = await http.get<CrawlJob[]>(`/crawler/jobs`, { params: { projectId } })
    return unwrap<CrawlJob[]>(resp)
  },
  async start(input: StartCrawlInput): Promise<CrawlJob[]> {
    const payload: Record<string, unknown> = { projectId: input.projectId }
    if (input.platforms && input.platforms.length) payload.platforms = input.platforms
    if (input.sourceUrls && input.sourceUrls.length) payload.sourceUrls = input.sourceUrls
    if (input.materialText && input.materialText.trim()) {
      payload.materialText = input.materialText
    }
    if (input.maxTargets && Number.isFinite(input.maxTargets)) {
      payload.maxTargets = input.maxTargets
    }
    const resp = await http.post<CrawlJob[]>(`/crawler/start`, payload)
    return unwrap<CrawlJob[]>(resp)
  },
  async cancel(jobId: string): Promise<CrawlJob> {
    const resp = await http.post<CrawlJob>(`/crawler/jobs/${jobId}/cancel`)
    return unwrap<CrawlJob>(resp)
  },
}
