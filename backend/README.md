# Anam's Learning Lab — Backend

FastAPI + SQLAlchemy backend that holds the Anthropic API key, stores progress,
and pre-generates the daily question bank. All tutoring prompts, the curriculum,
and the question schema are lifted **verbatim** from `../tutor_app.html`.

> **Status:** Phase 1 (scaffold, models, generation module, manual `generate-day`)
> and Phase 2 (nightly scheduler, advance/reinforce logic, writing-prompt
> pre-generation, seeding) are done. Next: the gameplay endpoints + React port
> (Phase 3), then Docker/deploy (Phase 4).

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
    grading.py         grade_answer / get_hint / ask_help (server-side)
    vision.py          analyze_work (Supernote image)
    review.py          parent_review / review_writing
    models.py          students, question_pool, sessions, answers,
                       weak_spots, progress_flags, writing_prompts
    schemas.py         QuestionPublic (NO answer/solution) vs internal
    auth.py            X-API-Key shared secret
    routers/admin.py   health, generate-day, pool, run-nightly, seed, writing-prompt
    main.py            app factory (starts the scheduler on boot)
  seed.py              create student "Anam"
  seed_pools.py        seed Week 1 Days 1-3 pools (calls the API)
  tests/               run without an API key (Anthropic is mocked)
```

## Run locally

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # then edit .env: set ANTHROPIC_API_KEY + API_SHARED_SECRET
python seed.py                  # creates student "Anam" (prints the student_id)
uvicorn app.main:app --reload   # http://127.0.0.1:8000  (docs at /docs)
```

On boot the nightly scheduler starts automatically (8 PM `America/New_York`).
Set `SCHEDULER_ENABLED=false` to run the API without it.

### Seed a few days so you can test immediately

```bash
python seed_pools.py    # generates Week 1 Days 1-3 for both subjects (needs the API key)
```

Or per-day over HTTP:

```bash
curl -s -X POST localhost:8000/api/admin/generate-day \
  -H "X-API-Key: $API_SHARED_SECRET" -H "Content-Type: application/json" \
  -d '{"student_id":1,"subject":"math","week":1,"day":1}'

# inspect what's stored (solutions are NOT returned)
curl -s "localhost:8000/api/admin/pool?student_id=1&subject=math&week=1&day=1" \
  -H "X-API-Key: $API_SHARED_SECRET"
```

### The nightly job (and how to trigger it by hand)

Every night at `SCHEDULER_HOUR` it reads each student's progress and prepares
**tomorrow's** pool (+ reading passage, + writing prompt on writing days):

- no completed sessions yet → bootstrap the current day
- last session went well → **advance** to the next day
- last session was a struggle (score < 60% or ≥ 4 help asks) → **reinforce**:
  repeat the same day (its static pool is reused — never regenerated mid-session)

Trigger it manually any time (e.g. to prep ahead or recover a missed run):

```bash
curl -s -X POST localhost:8000/api/admin/run-nightly -H "X-API-Key: $API_SHARED_SECRET"
# seed a specific student's first days:
curl -s -X POST localhost:8000/api/admin/seed -H "X-API-Key: $API_SHARED_SECRET" \
  -H "Content-Type: application/json" -d '{"student_id":1,"days":[1,2,3]}'
```

`generate-day` / `seed` are **idempotent** — a day's pool is built once and is
otherwise static. Pass `"force": true` to `generate-day` to rebuild.

> Real generation needs `ANTHROPIC_API_KEY` set and outbound access to
> `api.anthropic.com`. The test suite mocks the client, so it needs neither.

## Tests

```bash
cd backend && pip install -r requirements-dev.txt && pytest
```

35 tests covering: JSON-recovery, the precision-gate predicate, prompt
invariants (incl. the 70% weak-spot weighting and the per-level deviation),
level-pinning, `solution`/`answer` exclusion from `QuestionPublic`, the shared
prepare/idempotency/force services, the advance-vs-reinforce decision logic,
writing-day prompt generation, seeding, scheduler job registration, and the
full HTTP flow (auth + idempotency + nightly/seed/writing endpoints).

## Environment variables

| Var | Default | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **required** to generate. Server-only. |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | preserved from the HTML |
| `ANTHROPIC_TIMEOUT` | `40` | seconds per call |
| `ANTHROPIC_MAX_RETRIES` | `1` | transient-error retries |
| `API_SHARED_SECRET` | `change-me` | the `X-API-Key` the frontend sends |
| `DATABASE_URL` | `sqlite:///./data/tutor.db` | swap to Postgres with no code change |
| `SCHEDULER_ENABLED` | `true` | start the nightly background job |
| `SCHEDULER_TZ` | `America/New_York` | DST-aware Eastern (always ~8 PM local) |
| `SCHEDULER_HOUR` | `20` | nightly run hour, local |
| `FRONTEND_ORIGIN` | `*` | comma-separated CORS origins |
| `PER_LEVEL_MIN` / `PER_LEVEL_MAX` | `5` / `7` | pool size per level |

## Security notes

- The Anthropic key is read only in `anthropic_client.py` from the env; it is
  never returned or logged.
- `QuestionPublic` (the only question shape sent to the browser) omits `answer`,
  `solution`, and `distractor_note`. A precomputed `precision` flag drives the
  read-it-back gate without leaking the answer.
- All `/api` routes except `/health` require the `X-API-Key` header; generation
  and nightly/seed endpoints are rate-limited.
