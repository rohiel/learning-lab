# Anam's Learning Lab

A hosted tutoring app for a rising 6th grader — adaptive Math + English practice,
a pre-generated daily question bank, Socratic help, Supernote work analysis,
writing review, and a parent dashboard.

Originally a single browser file (`tutor_app.html`) that called the Anthropic API
directly; now a real web app:

```
Browser (React/Vite SPA)
        │  fetch /api/*   (X-API-Key)
        ▼
FastAPI backend ── Anthropic API   (key server-side only)
        │
        ▼
SQLite (SQLAlchemy; swap to Postgres via DATABASE_URL)
        ▲
APScheduler nightly job (8 PM America/New_York) pre-generates tomorrow's pool
```

- **Answer keys never reach the browser.** Questions are served without
  `answer`/`solution`; grading and the help bot read them server-side.
- **Questions are pre-generated** into a per-day pool (5–7 per level × levels 1–5)
  and **locked per session**, so a refresh resumes the exact same questions with
  zero live generation while she works.
- All tutoring prompts, the 8-week curriculum, and the question schema are lifted
  **verbatim** from `tutor_app.html`.

## Repo layout

```
tutor_app.html      the original single-file app (the behavioral spec)
backend/            FastAPI + SQLAlchemy + APScheduler   (see backend/README.md)
frontend/           Vite + React SPA                     (see frontend/README.md)
Dockerfile          single image: builds the SPA, serves it from the backend
docker-compose.yml  one-command local run with a SQLite volume
Makefile            dev shortcuts
DEPLOY.md           Railway / Render + custom domain
```

## Local development

First-time setup (Python 3.11+, Node 20+):

```bash
make setup            # backend venv + frontend npm install
cp backend/.env.example backend/.env   # set ANTHROPIC_API_KEY + API_SHARED_SECRET
cp frontend/.env.example frontend/.env # set VITE_API_SECRET to the SAME secret
```

Then run each side (one command each):

```bash
make backend          # API at http://localhost:8000  (docs at /docs)
make frontend         # SPA at http://localhost:5173
```

For the SPA to reach the API in dev, set `FRONTEND_ORIGIN=http://localhost:5173`
in `backend/.env` (CORS) and `VITE_API_BASE=http://localhost:8000/api` in
`frontend/.env`. Seed some questions so a session has content:

```bash
make seed             # creates the student
make seed-pools       # generates Week 1 Days 1-3 (calls the Anthropic API)
make test             # 47 backend tests (no API key needed; Anthropic mocked)
```

## Run the whole thing in one container

```bash
cp .env.example .env  # set ANTHROPIC_API_KEY + API_SHARED_SECRET
make docker           # or: docker compose up --build
# open http://localhost:8000   (SPA + API, same origin, SQLite in a volume)
```

The container serves the built SPA at `/` and the API at `/api`. The shared
secret is injected into the page at runtime from `API_SHARED_SECRET` — no
rebuild needed to rotate it.

## Deploy to your domain

See **[DEPLOY.md](DEPLOY.md)** — Railway (recommended, because the nightly job
needs an always-on process) or Render, with a persistent volume for SQLite and a
CNAME to your domain.

## Environment variables

The full list with defaults is in [backend/README.md](backend/README.md#environment-variables).
The essentials: `ANTHROPIC_API_KEY` (required, server-only) and
`API_SHARED_SECRET` (gates the API; also injected into the SPA).
