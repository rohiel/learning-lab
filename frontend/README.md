# Anam's Learning Lab — Frontend

Vite + React port of `../tutor_app.html`. The UI, styling, and adaptive engine
are unchanged; every Anthropic call and `localStorage` read is replaced by a
call to our backend (`src/api.js`). The answer key never reaches the browser.

## Run locally

```bash
cd frontend
cp .env.example .env     # set VITE_API_BASE + VITE_API_SECRET (match the backend)
npm install
npm run dev              # http://localhost:5173
```

The backend must be running (default `http://localhost:8000`) with
`FRONTEND_ORIGIN=http://localhost:5173` so CORS allows the dev server, and at
least one day's pool generated (`python seed_pools.py`).

## Build

```bash
npm run build            # -> dist/ (static files; serve behind your domain)
npm run preview          # preview the production build locally
```

## Structure

```
src/
  api.js          backend client (sends X-API-Key)
  config.js       VITE_API_BASE / VITE_API_SECRET / VITE_STUDENT_ID
  curriculum.js   display-only constants (lifted from the HTML)
  App.jsx         student/progress load, screen routing, resume banner
  screens/        Setup, Quiz, Results, WorkUpload, Writing, ParentReview
  ui.jsx          shared primitives (Spinner, Section, BigToggle, …)
  styles.css      the original CSS (verbatim)
```

## Notes

- The shared secret is embedded in the build and visible to anyone who loads the
  page — fine for a one-family app, but not strong auth.
- **Resume:** opening a day with an in-progress session returns the SAME locked
  questions; the adaptive level/streak are rebuilt from the answered questions.
- The read-it-back gate fires on the server-computed `precision` flag (so the
  browser never needs the answer).
