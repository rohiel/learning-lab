import React, { useState } from 'react'
import { api } from '../api.js'
import { Spinner, ErrorBox, Stat, ghostBtn } from '../ui.jsx'

export default function ParentReview({ student, progress, onExit }) {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const daysDone = (progress?.days || []).filter(d => d.done).length
  const weak = progress?.weak_spots || { math: [], english: [] }

  async function run() {
    setLoading(true); setError(null)
    try { const r = await api.review(student.id); setResult(r.review) }
    catch (e) { setError(e.status === 409 ? 'No completed sessions yet. Once Anam finishes a few, come back for the analysis.' : e.message) }
    setLoading(false)
  }

  function exportLog() {
    const blob = new Blob([JSON.stringify(progress, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'anam_progress_' + new Date().toISOString().slice(0, 10) + '.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '20px 18px 60px' }}>
      <button onClick={onExit} style={{ background: 'var(--bg-card)', color: 'var(--text-soft)', padding: '8px 14px', borderRadius: 10, fontWeight: 700, marginBottom: 18 }}>← Back</button>
      <div className="display" style={{ fontSize: 26, fontWeight: 600, marginBottom: 6 }}>📊 Parent review</div>
      <div style={{ color: 'var(--text-soft)', marginBottom: 18 }}>
        An honest analysis of where {student.name} stands and what to target next.
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
        <Stat label="Days completed" value={daysDone} />
        <Stat label="Total help asks" value={progress?.help_total || 0} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 18 }}>
        <Stat label="Math weak spots" value={(weak.math || []).length} />
        <Stat label="English weak spots" value={(weak.english || []).length} />
      </div>

      <div style={{ display: 'flex', gap: 10, marginBottom: 18 }}>
        <button disabled={loading} onClick={run}
          style={{ flex: 2, padding: '15px', borderRadius: 14, background: 'linear-gradient(90deg,#2563eb,#3b82f6)', color: '#fff', fontWeight: 700, fontSize: 16, opacity: loading ? 0.7 : 1 }}>
          {loading ? 'Analyzing…' : 'Generate analysis'}
        </button>
        <button onClick={exportLog} style={{ ...ghostBtn, flex: 1 }}>⬇ Export data</button>
      </div>

      {loading && <Spinner label="Reading the session log…" />}
      {error && <ErrorBox error={error} />}
      {result && (
        <div style={{ background: 'var(--bg-card)', borderRadius: 18, padding: '22px', border: '1px solid var(--border)', lineHeight: 1.65, fontSize: 15.5, whiteSpace: 'pre-wrap' }}>
          {result}
        </div>
      )}
    </div>
  )
}
