import React, { useState } from 'react'
import { api } from '../api.js'
import { MATH_WEEKS, ENGLISH_WEEKS, LEXILE_BY_WEEK, MODES, passageLines, practiceCount } from '../curriculum.js'
import { Section, BigToggle, ghostBtn } from '../ui.jsx'

export default function Setup({ student, progress, onStart, onRefresh }) {
  const [subject, setSubject] = useState('math')
  const [week, setWeek] = useState(student.current_week || 1)
  const [mode, setMode] = useState('practice')
  const [day, setDay] = useState(student.current_day || 1)
  const [editMode, setEditMode] = useState(false)
  const [reviewDay, setReviewDay] = useState(null)        // {subject, week, day}
  const [reviewData, setReviewData] = useState(null)      // fetched records
  const [busy, setBusy] = useState(false)

  const weeks = subject === 'math' ? MATH_WEEKS : ENGLISH_WEEKS
  const wk = weeks[week]
  const days = progress?.days || []
  const weekRows = progress?.weeks || []
  const hasAnyProgress = days.length > 0 || weekRows.length > 0 || (progress?.help_total > 0)

  const dayEntry = (s, w, d) => days.find(x => x.subject === s && x.week === w && x.day === d)
  const dayDone = (s, w, d) => !!dayEntry(s, w, d)?.done
  const dayIsManual = (s, w, d) => { const e = dayEntry(s, w, d); return !!(e && e.manual && e.done) }
  const hasRecordsForDay = (s, w, d) => !!dayEntry(s, w, d)?.has_records
  const weekEntry = (s, w) => weekRows.find(x => x.subject === s && x.week === w)
  const weekTestDone = (s, w) => !!weekEntry(s, w)?.complete
  const daysDoneInWeek = (s, w) => days.filter(x => x.subject === s && x.week === w && x.done).length

  async function toggleDay(s, w, d) {
    if (busy) return
    setBusy(true)
    try { await api.flag({ student_id: student.id, subject: s, week: w, day: d, done: !dayDone(s, w, d) }); await onRefresh() }
    finally { setBusy(false) }
  }
  async function toggleWeek(s, w) {
    if (busy) return
    setBusy(true)
    try { await api.flag({ student_id: student.id, subject: s, week: w, day: null, done: !weekTestDone(s, w) }); await onRefresh() }
    finally { setBusy(false) }
  }

  async function openReview(s, w, d) {
    setReviewDay({ subject: s, week: w, day: d }); setReviewData(null)
    try { setReviewData(await api.dayRecords(student.id, s, w, d)) } catch { setReviewData({ records: [] }) }
  }

  const writingThisWeek = (progress?.writing_this_week && progress.writing_this_week[week]) || 0

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: '24px 18px 60px' }}>
      <div style={{ textAlign: 'center', marginBottom: 28, animation: 'slideIn .5s ease' }}>
        <div className="display" style={{ fontSize: 40, fontWeight: 700, letterSpacing: '-0.5px',
          background: 'linear-gradient(90deg,#f59e0b,#ec4899,#14b8a6)', WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
          {student.name}'s Learning Lab
        </div>
        <div style={{ color: 'var(--text-dim)', marginTop: 6, fontWeight: 600 }}>
          Built for a rock-collecting, bug-loving rising 6th grader 🪨🐛
        </div>
      </div>

      <Section label="Subject">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <BigToggle active={subject === 'math'} onClick={() => { setSubject('math'); setWeek(student.current_week || 1) }}
            color="#3b82f6" emoji="🔢" title="Math" sub="Word problems that hide the operation" />
          <BigToggle active={subject === 'english'} onClick={() => { setSubject('english'); setWeek(student.current_week || 1) }}
            color="#ec4899" emoji="📖" title="English" sub="Reading, vocab & mechanics" />
        </div>
      </Section>

      {hasAnyProgress && (
        <div style={{ marginBottom: 22, padding: '14px 16px', background: 'var(--bg-card)', borderRadius: 14, border: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--text-dim)' }}>Progress so far</div>
            <button onClick={() => setEditMode(m => !m)}
              style={{ padding: '5px 12px', borderRadius: 8, fontWeight: 800, fontSize: 12,
                background: editMode ? 'linear-gradient(160deg,#7c3aed,#5b21b6)' : 'var(--bg-deep)',
                color: editMode ? '#fff' : 'var(--text-soft)', border: '1px solid var(--border)' }}>
              {editMode ? '✓ Done editing' : '✏️ Edit progress'}
            </button>
          </div>
          {editMode && (
            <div style={{ marginBottom: 12, padding: '10px 12px', background: 'var(--bg-deep)', borderRadius: 10, fontSize: 13, color: 'var(--text-soft)', lineHeight: 1.5 }}>
              Tap any <b>day</b> or <b>week</b> button below to mark it done or undone by hand.
              Auto-tracked sessions stay checked on their own — this is just for filling in work the app didn't record.
            </div>
          )}
          {['math', 'english'].map(s => (
            <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: s === 'math' ? 8 : 0 }}>
              <span style={{ width: 64, fontSize: 13.5, fontWeight: 700, color: s === 'math' ? '#93c5fd' : '#f9a8d4' }}>{s === 'math' ? '🔢 Math' : '📖 English'}</span>
              <div style={{ display: 'flex', gap: 4, flex: 1 }}>
                {[1, 2, 3, 4, 5, 6, 7, 8].map(w => {
                  const complete = weekTestDone(s, w)
                  const partial = !complete && daysDoneInWeek(s, w) > 0
                  return (
                    <div key={w} title={`Week ${w}`} style={{ flex: 1, height: 18, borderRadius: 5,
                      display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 800,
                      background: complete ? 'linear-gradient(160deg,#16a34a,#15803d)' : partial ? 'rgba(251,191,36,0.25)' : 'var(--bg-deep)',
                      color: complete ? '#fff' : partial ? '#fbbf24' : 'var(--text-dim)',
                      border: partial ? '1px solid #fbbf2455' : '1px solid transparent' }}>
                      {complete ? '✓' : w}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
          <div style={{ marginTop: 10, fontSize: 12, color: 'var(--text-dim)', display: 'flex', gap: 14, flexWrap: 'wrap' }}>
            <span><span style={{ color: '#22c55e' }}>■</span> week complete</span>
            <span><span style={{ color: '#fbbf24' }}>■</span> in progress</span>
            {(progress?.help_total > 0) && <span>· {progress.help_total} help asks total</span>}
          </div>
        </div>
      )}

      <Section label="Week of the 8-week plan">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {Object.keys(weeks).map(w => {
            const wn = Number(w)
            const complete = weekTestDone(subject, wn)
            const partial = !complete && daysDoneInWeek(subject, wn) > 0
            return (
              <button key={w} onClick={() => editMode ? toggleWeek(subject, wn) : setWeek(wn)}
                style={{
                  position: 'relative', padding: '10px 16px', borderRadius: 12, fontWeight: 700, fontSize: 15,
                  background: editMode
                    ? (complete ? 'linear-gradient(160deg,#15803d,#166534)' : 'var(--bg-deep)')
                    : (wn === week ? 'linear-gradient(160deg,#7c3aed,#5b21b6)' : complete ? 'linear-gradient(160deg,#15803d,#166534)' : 'var(--bg-card)'),
                  color: (wn === week || complete) ? '#fff' : 'var(--text-soft)',
                  border: editMode ? '2px dashed ' + (complete ? '#4ade80' : '#a78bfa66')
                    : wn === week ? '2px solid #a78bfa' : complete ? '2px solid #4ade80' : '2px solid transparent',
                  transition: 'all .15s',
                }}>
                {w}{complete ? ' ✓' : ''}
                {partial && !editMode && <span style={{ position: 'absolute', top: 3, right: 5, width: 6, height: 6, borderRadius: '50%', background: '#fbbf24' }} />}
              </button>
            )
          })}
        </div>
        <div style={{ marginTop: 14, padding: '14px 16px', background: 'var(--bg-card)', borderRadius: 14, border: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
            <div className="display" style={{ fontWeight: 600, fontSize: 18, color: '#fcd34d' }}>{wk.title}</div>
            {weekTestDone(subject, week)
              ? <span style={{ fontSize: 12.5, fontWeight: 800, color: '#86efac' }}>WEEK COMPLETE ✓</span>
              : <span style={{ fontSize: 12.5, fontWeight: 800, color: 'var(--text-dim)' }}>{daysDoneInWeek(subject, week)}/7 days</span>}
          </div>
          <div style={{ color: 'var(--text-soft)', fontSize: 14.5, marginTop: 5, lineHeight: 1.5 }}>{wk.focus}</div>
          {subject === 'english' && <div style={{ marginTop: 8, fontSize: 13, color: 'var(--text-dim)', fontWeight: 700 }}>
            Target reading level: {LEXILE_BY_WEEK[week]}L · ~{passageLines(week, day)} line passages today</div>}
        </div>
      </Section>

      {(mode === 'practice' || editMode) && (
        <Section label={editMode ? 'Day of the week (tap to mark done / undone)'
          : subject === 'english' ? 'Day of the week (more questions + longer passages each day)'
          : 'Day of the week (more practice each day)'}>
          <div style={{ display: 'flex', gap: 8 }}>
            {[1, 2, 3, 4, 5, 6, 7].map(d => {
              const done = dayDone(subject, week, d)
              const manual = dayIsManual(subject, week, d)
              return (
                <button key={d} onClick={() => editMode ? toggleDay(subject, week, d) : setDay(d)}
                  style={{ flex: 1, padding: '10px 0', borderRadius: 10, fontWeight: 700, position: 'relative',
                    background: editMode ? (done ? 'linear-gradient(160deg,#15803d,#166534)' : 'var(--bg-deep)')
                      : (d === day ? 'linear-gradient(160deg,#14b8a6,#0d9488)' : done ? 'linear-gradient(160deg,#15803d,#166534)' : 'var(--bg-card)'),
                    color: (d === day || done) ? '#fff' : 'var(--text-soft)',
                    border: editMode ? '2px dashed ' + (done ? '#4ade80' : '#5eead466') : '2px solid ' + (d === day ? '#5eead4' : done ? '#4ade80' : 'transparent') }}>
                  {d}
                  {done && (editMode || d !== day) && <span style={{ position: 'absolute', top: 2, right: 4, fontSize: 10, color: '#bbf7d0' }}>{manual ? '✎' : '✓'}</span>}
                </button>
              )
            })}
          </div>
          <div style={{ marginTop: 8, fontSize: 13, color: 'var(--text-dim)', fontWeight: 700 }}>
            Day {day}: {practiceCount(day)} questions{subject === 'english' ? ` · ~${passageLines(week, day)} line passages` : ''}
            {dayDone(subject, week, day) ? ' · completed ✓' : ''}
          </div>
          {hasRecordsForDay(subject, week, day) && !editMode && (
            <button onClick={() => openReview(subject, week, day)}
              style={{ marginTop: 10, width: '100%', padding: '11px', borderRadius: 10, background: 'var(--bg-deep)', color: '#93c5fd', fontWeight: 700, fontSize: 14, border: '1px solid var(--border)' }}>
              👁 View the questions she did on Day {day}
            </button>
          )}
        </Section>
      )}

      <Section label="Session type">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {Object.entries(MODES).map(([k, m]) => {
            const isTest = k === 'test'
            const testDone = isTest && weekTestDone(subject, week)
            return (
              <button key={k} onClick={() => setMode(k)}
                style={{ padding: '16px 12px', borderRadius: 16, textAlign: 'center', position: 'relative',
                  background: k === mode ? 'linear-gradient(160deg,#f59e0b,#d97706)' : 'var(--bg-card)',
                  border: '2px solid ' + (k === mode ? '#fcd34d' : 'transparent'),
                  color: k === mode ? '#fff' : 'var(--text-soft)', transition: 'all .15s' }}>
                <div style={{ fontSize: 26 }}>{m.icon}</div>
                <div className="display" style={{ fontWeight: 600, fontSize: 18, marginTop: 4 }}>{m.label}</div>
                <div style={{ fontSize: 12.5, opacity: 0.85, marginTop: 2 }}>
                  {isTest ? `${MODES.test.count} questions · once a week` : `${practiceCount(day)} questions · daily`}
                </div>
                {testDone && <div style={{ marginTop: 6, fontSize: 11.5, fontWeight: 800, color: '#86efac' }}>✓ taken this week</div>}
              </button>
            )
          })}
        </div>
        {mode === 'test' && (
          <div style={{ marginTop: 12, padding: '12px 14px', background: 'var(--bg-card)', borderRadius: 12, border: '1px solid var(--border)', fontSize: 13.5, color: 'var(--text-soft)', lineHeight: 1.5 }}>
            The Weekly Test is the once-a-week checkpoint for Week {week} {subject === 'math' ? 'Math' : 'English'} —
            it pulls from everything this week, weighted toward her weak spots, and the results feed the Parent Review.
          </div>
        )}
      </Section>

      <button onClick={() => onStart({ subject, week, mode, day })}
        style={{ width: '100%', marginTop: 26, padding: '18px', borderRadius: 18,
          background: 'linear-gradient(90deg,#16a34a,#22c55e)', color: '#fff',
          fontFamily: "'Fredoka',sans-serif", fontWeight: 600, fontSize: 22, letterSpacing: '0.3px',
          boxShadow: '0 8px 24px rgba(34,197,94,0.35)' }}>
        Start session →
      </button>

      {subject === 'english' && (
        <button onClick={() => onStart({ subject: 'writing', week, mode, day })}
          style={{ width: '100%', marginTop: 12, padding: '15px', borderRadius: 16,
            background: 'linear-gradient(90deg,#0d9488,#14b8a6)', color: '#fff',
            fontFamily: "'Fredoka',sans-serif", fontWeight: 600, fontSize: 18 }}>
          ✍️ Writing prompt
          <span style={{ marginLeft: 8, fontSize: 13.5, opacity: 0.9 }}>
            {writingThisWeek}/2 this week {writingThisWeek >= 2 ? '✓' : ''}</span>
        </button>
      )}

      <div style={{ display: 'flex', gap: 10, marginTop: 14 }}>
        <button onClick={() => onStart({ subject: 'work', week, mode, day })} style={ghostBtn}>📸 Upload my Supernote work</button>
        <button onClick={() => onStart({ subject: 'review', week, mode, day })} style={ghostBtn}>📊 Parent review</button>
      </div>

      {reviewDay && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(15,6,32,0.92)', zIndex: 60,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px' }}
          onClick={() => setReviewDay(null)}>
          <div onClick={e => e.stopPropagation()} style={{ maxWidth: 680, width: '100%', maxHeight: '86vh',
            overflowY: 'auto', background: 'var(--bg-card)', borderRadius: 20, border: '1px solid var(--border)', padding: '22px 24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <div className="display" style={{ fontSize: 20, fontWeight: 600, color: '#fcd34d' }}>
                {reviewDay.subject === 'math' ? '🔢 Math' : '📖 English'} · Week {reviewDay.week}, Day {reviewDay.day}
              </div>
              <button onClick={() => setReviewDay(null)} style={{ background: 'var(--bg-deep)', color: '#fff', borderRadius: 8, padding: '5px 12px', fontWeight: 700, fontSize: 13 }}>Close</button>
            </div>
            <div style={{ fontSize: 13.5, color: 'var(--text-dim)', marginBottom: 16 }}>
              {reviewData ? `Scored ${reviewData.score}/${reviewData.total}` : 'Loading…'}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {(reviewData?.records || []).map((r, i) => (
                <div key={i} style={{ background: 'var(--bg-deep)', borderRadius: 14, padding: '14px 16px', border: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, marginBottom: 6 }}>
                    <span style={{ fontSize: 12, fontWeight: 800, color: 'var(--text-dim)' }}>Q{i + 1} · Level {r.level || 1}{r.skill ? ' · ' + r.skill : ''}</span>
                    <span style={{ fontSize: 12, fontWeight: 800, color: r.correct ? '#86efac' : '#fca5a5' }}>{r.correct ? '✓' : '✗'}</span>
                  </div>
                  <div style={{ fontSize: 15.5, lineHeight: 1.45, marginBottom: 8 }}>{r.question}</div>
                  <div style={{ fontSize: 14, color: r.correct ? '#86efac' : '#fca5a5' }}>Her answer: {String(r.given)}</div>
                  {!r.correct && <div style={{ fontSize: 14, color: '#86efac', marginTop: 2 }}>Correct: {String(r.expected)}</div>}
                </div>
              ))}
              {reviewData && !reviewData.records.length && <div style={{ color: 'var(--text-soft)' }}>No saved questions for this day yet.</div>}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
