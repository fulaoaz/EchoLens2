import http, { unwrap } from './index'
import type { AxiosResponse } from 'axios'
import type { PredictionMetric } from './prediction'

// ---------- types -------------------------------------------------------------

export type RiskLevel = 'low' | 'elevated' | 'high'

export interface DecisionCoverage {
  simulation: boolean
  forecast: boolean
  causal: boolean
}

export interface DecisionKgFeatures {
  node_count?: number
  edge_count?: number
  kol_count?: number
  topic_count?: number
  product_count?: number
  brand_count?: number
  [key: string]: number | string | undefined
}

export interface DecisionSourceRunIds {
  simulation?: string
  forecast?: string
  causal?: string
}

export interface DecisionForecastConfidence {
  band_level?: number
  reliability?: number
  mape?: number
  smape?: number
  r2?: number
  n_observations?: number
  data_observed_ratio?: number
}

export interface DecisionCausalConfidence {
  p_value?: number
  significant?: boolean
  ci_low?: number | null
  ci_high?: number | null
  reliability?: number
  status?: string
}

export interface DecisionConfidenceRollup {
  forecast?: DecisionForecastConfidence
  causal?: DecisionCausalConfidence
  reliability?: number
}

export interface DecisionForecastCoverage {
  observed_days?: number
  total_days?: number
  observed_ratio?: number
  history_days?: number
  record_counts?: Record<string, number>
}

export interface DecisionCausalCoverage extends DecisionForecastCoverage {
  pre_days?: number
  post_days?: number
}

export interface DecisionSimulationBlock {
  job_id: string
  created_at: string
  config: {
    num_agents?: number
    num_rounds?: number
    rng_seed?: number | null
    kg_linked?: boolean
  }
  population: Record<string, unknown>
  network: {
    nodes?: number
    edges?: number
    mean_degree?: number
  }
  final_action_totals: Record<string, number>
  last_round: {
    round?: number
    avg_sentiment?: number
    awareness?: number
    purchase_rate?: number
    boycott_rate?: number
  }
  rounds_total: number
  evidence_ids: string[]
  kg_features: DecisionKgFeatures
  kg_linked: boolean
}

export interface DecisionForecastPoint {
  ts: string
  yhat: number
  yhat_lower: number
  yhat_upper: number
}

export interface DecisionForecastBlock {
  run_id: string
  metric: PredictionMetric
  metric_label: string
  unit: string
  headline: string
  delta_relative: number
  history: DecisionForecastPoint[]
  forecast: DecisionForecastPoint[]
  diagnostics: {
    mape: number
    r2: number
    trend_slope: number
    n_observations: number
  }
  risk_flags: string[]
  evidence_ids: string[]
  coverage: DecisionForecastCoverage
  confidence: DecisionForecastConfidence
  kg_features: DecisionKgFeatures
  kg_linked: boolean
  created_at: string
}

export interface DecisionCausalBlock {
  run_id: string
  metric: PredictionMetric
  status: 'ok' | 'insufficient_data' | 'no_post_window'
  intervention_start: string | null
  intervention_end: string | null
  ate: number | null
  ate_relative: number | null
  p_value: number | null
  ci_low: number | null
  ci_high: number | null
  narrative_seed: {
    direction?: 'up' | 'down' | 'flat'
    significant?: boolean
    abs_relative_pct?: number
  }
  evidence_ids: string[]
  coverage: DecisionCausalCoverage
  confidence: DecisionCausalConfidence
  kg_features: DecisionKgFeatures
  kg_linked: boolean
  created_at: string
}

export interface DecisionRisk {
  score: number // 0-100
  level: RiskLevel
  reasons: string[]
}

export interface DecisionRecommendation {
  id: string
  title: string
  priority: 'low' | 'medium' | 'high'
  rationale: string
  evidence: string[]
  tags: string[]
  source_run_ids?: DecisionSourceRunIds
  metric_trace?: Record<string, number | string>
}

export interface DecisionSnapshot {
  project_id: string
  coverage: DecisionCoverage
  simulation: DecisionSimulationBlock | null
  forecast: DecisionForecastBlock | null
  causal: DecisionCausalBlock | null
  risk: DecisionRisk
  recommendations: DecisionRecommendation[]
  evidence_ids: string[]
  kg_features: DecisionKgFeatures
  kg_linked: boolean
  confidence: DecisionConfidenceRollup
  source_run_ids: DecisionSourceRunIds
  model: string
}

// ---------- HTTP API ----------------------------------------------------------

export const decisionApi = {
  async snapshot(projectId: string): Promise<DecisionSnapshot> {
    const resp: AxiosResponse = await http.get(`/decision/${projectId}/snapshot`)
    return unwrap<DecisionSnapshot>(resp)
  },
}

export default decisionApi
