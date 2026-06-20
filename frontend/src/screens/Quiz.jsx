import React, { useState, useEffect, useRef } from 'react'
import { api } from '../api.js'
import { MATH_WEEKS, ENGLISH_WEEKS, ANSWER_COLORS, EXPLAIN_PROMPTS } from '../curriculum.js'
import { CenterWrap, Spinner, ErrorBox } from '../ui.jsx'

export default function Quiz({ student, config, resuming, onDone, onExit }) {
  const [questions, setQuestions] = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [idx, setIdx] = useState(0)
  const [selected, setSelected] = useState(null)
  const [fillValue, setFillValue] = useState('')
  const [feedback, setFeedback] = useState(null)   // {correct, hint, expected, bumped}
  const [checking, setChecking] = useState(false)
  const [explainPrompt, setExplainPrompt] = useState(null)
  const [explainValue, setExplainValue] = useState('')
  const [confirmStep, setConfirmStep] = useState(false)
  const [viewPrev, setViewPrev] = useState(null)

  // session-level adaptive state (client-side, exactly like the original)
  const streak = useRef(0)
  const curLevel = useRef(1)
  const results = useRef([])
  const sessionWeak = useRef([])
  const helpCount = useRef(0)
  const neededHelp = useRef(false)
  const neededHelpSkills = useRef([])

  const [helpOpen, setHelpOpen] = useState(false)
  const [helpMsgs, setHelpMsgs] = useState([])
  const [helpInput, setHelpInput] = useState('')
  const [helpBusy, setHelpBusy] = useState(false)
  const offTopic = useRef(0)

  const subj = config.subject

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        setLoading(true)
        const data = await api.startSession({ student_id: student.id, subject: subj, week: config.week, day: config.day, mode: config.mode })
        if (!alive) return
        const qs = data.questions
        if (!qs || !qs.length) throw new Error('No questions are prepared for this day yet. Ask a grown-up to run tonight\'s prep.')

        // Resume: rebuild adaptive state + index from already-answered questions.
        let startIdx = 0
        if (data.answered && data.answered.length) {
          const answeredMap = new Map(data.answered.map(a => [a.question_id, a]))
          let st = 0, lvl = 1
          for (const qq of qs) {
            const a = answeredMap.get(qq.id)
            if (!a) break
            results.current.push({ skill: qq.skill, level: qq.level, type: qq.type, correct: a.correct, retention: !!qq.retention, given: a.given, expected: null, question: qq.question })
            if (a.correct) { st += 1; if (st >= 2 && lvl < 5) { lvl += 1; st = 0 } }
            else { st = 0; if (qq.skill && !sessionWeak.current.includes(qq.skill)) sessionWeak.current.push(qq.skill) }
          }
          streak.current = st; curLevel.current = lvl
          startIdx = results.current.length
        }
        setQuestions(qs); setSessionId(data.session_id)
        setLoading(false)
        if (startIdx >= qs.length) finish(data.session_id) // all answered already
        else setIdx(startIdx)
      } catch (e) { if (alive) { setError(e.message); setLoading(false) } }
    })()
    return () => { alive = false }
  }, [])

  const q = questions ? questions[idx] : null

  // read-it-back gate is now driven by the server-computed precision flag
  const isPrecisionQuestion = (qq) => !!(qq && qq.precision)

  async function submit() {
    if (feedback) return
    if (!confirmStep && isPrecisionQuestion(q)) { setConfirmStep(true); return }
    setChecking(true)
    try {
      const given = q.type === 'mc' ? selected : fillValue.trim()
      const res = await api.answer({ session_id: sessionId, question_id: q.id, given, needed_help: neededHelp.current })
      const correct = res.correct
      results.current.push({ skill: q.skill, level: q.level, type: q.type, correct, retention: !!q.retention, given, expected: res.correct_answer, question: q.question })
      if (neededHelp.current && correct && q.skill && !neededHelpSkills.current.includes(q.skill)) neededHelpSkills.current.push(q.skill)

      if (correct) {
        streak.current += 1
        let bumped = false
        if (streak.current >= 2 && curLevel.current < 5) { curLevel.current += 1; streak.current = 0; bumped = true }
        setFeedback({ correct: true, bumped, expected: res.correct_answer })
        if (q.type === 'fill' || q.level >= 3) setExplainPrompt(EXPLAIN_PROMPTS[Math.floor(Math.random() * EXPLAIN_PROMPTS.length)])
      } else {
        streak.current = 0
        if (q.skill && !sessionWeak.current.includes(q.skill)) sessionWeak.current.push(q.skill)
        setFeedback({ correct: false, hint: res.hint || 'Take another look — one step at a time.', expected: res.correct_answer })
      }
    } catch (e) {
      setFeedback({ correct: false, hint: "Let's move on — take another look at this one later.", expected: '' })
    } finally { setChecking(false) }
  }

  function next() {
    setFeedback(null); setSelected(null); setFillValue('')
    setExplainPrompt(null); setExplainValue(''); setConfirmStep(false)
    neededHelp.current = false
    setHelpOpen(false); setHelpMsgs([]); setHelpInput(''); offTopic.current = 0
    if (idx + 1 >= questions.length) finish()
    else setIdx(idx + 1)
  }

  async function finish(explicitSessionId) {
    const sid = explicitSessionId || sessionId
    const correctCount = results.current.filter(r => r.correct).length
    const local = {
      subject: subj, week: config.week, day: config.day, mode: config.mode,
      score: correctCount, total: results.current.length,
      maxLevel: Math.max(1, ...results.current.map(r => r.level || 1)),
      weakSkills: sessionWeak.current,
      retentionResults: results.current.filter(r => r.retention).map(r => ({ skill: r.skill, correct: r.correct })),
      helpRequests: helpCount.current,
    }
    try {
      const res = await api.completeSession(sid)
      onDone({ ...local, score: res.score ?? local.score, total: res.total ?? local.total,
        maxLevel: res.max_level ?? local.maxLevel, weakSkills: (res.weak_skills && res.weak_skills.length) ? res.weak_skills : local.weakSkills })
    } catch (e) {
      onDone(local)
    }
  }

  async function sendHelp() {
    const text = helpInput.trim()
    if (!text || helpBusy) return
    helpCount.current += 1
    neededHelp.current = true
    const newMsgs = [...helpMsgs, { role: 'user', content: text }]
    setHelpMsgs(newMsgs); setHelpInput(''); setHelpBusy(true)
    const onTopicHint = /\b(answer|problem|question|number|divide|multiply|add|subtract|decimal|fraction|word|sentence|comma|read|passage|how|why|what|solve|step|mean|equal)\b/i.test(text)
    if (!onTopicHint) offTopic.current += 1; else offTopic.current = 0
    try {
      const res = await api.help({ session_id: sessionId, question_id: q.id, history: newMsgs, off_topic_count: offTopic.current })
      setHelpMsgs(m => [...m, { role: 'assistant', content: res.reply }])
    } catch (e) {
      setHelpMsgs(m => [...m, { role: 'assistant', content: "Hmm, I couldn't think just now — try asking again in a sec!" }])
    }
    setHelpBusy(false)
  }

  if (loading) return <CenterWrap onExit={onExit}><Spinner label={`Loading ${subj === 'math' ? 'math' : 'reading'} questions…`} /></CenterWrap>
  if (error) return <CenterWrap onExit={onExit}><ErrorBox error={error} /></CenterWrap>

  const accent = ANSWER_COLORS[idx % 4].solid

  return (
    <div style={{ maxWidth: 760, margin: '0 auto', padding: '16px 16px 50px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18 }}>
        <button onClick={onExit} style={{ background: 'var(--bg-card)', color: 'var(--text-soft)', padding: '8px 14px', borderRadius: 10, fontWeight: 700, fontSize: 14 }}>← Exit</button>
        {idx >= 1 && results.current.length >= idx && (
          <button onClick={() => setViewPrev(idx - 1)} style={{ background: 'var(--bg-card)', color: '#fcd34d', padding: '8px 12px', borderRadius: 10, fontWeight: 700, fontSize: 13.5 }} title="Review the previous question">⬑ Previous</button>
        )}
        <div style={{ flex: 1, height: 12, background: 'var(--bg-card)', borderRadius: 8, overflow: 'hidden' }}>
          <div style={{ width: `${(idx / (questions.length)) * 100}%`, height: '100%', background: 'linear-gradient(90deg,#14b8a6,#f59e0b)', transition: 'width .4s' }} />
        </div>
        <div style={{ background: '#0008', padding: '6px 14px', borderRadius: 20, fontWeight: 800, fontSize: 15, color: '#fcd34d' }}>{idx + 1}/{questions.length}</div>
      </div>

      {viewPrev !== null && results.current[viewPrev] && (() => {
        const r = results.current[viewPrev]
        const pq = questions[viewPrev]
        return (
          <div style={{ position: 'fixed', inset: 0, background: 'rgba(15,6,32,0.92)', zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px', animation: 'slideIn .2s ease' }} onClick={() => setViewPrev(null)}>
            <div onClick={e => e.stopPropagation()} style={{ maxWidth: 620, width: '100%', maxHeight: '85vh', overflowY: 'auto', background: 'var(--bg-card)', borderRadius: 20, border: '1px solid var(--border)', padding: '22px 24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                <div className="display" style={{ fontSize: 18, fontWeight: 600, color: '#fcd34d' }}>Question {viewPrev + 1} (review)</div>
                <span style={{ fontSize: 13, fontWeight: 800, padding: '4px 10px', borderRadius: 8, background: r.correct ? '#16a34a' : '#9a3412', color: '#fff' }}>{r.correct ? '✓ correct' : '✗ missed'}</span>
              </div>
              {pq && pq.passage && <div style={{ background: 'var(--bg-deep)', borderRadius: 12, padding: '12px 14px', marginBottom: 12, fontSize: 14.5, lineHeight: 1.6, color: 'var(--text-soft)' }}>{pq.passage}</div>}
              <div style={{ fontSize: 17, fontWeight: 600, marginBottom: 14, lineHeight: 1.4 }}>{r.question}</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ padding: '12px 14px', borderRadius: 10, background: 'var(--bg-deep)', border: '1px solid var(--border)' }}>
                  <span style={{ fontSize: 12.5, fontWeight: 800, color: 'var(--text-dim)' }}>HER ANSWER</span>
                  <div style={{ fontSize: 16, marginTop: 3, color: r.correct ? '#86efac' : '#fca5a5' }}>{String(r.given)}</div>
                </div>
                {!r.correct && r.expected && (
                  <div style={{ padding: '12px 14px', borderRadius: 10, background: 'var(--bg-deep)', border: '1px solid var(--border)' }}>
                    <span style={{ fontSize: 12.5, fontWeight: 800, color: 'var(--text-dim)' }}>CORRECT ANSWER</span>
                    <div style={{ fontSize: 16, marginTop: 3, color: '#86efac' }}>{String(r.expected)}</div>
                  </div>
                )}
              </div>
              <button onClick={() => setViewPrev(null)} style={{ width: '100%', marginTop: 18, padding: '14px', borderRadius: 12, background: 'linear-gradient(90deg,#7c3aed,#a855f7)', color: '#fff', fontFamily: "'Fredoka',sans-serif", fontWeight: 600, fontSize: 17 }}>Back to current question →</button>
            </div>
          </div>
        )
      })()}

      <div style={{ display: 'flex', justifyContent: 'center', gap: 6, marginBottom: 16 }}>
        {[1, 2, 3, 4, 5].map(l => (
          <div key={l} style={{ width: 34, height: 7, borderRadius: 4, background: l <= curLevel.current ? 'linear-gradient(90deg,#f59e0b,#ec4899)' : 'var(--bg-card)' }} />
        ))}
        <span style={{ marginLeft: 8, fontSize: 13, fontWeight: 800, color: 'var(--text-dim)' }}>LEVEL {curLevel.current}</span>
      </div>

      {q.passage && (
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 16, padding: '16px 18px', marginBottom: 14, lineHeight: 1.65, fontSize: 16, color: 'var(--text)', animation: 'pop .3s ease' }}>
          {q.connection && <div style={{ fontSize: 12, fontWeight: 800, color: '#5eead4', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '1px' }}>🔗 Connect the passages</div>}
          {q.passage}
        </div>
      )}

      <div className="display" style={{ background: 'linear-gradient(160deg,var(--bg-card-soft),var(--bg-card))', border: '1px solid var(--border)', borderRadius: 20, padding: '26px 24px', marginBottom: 18, fontSize: 21, fontWeight: 500, lineHeight: 1.4, textAlign: 'center', minHeight: 90, display: 'flex', alignItems: 'center', justifyContent: 'center', animation: feedback && !feedback.correct ? 'shake .4s' : 'pop .3s ease' }}>
        {q.question}
      </div>

      {q.type === 'mc' ? (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {q.choices.map((c, i) => {
            const isSel = selected === c
            const isAns = feedback && String(c).trim() === String(feedback.expected).trim()
            const wrongSel = feedback && isSel && !feedback.correct
            return (
              <button key={i} disabled={!!feedback} onClick={() => !feedback && setSelected(c)}
                style={{ padding: '22px 16px', borderRadius: 16, minHeight: 84, fontSize: 18, fontWeight: 700, color: '#fff',
                  background: ANSWER_COLORS[i].bg, border: isSel ? '3px solid #fff' : '3px solid transparent',
                  opacity: feedback ? (isAns ? 1 : (wrongSel ? 1 : 0.45)) : 1,
                  boxShadow: isAns ? '0 0 0 3px #22c55e, 0 6px 20px #22c55e66' : wrongSel ? '0 0 0 3px #ef4444' : '0 4px 14px #0004',
                  transform: isSel && !feedback ? 'scale(1.02)' : 'scale(1)', transition: 'all .15s' }}>
                {c}
              </button>
            )
          })}
        </div>
      ) : (
        <div>
          <input value={fillValue} disabled={!!feedback} onChange={e => setFillValue(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !feedback && fillValue.trim()) submit() }}
            placeholder="Type your answer…"
            style={{ width: '100%', padding: '20px 22px', borderRadius: 16, fontSize: 20, fontWeight: 700,
              background: 'var(--bg-card)', color: '#fff', textAlign: 'center',
              border: '3px solid ' + (feedback ? (feedback.correct ? '#22c55e' : '#ef4444') : 'var(--border)'), outline: 'none' }} />
        </div>
      )}

      {feedback && (
        <div style={{ marginTop: 18, animation: 'slideIn .3s ease' }}>
          {feedback.correct ? (
            <div style={{ background: 'linear-gradient(160deg,#16a34a,#15803d)', borderRadius: 16, padding: '16px 20px', textAlign: 'center' }}>
              <div className="display" style={{ fontSize: 22, fontWeight: 600 }}>{feedback.bumped ? '🔥 Correct — leveling you UP!' : '✓ Correct!'}</div>
              {feedback.bumped && <div style={{ fontSize: 14, marginTop: 4, color: '#dcfce7' }}>Two in a row — the questions just got harder. Let's find your edge.</div>}
            </div>
          ) : (
            <div style={{ background: 'linear-gradient(160deg,#7c2d12,#9a3412)', borderRadius: 16, padding: '16px 20px' }}>
              <div className="display" style={{ fontSize: 17, fontWeight: 600, color: '#fed7aa' }}>Not quite — let's think it through 🤔</div>
              <div style={{ marginTop: 8, fontSize: 16, lineHeight: 1.5, color: '#fff' }}>{feedback.hint}</div>
            </div>
          )}
          {explainPrompt && (
            <div style={{ marginTop: 12, background: 'var(--bg-card)', borderRadius: 14, padding: '14px 16px', border: '1px solid var(--border)' }}>
              <div style={{ fontWeight: 700, color: 'var(--text-soft)', marginBottom: 8 }}>{explainPrompt}</div>
              <input value={explainValue} onChange={e => setExplainValue(e.target.value)} placeholder="(optional) one quick line…"
                style={{ width: '100%', padding: '12px 14px', borderRadius: 10, background: 'var(--bg-deep)', color: '#fff', border: '1px solid var(--border)', outline: 'none', fontSize: 15 }} />
            </div>
          )}
        </div>
      )}

      {confirmStep && !feedback && (
        <div style={{ marginTop: 18, background: 'linear-gradient(160deg,#1e3a8a,#1d4ed8)', borderRadius: 16, padding: '16px 20px', animation: 'slideIn .25s ease' }}>
          <div className="display" style={{ fontSize: 18, fontWeight: 600, color: '#dbeafe' }}>👀 Quick check before you submit</div>
          <div style={{ marginTop: 6, fontSize: 15, lineHeight: 1.5, color: '#fff' }}>
            Look at your decimal point — is it in exactly the right spot? (Easy to drop a zero!) Fix it above if you need to, then submit.
          </div>
        </div>
      )}

      <div style={{ marginTop: 20 }}>
        {!feedback ? (
          confirmStep ? (
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={() => setConfirmStep(false)} style={{ flex: 1, padding: '16px', borderRadius: 16, background: 'var(--bg-card)', color: 'var(--text-soft)', fontFamily: "'Fredoka',sans-serif", fontWeight: 600, fontSize: 18 }}>✏️ Let me fix it</button>
              <button disabled={checking} onClick={submit} style={{ flex: 1.4, padding: '16px', borderRadius: 16, background: 'linear-gradient(90deg,#16a34a,#22c55e)', color: '#fff', fontFamily: "'Fredoka',sans-serif", fontWeight: 600, fontSize: 18, opacity: checking ? 0.7 : 1 }}>{checking ? 'Checking…' : 'Checked it — submit ✓'}</button>
            </div>
          ) : (
            <button disabled={checking || (q.type === 'mc' ? !selected : !fillValue.trim())} onClick={submit}
              style={{ width: '100%', padding: '16px', borderRadius: 16, background: (q.type === 'mc' ? selected : fillValue.trim()) ? accent : 'var(--bg-card)', color: '#fff', fontFamily: "'Fredoka',sans-serif", fontWeight: 600, fontSize: 20, opacity: checking ? 0.7 : 1 }}>
              {checking ? 'Checking…' : 'Check answer'}
            </button>
          )
        ) : (
          <button onClick={next} style={{ width: '100%', padding: '16px', borderRadius: 16, background: 'linear-gradient(90deg,#7c3aed,#a855f7)', color: '#fff', fontFamily: "'Fredoka',sans-serif", fontWeight: 600, fontSize: 20 }}>
            {idx + 1 >= questions.length ? 'See my results →' : 'Next question →'}
          </button>
        )}
      </div>

      {!helpOpen && (
        <button onClick={() => setHelpOpen(true)} style={{ marginTop: 18, width: '100%', padding: '13px', borderRadius: 14, background: 'var(--bg-card)', color: '#fcd34d', fontWeight: 800, fontSize: 15, border: '1px dashed var(--border)' }}>
          🙋 I'm stuck — ask for help
          {helpCount.current > 0 && <span style={{ marginLeft: 8, fontSize: 12.5, color: 'var(--text-dim)' }}>(asked {helpCount.current}× this session)</span>}
        </button>
      )}

      {helpOpen && (
        <div style={{ marginTop: 18, background: 'var(--bg-card)', borderRadius: 18, border: '1px solid var(--border)', overflow: 'hidden', animation: 'slideIn .25s ease' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: 'linear-gradient(90deg,#5b21b6,#7c3aed)' }}>
            <div className="display" style={{ fontWeight: 600, fontSize: 16 }}>🙋 Ask your tutor</div>
            <button onClick={() => setHelpOpen(false)} style={{ background: '#0003', color: '#fff', borderRadius: 8, padding: '4px 10px', fontWeight: 700, fontSize: 13 }}>Close</button>
          </div>
          <div style={{ maxHeight: 240, overflowY: 'auto', padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 10 }}>
            {helpMsgs.length === 0 && (
              <div style={{ color: 'var(--text-dim)', fontSize: 14, lineHeight: 1.5 }}>
                Stuck on this one? Ask me anything about it — I'll help you figure it out (but I won't just give you the answer 😊).
              </div>
            )}
            {helpMsgs.map((m, i) => (
              <div key={i} style={{ alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '85%', padding: '10px 14px', borderRadius: 14, fontSize: 14.5, lineHeight: 1.5, background: m.role === 'user' ? 'linear-gradient(160deg,#2563eb,#1d4ed8)' : 'var(--bg-deep)', color: '#fff', whiteSpace: 'pre-wrap' }}>{m.content}</div>
            ))}
            {helpBusy && <div style={{ alignSelf: 'flex-start', padding: '10px 14px' }}><div className="spinner" style={{ width: 22, height: 22, borderWidth: 3 }} /></div>}
          </div>
          <div style={{ display: 'flex', gap: 8, padding: '12px 16px', borderTop: '1px solid var(--border)' }}>
            <input value={helpInput} onChange={e => setHelpInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') sendHelp() }} placeholder="Type your question…"
              style={{ flex: 1, padding: '12px 14px', borderRadius: 10, background: 'var(--bg-deep)', color: '#fff', border: '1px solid var(--border)', outline: 'none', fontSize: 15 }} />
            <button onClick={sendHelp} disabled={helpBusy || !helpInput.trim()} style={{ padding: '12px 18px', borderRadius: 10, fontWeight: 700, background: helpInput.trim() ? 'linear-gradient(90deg,#7c3aed,#a855f7)' : 'var(--bg-deep)', color: '#fff', fontSize: 15 }}>Ask</button>
          </div>
        </div>
      )}
    </div>
  )
}
