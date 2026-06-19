// Thin client over the backend REST API. Every call sends the shared secret.
// This replaces the browser-direct Anthropic calls and the localStorage Store
// from tutor_app.html.
import { API_BASE, API_SECRET } from './config.js'

async function request(path, { method = 'GET', body, form } = {}) {
  const headers = { 'X-API-Key': API_SECRET }
  let payload
  if (form) {
    payload = form // FormData — let the browser set the multipart boundary
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }

  let res
  try {
    res = await fetch(API_BASE + path, { method, headers, body: payload })
  } catch (e) {
    throw new Error('Could not reach the tutor server. Is it running?')
  }

  if (!res.ok) {
    let detail
    try { detail = (await res.json()).detail } catch { detail = await res.text() }
    const err = new Error(detail || `API error ${res.status}`)
    err.status = res.status
    throw err
  }
  if (res.status === 204) return null
  const text = await res.text()
  return text ? JSON.parse(text) : null
}

export const api = {
  listStudents: () => request('/students'),
  progress: (sid) => request(`/progress/${sid}`),
  dayRecords: (sid, subject, week, day) =>
    request(`/progress/${sid}/day?subject=${subject}&week=${week}&day=${day}`),
  flag: (body) => request('/progress/flag', { method: 'POST', body }),

  activeSession: (sid) => request(`/session/active/${sid}`),
  startSession: (body) => request('/session/start', { method: 'POST', body }),
  answer: (body) => request('/answer', { method: 'POST', body }),
  completeSession: (session_id) =>
    request('/session/complete', { method: 'POST', body: { session_id } }),
  help: (body) => request('/help', { method: 'POST', body }),

  writingPrompt: (sid, week, day) =>
    request(`/writing/prompt?student_id=${sid}&week=${week}&day=${day}`),
  reviewWriting: (body) => request('/writing/review', { method: 'POST', body }),

  analyzeWork: (file, problemContext) => {
    const form = new FormData()
    form.append('file', file)
    form.append('problem_context', problemContext || '')
    return request('/work/analyze', { method: 'POST', form })
  },

  review: (sid) => request(`/review/${sid}`),
}
