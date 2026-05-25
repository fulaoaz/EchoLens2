import http, { unwrap } from './index'

// ---------- types -------------------------------------------------------------

export interface ReportSummary {
  id: string
  projectId: string
  title: string
  format: 'markdown' | 'pdf'
  url: string
  generatedAt: string
}

export interface ReportFull extends ReportSummary {
  markdown: string
  snapshot: Record<string, unknown>
}

// ---------- HTTP API ----------------------------------------------------------

export const reportApi = {
  async list(projectId: string): Promise<ReportSummary[]> {
    const resp = await http.get('/report', { params: { projectId } })
    return unwrap<ReportSummary[]>(resp)
  },
  async generate(projectId: string): Promise<ReportSummary> {
    const resp = await http.post('/report/generate', { projectId })
    return unwrap<ReportSummary>(resp)
  },
  async get(reportId: string): Promise<ReportFull> {
    const resp = await http.get(`/report/${reportId}`)
    return unwrap<ReportFull>(resp)
  },
  /** Returns the absolute URL the browser can hit directly for download. */
  downloadUrl(reportId: string): string {
    return `/api/report/${reportId}/download`
  },
  /** Self-contained HTML rendering — open in a browser and Print → Save as PDF. */
  downloadHtmlUrl(reportId: string): string {
    return `/api/report/${reportId}/download.html`
  },
}

export default reportApi
