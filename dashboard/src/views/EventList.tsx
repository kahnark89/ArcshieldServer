import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api, type EventSummary } from '../api/client'

function outcomeBadge(tag: string | null) {
  const cls = `badge badge-${(tag ?? 'unknown').toLowerCase().replace('_', '_')}`
  return <span className={cls}>{tag ?? 'UNKNOWN'}</span>
}

function validatedBadge(v: boolean | null) {
  if (v === true) return <span className="badge badge-tp">TP</span>
  if (v === false) return <span className="badge badge-fp">FP</span>
  return <span className="badge badge-null">—</span>
}

export default function EventList() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [outcomeTag, setOutcomeTag] = useState('')
  const [validated, setValidated] = useState('')
  const [srkLevel, setSrkLevel] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const limit = 50

  const params = {
    page,
    limit,
    outcome_tag: outcomeTag || undefined,
    operator_validated: validated === '' ? undefined : validated === 'true',
    srk_level: srkLevel || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  }

  const { data, isLoading, error } = useQuery({
    queryKey: ['events', params],
    queryFn: () => api.listEvents(params as Record<string, string | number | boolean | undefined>),
  })

  const totalPages = data ? Math.ceil(data.total / limit) : 1

  return (
    <div>
      <h1>Events</h1>

      <div className="filters">
        <div className="filter-group">
          <label>Outcome</label>
          <select value={outcomeTag} onChange={e => { setOutcomeTag(e.target.value); setPage(1) }}>
            <option value="">All</option>
            {['PREVENTED','RESOLVED','IMPROVED','NO_CHANGE','WORSE','UNKNOWN'].map(o =>
              <option key={o} value={o}>{o}</option>
            )}
          </select>
        </div>
        <div className="filter-group">
          <label>Label</label>
          <select value={validated} onChange={e => { setValidated(e.target.value); setPage(1) }}>
            <option value="">All</option>
            <option value="true">TP (genuine)</option>
            <option value="false">FP (false positive)</option>
          </select>
        </div>
        <div className="filter-group">
          <label>SRK Level</label>
          <select value={srkLevel} onChange={e => { setSrkLevel(e.target.value); setPage(1) }}>
            <option value="">All</option>
            {['SKILL','RULE','KNOWLEDGE'].map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div className="filter-group">
          <label>From</label>
          <input type="date" value={dateFrom} onChange={e => { setDateFrom(e.target.value); setPage(1) }} />
        </div>
        <div className="filter-group">
          <label>To</label>
          <input type="date" value={dateTo} onChange={e => { setDateTo(e.target.value); setPage(1) }} />
        </div>
      </div>

      {isLoading && <div className="loading">Loading events...</div>}
      {error && <div className="error">Error loading events</div>}

      {data && (
        <>
          <div style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
            {data.total} event{data.total !== 1 ? 's' : ''}
          </div>
          <div className="card" style={{ padding: 0, overflow: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Operator</th>
                  <th>Trigger</th>
                  <th>Shift</th>
                  <th>SRK</th>
                  <th>Outcome</th>
                  <th>Weight</th>
                  <th>Label</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((ev: EventSummary) => (
                  <tr key={ev.event_id} onClick={() => navigate(`/events/${ev.event_id}`)}>
                    <td>{new Date(ev.created_at).toLocaleString()}</td>
                    <td>{ev.operator_id}</td>
                    <td>{ev.trigger_type}</td>
                    <td>{ev.shift_phase ?? '—'}</td>
                    <td>{ev.srk_level ?? '—'}</td>
                    <td>{outcomeBadge(ev.outcome_tag)}</td>
                    <td>{ev.graph_weight.toFixed(2)}</td>
                    <td>{validatedBadge(ev.operator_validated)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <button onClick={() => setPage(p => p - 1)} disabled={page === 1}>Prev</button>
            <span>Page {page} / {totalPages}</span>
            <button onClick={() => setPage(p => p + 1)} disabled={page >= totalPages}>Next</button>
          </div>
        </>
      )}
    </div>
  )
}
