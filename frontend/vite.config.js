import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev server runs on :5173 and talks to the FastAPI backend via VITE_API_BASE
// (default http://localhost:8000/api). In production the built static files are
// served behind the same domain and VITE_API_BASE can be "/api".
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
})
