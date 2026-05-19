import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { api } from '../api/client'

function DetailRow({ label, value }: { label: string; value: unknown }) {
  if (value === null || value === undefined) return null
  return (
    <div className="detail-row">
      <span className="detail-label">{label}</span>
      <span className="detail-value">{String(value)}</span>
    </div>
  )
}

export default function EventDetail() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()

  const { data: ev, isLoading, error } = useQuery({
    queryKey: ['event', id],
    queryFn: () => api.getEvent(id!),
    enabled: !!id,
  })

  const feedbackMutation = useMutation({
    mutationFn: ({ validated, notes }: { validated: boolean; notes?: string }) =>
      api.patchFeedback(id!, validated, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['event', id] })
      queryClient.invalidateQueries({ queryKey: ['events'] })
    },
  })

  if (isLoading) return <div className="loading">Loading event...</div>
  if (error || !ev) return <div className="error">Event not found</div>

  const cause = ev.cause as Record<string, unknown> | undefined
  const intuition = ev.intuition as Record<string, unknown> | undefined
  const action = ev.action as Record<string, unknown> | undefined
  const result = ev.result as Record<string, unknown> | undefined
  const preEnv = ev.pre_env as Record<string, unknown> | undefined
  const biometric = ev.biometric_snapshot as Record<string, unknown> | undefined
  const tc = (cause?.trigger_context as Record<string, unknown> | undefined)
  const scores = (tc?.signal_scores as Record<string, number> | undefined)
  const feedback = (tc?.feedback as Record<string, unknown> | undefined)
  const shadowActions = (ev.shadow_actions as Array<Record<string, unknown>>) ?? []
  const visual = ((preEnv?.sensory_baseline as Record<string, unknown> | undefined)?.visual as Record<string, unknown> | undefined)

  const scoreData = scores
    ? [
        { name: 'Gaze', value: scores.gaze ?? 0 },
        { name: 'Hand', value: scores.hand ?? 0 },
        { name: 'HRV', value: scores.hrv ?? 0 },
        { name: 'Acoustic', value: scores.acoustic ?? 0 },
      ]
    : []

  const currentLabel = feedback?.operator_validated

  return (
    <div>
      <Link to="/events" className="back-link">← Back to Events</Link>
      <h1>Event Detail</h1>
      <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '1rem' }}>{id}</div>

      <div className="detail-grid">
        <div className="card">
          <h2>Cause</h2>
          <DetailRow label="Description" value={cause?.description} />
          <DetailRow label="Trigger Type" value={cause?.trigger_type} />
          <DetailRow label="Timestamp" value={cause?.timestamp} />
          <DetailRow label="Operational Mode" value={tc?.operational_mode} />
          <DetailRow label="Trigger Channels" value={(cause?.trigger_channels as string[] | undefined)?.join(', ')} />
        </div>

        <div className="card">
          <h2>Intuition</h2>
          <DetailRow label="Hypothesis" value={intuition?.hypothesis} />
          <DetailRow label="SRK Level" value={intuition?.srk_level} />
          <DetailRow label="Confirmed" value={String(intuition?.hypothesis_confirmed ?? '—')} />
          <DetailRow label="Confidence" value={intuition?.confidence != null ? Number(intuition.confidence).toFixed(3) : undefined} />
        </div>

        <div className="card">
          <h2>Action</h2>
          <DetailRow label="Description" value={action?.description} />
          <DetailRow label="Tool Used" value={action?.tool_used} />
        </div>

        <div className="card">
          <h2>Result</h2>
          <DetailRow label="Outcome" value={result?.outcome_tag} />
          <DetailRow label="Graph Weight" value={result?.graph_weight} />
          <DetailRow label="Notes" value={result?.notes} />
          <DetailRow label="Withhold Sample" value={String(result?.withhold_sample ?? false)} />
        </div>

        <div className="card">
          <h2>Environment</h2>
          <DetailRow label="Operator" value={preEnv?.operator_id} />
          <DetailRow label="Shift Phase" value={preEnv?.shift_phase} />
          <DetailRow label="Ambient Temp (°F)" value={preEnv?.ambient_temp_f} />
          <DetailRow label="Batch ID" value={preEnv?.material_batch_id} />
        </div>

        <div className="card">
          <h2>Biometrics</h2>
          <DetailRow label="HR (bpm)" value={biometric?.hr_bpm} />
          <DetailRow label="HRV RMSSD (ms)" value={biometric?.hrv_rmssd_ms} />
          <DetailRow label="Skin Temp (°C)" value={biometric?.skin_temp_c} />
          <DetailRow label="Device" value={biometric?.source_device} />
        </div>
      </div>

      {scoreData.length > 0 && (
        <div className="card">
          <h2>Signal Scores</h2>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={scoreData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <YAxis domain={[0, 1]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1a1f2e', border: '1px solid #2d3748', color: '#e2e8f0' }} />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {scoreData.map((entry, i) => (
                  <Cell key={i} fill={entry.value >= 0.65 ? '#f59e0b' : '#3b82f6'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {shadowActions.length > 0 && (
        <div className="card">
          <h2>Shadow Actions</h2>
          {shadowActions.map((sa, i) => (
            <div key={i} style={{ marginBottom: '0.75rem', paddingBottom: '0.75rem', borderBottom: '1px solid #1e2532' }}>
              <div style={{ fontWeight: 500, marginBottom: '0.2rem' }}>{sa.description as string}</div>
              <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                Rejected: {sa.rejection_rationale as string} · SRK: {sa.srk_level as string}
              </div>
            </div>
          ))}
        </div>
      )}

      {typeof visual?.frame_path === 'string' && (
        <div className="card">
          <h2>Pre-Trigger Frame</h2>
          <img
            src={`/media/frames/${visual.frame_path.split('/').pop()}`}
            alt="Pre-trigger frame"
            style={{ maxWidth: '100%', borderRadius: 6, border: '1px solid #2d3748' }}
          />
        </div>
      )}

      <div className="card">
        <h2>FP / TP Label</h2>
        {currentLabel !== undefined && currentLabel !== null && (
          <div style={{ marginBottom: '0.75rem', fontSize: '0.875rem', color: '#94a3b8' }}>
            Current label: {currentLabel === true
              ? <span className="badge badge-tp">Genuine Insight (TP)</span>
              : <span className="badge badge-fp">False Positive (FP)</span>
            }
          </div>
        )}
        <div className="fp-tp-buttons">
          <button
            className="btn btn-tp"
            onClick={() => feedbackMutation.mutate({ validated: true })}
            disabled={feedbackMutation.isPending}
          >
            Genuine Insight (TP)
          </button>
          <button
            className="btn btn-fp"
            onClick={() => feedbackMutation.mutate({ validated: false })}
            disabled={feedbackMutation.isPending}
          >
            False Positive (FP)
          </button>
        </div>
        {feedbackMutation.isSuccess && (
          <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: '#86efac' }}>Label saved.</div>
        )}
      </div>
    </div>
  )
}
