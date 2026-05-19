import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, CartesianGrid,
} from 'recharts'
import { api } from '../api/client'

const OPERATOR_ID = 'default'

export default function ThresholdDashboard() {
  const queryClient = useQueryClient()
  const [overrideValue, setOverrideValue] = useState('')
  const [overrideError, setOverrideError] = useState('')

  const { data: current, isLoading: loadingCurrent } = useQuery({
    queryKey: ['threshold', OPERATOR_ID],
    queryFn: () => api.getThreshold(OPERATOR_ID),
    refetchInterval: 60_000,
  })

  const { data: history } = useQuery({
    queryKey: ['threshold-history', OPERATOR_ID],
    queryFn: () => api.getThresholdHistory(OPERATOR_ID),
    refetchInterval: 60_000,
  })

  const overrideMutation = useMutation({
    mutationFn: (value: number) => api.patchThreshold(OPERATOR_ID, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['threshold'] })
      queryClient.invalidateQueries({ queryKey: ['threshold-history'] })
      setOverrideValue('')
      setOverrideError('')
    },
  })

  const handleOverride = () => {
    const val = parseFloat(overrideValue)
    if (isNaN(val) || val < 0.55 || val > 0.80) {
      setOverrideError('Must be between 0.55 and 0.80')
      return
    }
    setOverrideError('')
    overrideMutation.mutate(val)
  }

  const chartData = history?.entries
    .slice()
    .reverse()
    .map(e => ({
      time: new Date(e.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      value: e.threshold_value,
      direction: e.direction,
    })) ?? []

  return (
    <div>
      <h1>Threshold Dashboard</h1>

      {loadingCurrent && <div className="loading">Loading threshold...</div>}

      {current && (
        <div className="threshold-grid">
          <div className="threshold-card">
            <div className="value">{current.threshold_immediate.toFixed(2)}</div>
            <div className="label">Immediate Threshold</div>
          </div>
          <div className="threshold-card">
            <div className="value">{current.threshold_counter.toFixed(2)}</div>
            <div className="label">Counter Threshold</div>
          </div>
          <div className="threshold-card">
            <div className="value">{current.threshold_adjusted.toFixed(2)}</div>
            <div className="label">Adjusted Threshold · {current.mode}</div>
          </div>
        </div>
      )}

      <div className="card">
        <h2>Manual Override</h2>
        <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '0.75rem' }}>
          Range: [0.55 – 0.80]. Overrides will be logged in threshold history.
        </p>
        <div className="override-row">
          <input
            type="number"
            step="0.01"
            min="0.55"
            max="0.80"
            placeholder="e.g. 0.68"
            value={overrideValue}
            onChange={e => setOverrideValue(e.target.value)}
          />
          <button className="btn btn-primary" onClick={handleOverride} disabled={overrideMutation.isPending}>
            Apply Override
          </button>
        </div>
        {overrideError && <div style={{ color: '#f87171', fontSize: '0.8rem', marginTop: '0.4rem' }}>{overrideError}</div>}
        {overrideMutation.isSuccess && <div style={{ color: '#86efac', fontSize: '0.8rem', marginTop: '0.4rem' }}>Override applied.</div>}
      </div>

      {chartData.length > 0 && (
        <div className="card">
          <h2>Threshold History</h2>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData} margin={{ top: 8, right: 16, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
              <XAxis dataKey="time" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis domain={[0.5, 0.85]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1a1f2e', border: '1px solid #2d3748', color: '#e2e8f0' }} />
              <ReferenceLine y={0.55} stroke="#ef4444" strokeDasharray="4 4" label={{ value: 'min', fill: '#ef4444', fontSize: 10 }} />
              <ReferenceLine y={0.80} stroke="#ef4444" strokeDasharray="4 4" label={{ value: 'max', fill: '#ef4444', fontSize: 10 }} />
              <Line type="stepAfter" dataKey="value" stroke="#f59e0b" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {history && history.entries.length > 0 && (
        <div className="card" style={{ padding: 0, overflow: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Value</th>
                <th>Direction</th>
                <th>FP Rate/hr</th>
                <th>TP Count/hr</th>
              </tr>
            </thead>
            <tbody>
              {history.entries.map((e, i) => (
                <tr key={i}>
                  <td>{new Date(e.created_at).toLocaleString()}</td>
                  <td>{e.threshold_value.toFixed(4)}</td>
                  <td>
                    {e.direction === 'UP' && <span style={{ color: '#f87171' }}>▲ UP</span>}
                    {e.direction === 'DOWN' && <span style={{ color: '#86efac' }}>▼ DOWN</span>}
                    {e.direction === 'MANUAL' && <span style={{ color: '#93c5fd' }}>✎ MANUAL</span>}
                    {!e.direction && '—'}
                  </td>
                  <td>{e.fp_rate_hourly?.toFixed(2) ?? '—'}</td>
                  <td>{e.tp_count_hourly ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
