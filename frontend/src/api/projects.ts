import http, { unwrap } from './index'
import type { AxiosResponse } from 'axios'

export type ProjectStatus =
  | 'created'
  | 'crawling'
  | 'seed_ready'
  | 'simulating'
  | 'predicting'
  | 'ready'
  | 'failed'

export interface Project {
  id: string
  name: string
  description: string
  keywords: string[]
  target_platforms: string[]
  status: ProjectStatus
  created_at: string
  updated_at: string
}

export interface CreateProjectInput {
  name: string
  description?: string
  keywords?: string[]
  target_platforms?: string[]
}

export interface ProjectListResult {
  items: Project[]
  count: number
}

export interface SeedRecord {
  id?: string | number
  platform?: string
  title?: string
  brand?: string
  price_current?: number
  price_original?: number
  content?: string
  sentiment?: 'positive' | 'negative' | 'neutral' | 'mixed' | 'unknown'
  author_hash?: string
  posted_at?: string
  crawled_at?: string
  [key: string]: unknown
}

export interface SeedDataInput {
  products?: SeedRecord[]
  reviews?: SeedRecord[]
  posts?: SeedRecord[]
}

export interface SeedReportCounts {
  products: number
  reviews: number
  posts: number
  cross_platform_groups: number
}

export interface TimelineBucket {
  date: string
  sentiment: string
  count: number
}

export interface TopKol {
  author_hash: string
  post_count: number
}

export interface SeedReport {
  project_id: string
  generated_at: string
  counts: SeedReportCounts
  products: Array<{
    id?: string
    platform?: string
    title?: string
    brand?: string
    price_current?: number
  }>
  review_sentiment_distribution: Record<string, number>
  sentiment_volume_timeline: TimelineBucket[]
  top_kols: TopKol[]
  cross_platform_groups: Record<string, string[]>
  summary_text: string
}

export const projectsApi = {
  async list(): Promise<ProjectListResult> {
    const resp: AxiosResponse = await http.get('/projects')
    return unwrap<ProjectListResult>(resp)
  },
  async get(id: string): Promise<Project> {
    const resp: AxiosResponse = await http.get(`/projects/${id}`)
    return unwrap<Project>(resp)
  },
  async create(input: CreateProjectInput): Promise<Project> {
    const resp: AxiosResponse = await http.post('/projects', input)
    return unwrap<Project>(resp)
  },
  async remove(id: string): Promise<{ deleted: string }> {
    const resp: AxiosResponse = await http.delete(`/projects/${id}`)
    return unwrap<{ deleted: string }>(resp)
  },
  async ingestSeedData(id: string, input: SeedDataInput): Promise<{ ingested: SeedReportCounts }> {
    const resp: AxiosResponse = await http.post(`/projects/${id}/seed_data`, input)
    return unwrap<{ ingested: SeedReportCounts }>(resp)
  },
  async getSeedReport(id: string): Promise<SeedReport> {
    const resp: AxiosResponse = await http.get(`/projects/${id}/seed_report`)
    return unwrap<SeedReport>(resp)
  },
}

export default projectsApi
