// Runtime config from Vite env (VITE_*). See .env.example.
export const API_BASE = import.meta.env.VITE_API_BASE || '/api'
export const API_SECRET = import.meta.env.VITE_API_SECRET || ''
export const STUDENT_ID_OVERRIDE = import.meta.env.VITE_STUDENT_ID
  ? Number(import.meta.env.VITE_STUDENT_ID)
  : null
