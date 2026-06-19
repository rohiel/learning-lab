import React, { useState, useRef } from 'react'
import { api } from '../api.js'
import { Spinner, ErrorBox, ghostBtn } from '../ui.jsx'

export default function WorkUpload({ onExit }) {
  const [image, setImage] = useState(null)   // {file, preview}
  const [context, setContext] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const fileRef = useRef()

  function onFile(e) {
    const f = e.target.files[0]
    if (!f) return
    const reader = new FileReader()
    reader.onload = () => { setImage({ file: f, preview: reader.result }); setResult(null); setError(null) }
    reader.readAsDataURL(f)
  }

  async function analyze() {
    if (!image) return
    setLoading(true); setError(null)
    try { const r = await api.analyzeWork(image.file, context); setResult(r.feedback) }
    catch (e) { setError(e.message) }
    setLoading(false)
  }

  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '20px 18px 60px' }}>
      <button onClick={onExit} style={{ background: 'var(--bg-card)', color: 'var(--text-soft)', padding: '8px 14px', borderRadius: 10, fontWeight: 700, marginBottom: 18 }}>← Back</button>
      <div className="display" style={{ fontSize: 26, fontWeight: 600, marginBottom: 6 }}>📸 Show me your work</div>
      <div style={{ color: 'var(--text-soft)', marginBottom: 20, lineHeight: 1.5 }}>
        Take a screenshot of your Supernote work and upload it. I'll read your steps, follow your thinking,
        and help you find any spot that needs a fix — without just giving you the answer.
      </div>

      <input ref={fileRef} type="file" accept="image/*" onChange={onFile} style={{ display: 'none' }} />

      {!image ? (
        <button onClick={() => fileRef.current.click()} style={{ width: '100%', padding: '40px', borderRadius: 18, background: 'var(--bg-card)', border: '2px dashed var(--border)', color: 'var(--text-soft)', fontSize: 18, fontWeight: 700 }}>
          📷 Tap to upload a photo
        </button>
      ) : (
        <div>
          <img src={image.preview} alt="your work" style={{ width: '100%', borderRadius: 16, border: '1px solid var(--border)', marginBottom: 12 }} />
          <button onClick={() => fileRef.current.click()} style={{ ...ghostBtn, width: '100%', marginBottom: 12 }}>Choose a different photo</button>
        </div>
      )}

      <input value={context} onChange={e => setContext(e.target.value)} placeholder="(optional) What problem are you solving?"
        style={{ width: '100%', padding: '14px 16px', borderRadius: 12, background: 'var(--bg-card)', color: '#fff', border: '1px solid var(--border)', outline: 'none', fontSize: 15, marginBottom: 14 }} />

      <button disabled={!image || loading} onClick={analyze}
        style={{ width: '100%', padding: '16px', borderRadius: 16, background: image ? 'linear-gradient(90deg,#7c3aed,#a855f7)' : 'var(--bg-card)', color: '#fff', fontFamily: "'Fredoka',sans-serif", fontWeight: 600, fontSize: 20, opacity: loading ? 0.7 : 1 }}>
        {loading ? 'Reading your work…' : 'Read my work & help me'}
      </button>

      {loading && <Spinner label="Tracing your steps…" />}
      {error && <div style={{ marginTop: 16 }}><ErrorBox error={error} /></div>}
      {result && (
        <div style={{ marginTop: 20, background: 'linear-gradient(160deg,var(--bg-card-soft),var(--bg-card))', borderRadius: 18, padding: '20px 22px', border: '1px solid var(--border)', lineHeight: 1.6, fontSize: 16, whiteSpace: 'pre-wrap', animation: 'slideIn .4s ease' }}>
          {result}
        </div>
      )}
    </div>
  )
}
