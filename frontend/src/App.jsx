import React, { useState, useEffect, useCallback } from 'react'
import { api } from './api.js'
import { STUDENT_ID_OVERRIDE } from './config.js'
import { CenterWrap, Spinner, ErrorBox } from './ui.jsx'
import Setup from './screens/Setup.jsx'
import Quiz from './screens/Quiz.jsx'
import Results from './screens/Results.jsx'
import WorkUpload from './screens/WorkUpload.jsx'
import Writing from './screens/Writing.jsx'
import ParentReview from './screens/ParentReview.jsx'

export default function App() {
  const [loaded, setLoaded] = useState(false)
  const [loadError, setLoadError] = useState(null)
  const [student, setStudent] = useState(null)
  const [progress, setProgress] = useState(null)
  const [activeSession, setActiveSession] = useState(null)
  const [screen, setScreen] = useState('setup')
  const [config, setConfig] = useState(null)
  const [lastSession, setLastSession] = useState(null)
  const [resuming, setResuming] = useState(false)

  const refresh = useCallback(async () => {
    if (!student) return
    const [p, a] = await Promise.all([api.progress(student.id), api.activeSession(student.id)])
    setProgress(p); setActiveSession(a)
  }, [student])

  useEffect(() => {
    (async () => {
      try {
        const students = await api.listStudents()
        if (!students || !students.length) {
          setLoadError('No student found yet. On the server run: python seed.py')
          setLoaded(true); return
        }
        const chosen = STUDENT_ID_OVERRIDE
          ? students.find(s => s.id === STUDENT_ID_OVERRIDE) || students[0]
          : students[0]
        setStudent(chosen)
        const [p, a] = await Promise.all([api.progress(chosen.id), api.activeSession(chosen.id)])
        setProgress(p); setActiveSession(a); setLoaded(true)
      } catch (e) {
        setLoadError(e.message); setLoaded(true)
      }
    })()
  }, [])

  function start(cfg) {
    setResuming(false); setConfig(cfg)
    if (cfg.subject === 'work') setScreen('work')
    else if (cfg.subject === 'review') setScreen('review')
    else if (cfg.subject === 'writing') setScreen('writing')
    else setScreen('quiz')
  }

  function resumeSession() {
    setConfig({ subject: activeSession.subject, week: activeSession.week, day: activeSession.day, mode: activeSession.mode })
    setResuming(true); setScreen('quiz')
  }

  // "Start fresh" just dismisses the banner; the in-progress session is harmless
  // and re-entering that day resumes it.
  function discardSession() { setActiveSession(null) }

  if (!loaded) return <CenterWrap><Spinner label="Loading Anam's lab…" /></CenterWrap>
  if (loadError) return <CenterWrap><ErrorBox error={loadError} /></CenterWrap>

  return (
    <>
      {screen === 'setup' && <>
        {activeSession && (
          <div style={{ maxWidth: 720, margin: '0 auto', padding: '18px 18px 0' }}>
            <div style={{ background: 'linear-gradient(160deg,#1e3a8a,#1d4ed8)', borderRadius: 16,
              padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              gap: 12, flexWrap: 'wrap' }}>
              <div>
                <div className="display" style={{ fontSize: 17, fontWeight: 600 }}>
                  📌 You have an unfinished {activeSession.subject === 'math' ? 'Math' : 'English'} session
                </div>
                <div style={{ fontSize: 13.5, color: '#dbeafe', marginTop: 3 }}>
                  Week {activeSession.week}, Day {activeSession.day} · question {activeSession.answered + 1} of {activeSession.total}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={discardSession} style={{ padding: '10px 14px', borderRadius: 10,
                  background: '#0003', color: '#fff', fontWeight: 700, fontSize: 14 }}>Start fresh</button>
                <button onClick={resumeSession} style={{ padding: '10px 16px', borderRadius: 10,
                  background: 'linear-gradient(90deg,#16a34a,#22c55e)', color: '#fff', fontWeight: 700, fontSize: 14 }}>
                  Resume →
                </button>
              </div>
            </div>
          </div>
        )}
        <Setup student={student} progress={progress} onStart={start} onRefresh={refresh} />
      </>}

      {screen === 'quiz' && <Quiz student={student} config={config} resuming={resuming}
        onDone={(summary) => { setLastSession(summary); setResuming(false); refresh(); setScreen('results') }}
        onExit={() => { setResuming(false); refresh(); setScreen('setup') }} />}

      {screen === 'results' && <Results session={lastSession} onHome={() => setScreen('setup')} />}

      {screen === 'work' && <WorkUpload onExit={() => setScreen('setup')} />}

      {screen === 'writing' && <Writing student={student} config={config} progress={progress}
        onExit={() => { refresh(); setScreen('setup') }} />}

      {screen === 'review' && <ParentReview student={student} progress={progress}
        onExit={() => setScreen('setup')} />}
    </>
  )
}
