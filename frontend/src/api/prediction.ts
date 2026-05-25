import http, { unwrap } from './index'
import type { AxiosResponse } from 'axios'

// ---------- types -------------------------------------------------------------

export type PredictionMetric = 'volume' | 'sentiment' | 'gmv_synth' | 'negative_ratio'

export type PredictionKind = 'forecast' | 'causal' | 'fused'
export type PredictionStatus = 'completed' | 'failed'

export interface ForecastInput {
  metric?: PredictionMetric
  horizon_days?: number
  seasonality_period?: number
  confidence?: number
}

export interface CausalInput {
  metric?: PredictionMetric
  intervention_start: string // ISO date
  intervention_end?: string | null
}

export interface ForecastPoint {
  ts: string
  yhat: number
  yhat_lower: number
  yhat_upper: number
}

export interface FitDiagnostics {
  n_observations: number
  trend_slope: number
  trend_intercept: number
  seasonal_amplitude: number
  residual_std: number
  mape: number
  smape: number
  r2: number
}

export interface ForecastResult {
  history: ForecastPoint[]
  forecast: ForecastPoint[]
  diagnostics: FitDiagnostics
  config: {
    horizon_days: number
    seasonality_period: number
    confidence: number
    floor: number | null
    model: string
  }
}

export interface ExplanationBullet {
  text: string
  evidence: string[]
}

export interface ExplanationPayload {
  metric: PredictionMetric
  metric_label: string
  unit: string
  headline: string
  bullets: ExplanationBullet[]
  evidence_index: Record<string, number | string | null>
  risk_flags: string[]
  labels: { trend: string; mape: string; seasonality: string }
  delta_relative: number
  model: string
}

export interface ForecastPayload {
  history_window: {
    start_date: string
    end_date: string
    days: number
    avg_price: number | null
  }
  forecast: ForecastResult
  explanation: ExplanationPayload
}

export interface CausalSeriesPoint {
  date: string
  value: number
}

export interface CausalPayload {
  status: 'ok' | 'insufficient_data' | 'no_post_window'
  metric: PredictionMetric
  intervention_start: string
  intervention_end: string | null
  ate: number
  ate_relative: number
  p_value: number
  ci_low: number
  ci_high: number
  pre_mean: number
  post_mean: number
  post_counterfactual_mean: number
  pre_days: number
  post_days: number
  pre_series: CausalSeriesPoint[]
  post_series: CausalSeriesPoint[]
  counterfactual_series: CausalSeriesPoint[]
  narrative_seed: {
    direction: 'up' | 'down' | 'flat'
    significant: boolean
    abs_relative_pct: number
  }
  model: string
}

export interface PredictionRunSnapshot {
  id: string
  project_id: string
  kind: PredictionKind
  status: PredictionStatus
  created_at: string
  metric: PredictionMetric
  config: Record<string, unknown>
  error: string | null
}

export interface PredictionRun extends PredictionRunSnapshot {
  result: ForecastPayload | CausalPayload
}

// Legacy alias kept for runs store compatibility.
export type { PredictionRun as PredictionRunFull }

// ---------- HTTP API ----------------------------------------------------------

export const predictionApi = {
  async forecast(projectId: string, input: ForecastInput = {}): Promise<PredictionRun> {
    const resp: AxiosResponse = await http.post(`/prediction/${projectId}/forecast`, input, {
      timeout: 60_000,
    })
    return unwrap<PredictionRun>(resp)
  },
  async causal(projectId: string, input: CausalInput): Promise<PredictionRun> {
    const resp: AxiosResponse = await http.post(`/prediction/${projectId}/causal`, input, {
      timeout: 60_000,
    })
    return unwrap<PredictionRun>(resp)
  },
  async getRun(runId: string): Promise<PredictionRun> {
    const resp: AxiosResponse = await http.get(`/prediction/runs/${runId}`)
    return unwrap<PredictionRun>(resp)
  },
  async listRuns(projectId: string): Promise<PredictionRunSnapshot[]> {
    const resp: AxiosResponse = await http.get(`/prediction/${projectId}/runs`)
    return unwrap<PredictionRunSnapshot[]>(resp)
  },
}

export default predictionApi
