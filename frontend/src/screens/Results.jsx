import React from 'react'
import { MODES } from '../curriculum.js'
import { Stat } from '../ui.jsx'

export default function Results({ session, onHome }) {
  const pct = Math.round((session.score / Math.max(session.total, 1)) * 100)
  const msg = pct >= 90 ? 'Outstanding! 🏆' : pct >= 70 ? 'Great work! 🌟' : pct >= 50 ? 'Solid effort — gaps spotted 💪' : 'We found the spots to work on 🔍'
  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '30px 18px 60px', textAlign: 'center' }}>
      <div className="display" style={{ fontSize: 30, fontWeight: 700 }}>{msg}</div>
      <div style={{ margin: '24px auto', width: 170, height: 170, borderRadius: '50%',
        background: `conic-gradient(#22c55e ${pct * 3.6}deg, var(--bg-card) 0deg)`,
        display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ width: 140, height: 140, borderRadius: '50%', background: 'var(--bg-deep)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <div className="display" style={{ fontSize: 44, fontWeight: 700, color: '#fcd34d' }}>{pct}%</div>
          <div style={{ color: 'var(--text-dim)', fontWeight: 700 }}>{session.score}/{session.total}</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 18 }}>
        <Stat label="Top level reached" value={'Level ' + session.maxLevel} />
        <Stat label="Mode" value={(MODES[session.mode] || { label: session.mode }).label} />
        <Stat label="Help asks" value={session.helpRequests || 0} />
      </div>

      {session.weakSkills && session.weakSkills.length > 0 && (
        <div style={{ background: 'var(--bg-card)', borderRadius: 16, padding: '16px 18px', textAlign: 'left', marginBottom: 14, border: '1px solid var(--border)' }}>
          <div style={{ fontWeight: 800, color: '#fca5a5', marginBottom: 8 }}>🎯 Spots to work on next time</div>
          {session.weakSkills.map((s, i) => (
            <div key={i} style={{ padding: '6px 0', color: 'var(--text-soft)', borderBottom: i < session.weakSkills.length - 1 ? '1px solid var(--border)' : 'none' }}>• {s}</div>
          ))}
        </div>
      )}

      {session.retentionResults && session.retentionResults.length > 0 && (
        <div style={{ background: 'var(--bg-card)', borderRadius: 16, padding: '16px 18px', textAlign: 'left', marginBottom: 14, border: '1px solid var(--border)' }}>
          <div style={{ fontWeight: 800, color: '#93c5fd', marginBottom: 8 }}>🧠 Memory check (did it stick?)</div>
          {session.retentionResults.map((r, i) => (
            <div key={i} style={{ padding: '5px 0', color: 'var(--text-soft)' }}>
              {r.correct ? '✅' : '🔁'} {r.skill} {r.correct ? '— remembered!' : "— we'll revisit this"}
            </div>
          ))}
        </div>
      )}

      <button onClick={onHome} style={{ width: '100%', padding: '16px', borderRadius: 16, background: 'linear-gradient(90deg,#16a34a,#22c55e)', color: '#fff', fontFamily: "'Fredoka',sans-serif", fontWeight: 600, fontSize: 20, marginTop: 8 }}>
        Back to start
      </button>
      <div style={{ fontSize: 13, color: 'var(--text-dim)', marginTop: 14 }}>Tip for parent: screenshot this for your weekly log.</div>
    </div>
  )
}
