// Config resolves at runtime first (window.__APP_CONFIG__ injected by the
// backend when it serves the SPA same-origin), then falls back to Vite build
// env (VITE_*) for local `npm run dev`. See .env.example.
const runtime = (typeof window !== 'undefined' && window.__APP_CONFIG__) || {}

export const API_BASE = runtime.apiBase || import.meta.env.VITE_API_BASE || '/api'
export const API_SECRET = runtime.apiSecret || import.meta.env.VITE_API_SECRET || ''
export const STUDENT_ID_OVERRIDE = import.meta.env.VITE_STUDENT_ID
  ? Number(import.meta.env.VITE_STUDENT_ID)
  : null
