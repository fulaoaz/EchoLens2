import http, { unwrap } from './index'
import type { AxiosResponse } from 'axios'

// ---------- types -------------------------------------------------------------

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface CampaignEntry {
  round: number
  stimulus: number
  price_pressure: number
}

export interface RunSimulationInput {
  num_agents?: number
  num_rounds?: number
  mean_degree?: number
  target_product_id?: string | null
  campaign_schedule?: CampaignEntry[]
  rng_seed?: number | null
}

export interface RoundMetrics {
  round: number
  avg_sentiment: number
  sentiment_std: number
  action_counts: Record<string, number>
  awareness: number
  purchase_rate: number
  boycott_rate: number
}

export interface JobConfig {
  num_agents: number
  num_rounds: number
  mean_degree: number
  target_product_id: string | null
  campaign_schedule: CampaignEntry[]
  rng_seed: number | null
}

export interface JobSnapshot {
  id: string
  project_id: string
  status: JobStatus
  created_at: string
  started_at: string | null
  finished_at: string | null
  config: JobConfig
  rounds_done: number
  total_rounds: number
  last_round_metrics: RoundMetrics | null
  error: string | null
}

export interface SimulationResult {
  project_id: string
  started_at: string
  finished_at: string
  config: JobConfig
  population: {
    size: number
    persona_counts: Record<string, number>
    avg_initial_sentiment: number
  }
  network: {
    nodes: number
    edges: number
    mean_degree: number
    max_degree: number
  }
  rounds: RoundMetrics[]
  final_sentiment: number[]
  final_action_totals: Record<string, number>
}

// ---------- HTTP API ----------------------------------------------------------

export const simulationApi = {
  async runSync(projectId: string, input: RunSimulationInput): Promise<SimulationResult> {
    const resp: AxiosResponse = await http.post(`/simulation/${projectId}/run`, input, {
      timeout: 120_000,
    })
    return unwrap<SimulationResult>(resp)
  },
  async runAsync(projectId: string, input: RunSimulationInput): Promise<JobSnapshot> {
    const resp: AxiosResponse = await http.post(`/simulation/${projectId}/run_async`, input)
    return unwrap<JobSnapshot>(resp)
  },
  async getJob(jobId: string): Promise<JobSnapshot> {
    const resp: AxiosResponse = await http.get(`/simulation/jobs/${jobId}`)
    return unwrap<JobSnapshot>(resp)
  },
  async getResult(jobId: string): Promise<SimulationResult> {
    const resp: AxiosResponse = await http.get(`/simulation/jobs/${jobId}/result`)
    return unwrap<SimulationResult>(resp)
  },
  async cancel(jobId: string): Promise<{ cancelled: boolean; job_id: string }> {
    const resp: AxiosResponse = await http.post(`/simulation/jobs/${jobId}/cancel`)
    return unwrap<{ cancelled: boolean; job_id: string }>(resp)
  },
  async listJobs(projectId: string): Promise<JobSnapshot[]> {
    const resp: AxiosResponse = await http.get(`/simulation/${projectId}/jobs`)
    return unwrap<JobSnapshot[]>(resp)
  },
}

// ---------- SSE helper --------------------------------------------------------

export type SimEventType = 'queued' | 'started' | 'round' | 'done' | 'failed' | 'cancelled'

export interface SimEvent {
  type: SimEventType
  timestamp?: string
  job_id?: string
  round?: number
  metrics?: RoundMetrics
  rounds_done?: number
  total_rounds?: number
  final_action_totals?: Record<string, number>
  rounds?: number
  error?: string
  heartbeat?: boolean
  project_id?: string
}

export interface JobEventStream {
  close(): void
}

/**
 * Subscribe to a job's SSE event stream. Returns a closer that detaches the
 * EventSource. Each `event:` block is wrapped in a uniform SimEvent.
 */
export function subscribeJobEvents(
  jobId: string,
  handler: (event: SimEvent) => void,
  onError?: (err: Event) => void,
): JobEventStream {
  const url = `/api/simulation/jobs/${jobId}/events`
  const es = new EventSource(url)

  const eventTypes: SimEventType[] = ['queued', 'started', 'round', 'done', 'failed', 'cancelled']
  for (const t of eventTypes) {
    es.addEventListener(t, (raw) => {
      const ev = raw as MessageEvent<string>
      try {
        const payload = JSON.parse(ev.data) as Omit<SimEvent, 'type'>
        handler({ type: t, ...payload })
      } catch {
        handler({ type: t })
      }
    })
  }

  if (onError) {
    es.onerror = onError
  }

  return {
    close() {
      es.close()
    },
  }
}

export default simulationApi
