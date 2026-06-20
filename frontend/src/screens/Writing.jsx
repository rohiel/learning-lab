import React, { useState, useEffect, useRef } from 'react'
import { api } from '../api.js'
import { CenterWrap, Spinner, ErrorBox, ghostBtn } from '../ui.jsx'

export default function Writing({ student, config, progress, onExit }) {
  const [prompt, setPrompt] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [text, setText] = useState('')
  const [review, setReview] = useState(null)
  const [reviewing, setReviewing] = useState(false)
  const fileRef = useRef()
  const [imgPreview, setImgPreview] = useState(null)

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const p = await api.writingPrompt(student.id, config.week, config.day)
        if (alive) { setPrompt({ prompt: p.prompt, targetWords: p.target_words || [], lines: p.lines }); setLoading(false) }
      } catch (e) {
        if (alive) {
          setError(e.status === 404 ? "Today's writing prompt isn't ready yet — ask a grown-up to prep it (writing is twice a week)." : e.message)
          setLoading(false)
        }
      }
    })()
    return () => { alive = false }
  }, [])

  function onFile(e) {
    const f = e.target.files[0]; if (!f) return
    const reader = new FileReader(); reader.onload = () => setImgPreview(reader.result); reader.readAsDataURL(f)
  }

  async function submit() {
    if (!text.trim() || reviewing) return
    setReviewing(true); setError(null)
    try {
      const r = await api.reviewWriting({ student_id: student.id, week: config.week, day: config.day, text: text.trim() })
      setReview(r.feedback)
    } catch (e) { setError(e.message) }
    setReviewing(false)
  }

  if (loading) return <CenterWrap onExit={onExit}><Spinner label="Loading your writing prompt…" /></CenterWrap>
  if (error && !prompt) return <CenterWrap onExit={onExit}><ErrorBox error={error} /></CenterWrap>

  const doneThisWeek = (progress?.writing_this_week && progress.writing_this_week[config.week]) || 0

  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: '20px 18px 60px' }}>
      <button onClick={onExit} style={{ background: 'var(--bg-card)', color: 'var(--text-soft)', padding: '8px 14px', borderRadius: 10, fontWeight: 700, marginBottom: 18 }}>← Back</button>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div className="display" style={{ fontSize: 26, fontWeight: 600 }}>✍️ Writing time</div>
        <div style={{ fontSize: 13, fontWeight: 800, color: doneThisWeek >= 2 ? '#86efac' : 'var(--text-dim)' }}>{doneThisWeek}/2 this week {doneThisWeek >= 2 ? '✓' : ''}</div>
      </div>

      <div style={{ background: 'linear-gradient(160deg,var(--bg-card-soft),var(--bg-card))', border: '1px solid var(--border)', borderRadius: 18, padding: '18px 20px', marginBottom: 16, fontSize: 17, lineHeight: 1.55 }}>
        {prompt.prompt}
        <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {(prompt.targetWords || []).map((w, i) => (
            <span key={i} style={{ padding: '5px 12px', borderRadius: 20, fontWeight: 700, fontSize: 14, background: 'linear-gradient(160deg,#0d9488,#14b8a6)', color: '#fff' }}>{w}</span>
          ))}
        </div>
        <div style={{ marginTop: 10, fontSize: 13, color: 'var(--text-dim)', fontWeight: 700 }}>
          Aim for about {prompt.lines} sentences · use the {(prompt.targetWords || []).length} teal words
        </div>
      </div>

      {!review && (
        <>
          <textarea value={text} onChange={e => setText(e.target.value)} placeholder="Write your paragraph here… (or upload a photo of your handwriting below)" rows={7}
            style={{ width: '100%', padding: '16px', borderRadius: 14, background: 'var(--bg-card)', color: '#fff', border: '1px solid var(--border)', outline: 'none', fontSize: 16, lineHeight: 1.6, resize: 'vertical', fontFamily: 'inherit' }} />
          <div style={{ fontSize: 13, color: 'var(--text-dim)', margin: '6px 2px 14px', fontWeight: 700 }}>{text.trim() ? text.trim().split(/\s+/).length + ' words' : '0 words'}</div>

          <input ref={fileRef} type="file" accept="image/*" onChange={onFile} style={{ display: 'none' }} />
          {imgPreview && <img src={imgPreview} alt="handwriting" style={{ width: '100%', borderRadius: 14, marginBottom: 12, border: '1px solid var(--border)' }} />}
          <div style={{ display: 'flex', gap: 10 }}>
            <button onClick={() => fileRef.current.click()} style={{ ...ghostBtn, flex: 1 }}>📸 Upload handwriting</button>
            <button disabled={!text.trim() || reviewing} onClick={submit}
              style={{ flex: 2, padding: '14px', borderRadius: 14, background: text.trim() ? 'linear-gradient(90deg,#16a34a,#22c55e)' : 'var(--bg-card)', color: '#fff', fontFamily: "'Fredoka',sans-serif", fontWeight: 600, fontSize: 18, opacity: reviewing ? 0.7 : 1 }}>
              {reviewing ? 'Reading…' : 'Get feedback'}
            </button>
          </div>
        </>
      )}

      {error && <div style={{ marginTop: 14 }}><ErrorBox error={error} /></div>}

      {review && (
        <div>
          <div style={{ background: 'linear-gradient(160deg,var(--bg-card-soft),var(--bg-card))', borderRadius: 18, padding: '20px 22px', border: '1px solid var(--border)', lineHeight: 1.6, fontSize: 16, whiteSpace: 'pre-wrap', animation: 'slideIn .4s ease' }}>
            {review}
          </div>
          <button onClick={onExit} style={{ width: '100%', marginTop: 16, padding: '15px', borderRadius: 14, background: 'linear-gradient(90deg,#16a34a,#22c55e)', color: '#fff', fontFamily: "'Fredoka',sans-serif", fontWeight: 600, fontSize: 18 }}>Done ✓</button>
        </div>
      )}
    </div>
  )
}
