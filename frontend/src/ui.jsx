import React from 'react'

export const ghostBtn = {
  flex: 1, padding: '13px', borderRadius: 14, background: 'var(--bg-card)',
  color: 'var(--text-soft)', fontWeight: 700, fontSize: 14.5, border: '1px solid var(--border)',
}

export function Spinner({ label }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16, padding: '40px 0' }}>
      <div className="spinner" />
      {label && <div style={{ color: 'var(--text-soft)', fontWeight: 600 }}>{label}</div>}
    </div>
  )
}

export function Section({ label, children }) {
  return (
    <div style={{ marginBottom: 22, animation: 'slideIn .5s ease' }}>
      <div style={{ fontSize: 13, fontWeight: 800, letterSpacing: '1px', textTransform: 'uppercase',
        color: 'var(--text-dim)', marginBottom: 10 }}>{label}</div>
      {children}
    </div>
  )
}

export function BigToggle({ active, onClick, color, emoji, title, sub }) {
  return (
    <button onClick={onClick}
      style={{
        padding: '18px 16px', borderRadius: 16, textAlign: 'left',
        background: active ? `linear-gradient(160deg,${color},${color}cc)` : 'var(--bg-card)',
        border: '2px solid ' + (active ? '#fff8' : 'transparent'),
        color: active ? '#fff' : 'var(--text-soft)', transition: 'all .15s',
      }}>
      <div style={{ fontSize: 30 }}>{emoji}</div>
      <div className="display" style={{ fontWeight: 600, fontSize: 20, marginTop: 4 }}>{title}</div>
      <div style={{ fontSize: 13, opacity: 0.85, marginTop: 2, lineHeight: 1.35 }}>{sub}</div>
    </button>
  )
}

export function Stat({ label, value }) {
  return (
    <div style={{ background: 'var(--bg-card)', borderRadius: 14, padding: '14px' }}>
      <div style={{ fontSize: 12, color: 'var(--text-dim)', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</div>
      <div className="display" style={{ fontSize: 22, fontWeight: 600, marginTop: 4 }}>{value}</div>
    </div>
  )
}

export function CenterWrap({ children, onExit }) {
  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '30px 18px' }}>
      {onExit && <button onClick={onExit} style={{ background: 'var(--bg-card)', color: 'var(--text-soft)',
        padding: '8px 14px', borderRadius: 10, fontWeight: 700, marginBottom: 18 }}>← Exit</button>}
      {children}
    </div>
  )
}

export function ErrorBox({ error }) {
  return (
    <div style={{ background: 'linear-gradient(160deg,#7f1d1d,#991b1b)', borderRadius: 16,
      padding: '18px 20px', lineHeight: 1.5 }}>
      <div className="display" style={{ fontWeight: 600, fontSize: 18, marginBottom: 6 }}>Something went wrong</div>
      <div style={{ fontSize: 14.5, color: '#fecaca' }}>{String(error)}</div>
    </div>
  )
}
