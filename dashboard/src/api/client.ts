const API_KEY = import.meta.env.VITE_API_KEY ?? 'changeme'
const BASE = ''

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
      ...(options.headers ?? {}),
    },
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status} ${text}`)
  }
  return res.json() as Promise<T>
}

export interface EventSummary {
  event_id: string
  operator_id: string
  trigger_type: string
  outcome_tag: string | null
  graph_weight: number
  operator_validated: boolean | null
  shift_phase: string | null
  srk_level: string | null
  created_at: string
}

export interface EventListResponse {
  total: number
  page: number
  limit: number
  results: EventSummary[]
}

export interface ThresholdResponse {
  threshold_immediate: number
  threshold_counter: number
  threshold_adjusted: number
  mode: string
}

export interface ThresholdHistoryEntry {
  threshold_value: number
  direction: string | null
  fp_rate_hourly: number | null
  tp_count_hourly: number | null
  created_at: string
}

export interface ThresholdHistoryResponse {
  operator_id: string
  entries: ThresholdHistoryEntry[]
}

export const api = {
  listEvents: (params: Record<string, string | number | boolean | undefined>) => {
    const q = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') q.set(k, String(v))
    }
    return apiFetch<EventListResponse>(`/events?${q}`)
  },

  getEvent: (id: string) => apiFetch<Record<string, unknown>>(`/events/${id}`),

  patchFeedback: (id: string, operator_validated: boolean, notes?: string) =>
    apiFetch(`/events/${id}/feedback`, {
      method: 'PATCH',
      body: JSON.stringify({ operator_validated, notes }),
    }),

  getThreshold: (operator_id = 'default') =>
    apiFetch<ThresholdResponse>(`/config/threshold?operator_id=${operator_id}`),

  patchThreshold: (operator_id: string, threshold_adjusted: number) =>
    apiFetch(`/config/threshold?operator_id=${operator_id}`, {
      method: 'PATCH',
      body: JSON.stringify({ threshold_adjusted }),
    }),

  getThresholdHistory: (operator_id = 'default') =>
    apiFetch<ThresholdHistoryResponse>(`/config/threshold/history?operator_id=${operator_id}`),
}
