# Anam's Learning Lab — Backend

FastAPI + SQLAlchemy backend that holds the Anthropic API key, stores progress,
pre-generates the daily question bank, and runs the server-authoritative game
loop. All tutoring prompts, the curriculum, and the question schema are lifted
**verbatim** from `../tutor_app.html`.

> **Status:** Phases 1–3a done — scaffold + models + generation module (1);
> nightly scheduler, advance/reinforce logic, writing-prompt pre-generation,
> seeding (2); and the full gameplay REST API — session start/answer/complete,
> Socratic help, Supernote analysis, writing, progress + parent review (3a).
> Next: the React/Vite frontend port (3b), then Docker/deploy (4).

## Layout

```
backend/
  app/
    config.py          settings (env): keys, DB url, model, tz, scheduler
    curriculum.py      MATH_WEEKS / ENGLISH_WEEKS / lexile / themes  (verbatim)
    prompts.py         every system/user prompt                      (verbatim)
    jsonutils.py       extractJSON/recoverJSON port (truncation-safe)
    anthropic_client.py call_claude() — the key lives here only
    generation.py      generate_day_pool(): 5-7 questions x level 1-5; writing prompt
    services.py        prepare_day_pool / prepare_writing_prompt (shared, no commit)
    nightly.py         decide_next_day (advance/reinforce) + run_nightly
    scheduler.py       APScheduler nightly cron (8 PM America/New_York)
    seeding.py         seed_initial_pools (Week 1 Days 1-3)
    sessions.py        select+lock, grade, finalize (server-authoritative loop)
    progress_report.py home-screen / day-review / parent-review aggregations
    grading.py         grade_answer / get_hint / ask_help (server-side)
    vision.py          analyze_work (Supernote image)
    review.py          parent_review / review_writing
    models.py          students, question_pool, sessions, answers,
                       weak_spots, progress_flags, writing_prompts
    schemas.py         QuestionPublic (NO answer/solution) vs internal
    auth.py            X-API-Key shared secret
    routers/admin.py   health, generate-day, pool, run-nightly, seed, writing-prompt
    routers/play.py    session start/answer/complete, help, work, writing
    routers/progress.py progress, progress/day, progress/flag, review
    main.py            app factory (starts the scheduler on boot)
  seed.py / seed_pools.py   create student "Anam" / seed Week 1 Days 1-3
  tests/               run without an API key (Anthropic is mocked)
```

## Run locally

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # set ANTHROPIC_API_KEY + API_SHARED_SECRET
python seed.py                  # creates student "Anam"
python seed_pools.py            # generates Week 1 Days 1-3 pools (needs the API key)
uvicorn app.main:app --reload   # http://127.0.0.1:8000  (docs at /docs)
```

## API

All routes require the `X-API-Key` header except `/api/health`. Generation,
help, answer, work, and writing endpoints are rate-limited.

**Admin / pre-generation**
- `POST /api/admin/generate-day` — build one day's pool (idempotent; `force` to rebuild)
- `GET  /api/admin/pool` — inspect counts for a day
- `POST /api/admin/run-nightly` — trigger the nightly batch by hand
- `POST /api/admin/seed` — seed Week 1 Days 1-3 for a student
- `GET  /api/admin/writing-prompt` — inspect a stored writing prompt

**Gameplay**
- `POST /api/session/start` — select + **lock** questions, return them (no answer key); resumes an in-progress session with the SAME questions
- `POST /api/answer` — grade one answer (exact/normalized first, model only if needed); Socratic hint when wrong; reveals the correct answer post-submit
- `POST /api/session/complete` — score it; update weak-spots / retention / mastery
- `POST /api/help` — "I'm stuck" chat, anchored server-side to the hidden `solution`, with the 2-off-topic redirect; logs each help request
- `POST /api/work/analyze` — Supernote image analysis (multipart upload)
- `GET  /api/writing/prompt` — fetch the pre-generated writing prompt for a day
- `POST /api/writing/review` — review a writing submission against target vocab

**Progress / review**
- `GET  /api/progress/{student_id}` — home-screen summary (completed days/weeks, weak spots, retention, mastered, help totals, writing counts)
- `GET  /api/progress/{student_id}/day` — saved questions + her answers for one day (review modal)
- `POST /api/progress/flag` — manually mark a day/week done or undone
- `GET  /api/review/{student_id}` — the parent review analysis

### The game loop (server-authoritative)

`session/start` picks a level-distributed sample ordered easy→hard and **locks
the question ids** on the session row, so a refresh/resume returns the exact
same set — never new questions. The `solution` and `answer` stay server-side;
`QuestionPublic` carries only a precomputed `precision` flag for the
read-it-back gate. `session/complete` maps results onto `weak_spots.status`:
missed → `learning` (weighted ~70% next time), correct@level≥2 → `short_term`
(retention queue), retention pass → `mastered`.

### The nightly job (and triggering it by hand)

Every night at `SCHEDULER_HOUR` it reads each student's progress and prepares
**tomorrow's** pool (+ writing prompt on writing days):
no completed sessions → bootstrap the current day; last day went well → advance;
a struggle (score < 60% or ≥ 4 help asks) → reinforce (repeat the same static
day). `generate-day` / `seed` are idempotent.

> Real generation needs `ANTHROPIC_API_KEY` + access to `api.anthropic.com`.
> The test suite mocks the client, so it needs neither.

## Tests

```bash
cd backend && pip install -r requirements-dev.txt && pytest
```

44 tests: JSON-recovery, precision-gate, prompt invariants (incl. 70% weighting
and the per-level deviation), level-pinning, answer-key exclusion, shared
prepare/idempotency/force, advance-vs-reinforce, writing-day generation,
seeding, scheduler registration, the full session loop (start/lock/resume →
answer → complete → weak-spot updates), help/writing/work endpoints, progress
aggregation + manual flags, and parent review.

## Environment variables

| Var | Default | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **required** to generate. Server-only. |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | preserved from the HTML |
| `ANTHROPIC_TIMEOUT` / `ANTHROPIC_MAX_RETRIES` | `60` / `2` | timeout/retries for the quick calls (grading/help) |
| `GENERATION_TIMEOUT` / `GENERATION_RETRIES` | `180` / `3` | timeout/retries for slow question-generation calls (exp. backoff) |
| `LOG_LEVEL` | `INFO` | generation timing + retry logging |
| `API_SHARED_SECRET` | `change-me` | the `X-API-Key` the frontend sends |
| `DATABASE_URL` | `sqlite:///./data/tutor.db` | swap to Postgres with no code change |
| `SCHEDULER_ENABLED` | `true` | start the nightly background job |
| `SCHEDULER_TZ` / `SCHEDULER_HOUR` | `America/New_York` / `20` | DST-aware ~8 PM local |
| `FRONTEND_ORIGIN` | `*` | comma-separated CORS origins (dev only; prod is same-origin) |
| `PER_LEVEL_MIN` / `PER_LEVEL_MAX` | `5` / `7` | pool size per level |
| `STATIC_DIR` | `""` | path to the built SPA; set by the Docker image. Empty = API only |
| `SPA_API_BASE` | `/api` | API base injected into the served SPA at runtime |
| `AUTO_SEED_STUDENT` / `DEFAULT_STUDENT_NAME` | `true` / `Anam` | create the student on first boot |

## Security notes

- The Anthropic key is read only in `anthropic_client.py` from the env; never
  returned or logged.
- `QuestionPublic` (the only question shape sent to the browser) omits `answer`,
  `solution`, and `distractor_note`. Grading and help read them server-side.
- All `/api` routes except `/health` require `X-API-Key`; generation, answer,
  help, work, and writing endpoints are rate-limited.
